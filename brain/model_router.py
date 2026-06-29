"""
Model Router — يبني هوية الوكيل ويحقن الذاكرة ويوجّه المهام للمزوّد الأنسب.

  • هوية الوكيل  : تُبنى من config.agent (لا من إدخال المستخدم) + mission_anchor
  • حقن الذاكرة  : Working (history) + Episodic (summaries) + Core (facts)
  • توجيه المفاتيح: keys في config تربط نوع المهمة بمزوّد محدّد

يدعم 10 مزوّدين: deepseek, zai, anthropic, openai, groq, openrouter,
                  mistral, xai, gemini, ollama
"""
import os
import json
import urllib.request
import urllib.error


class ModelRouter:
    """يوجّه الطلبات للنموذج الأنسب ثم يجرّب البقية عند الفشل."""

    # المزود → (endpoint, متغير البيئة, نمط الـ API)
    PROVIDERS = {
        "anthropic":  ("https://api.anthropic.com/v1/messages",          "ANTHROPIC_API_KEY",  "anthropic"),
        "openai":     ("https://api.openai.com/v1/chat/completions",      "OPENAI_API_KEY",     "openai"),
        "groq":       ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY",       "openai"),
        "deepseek":   ("https://api.deepseek.com/chat/completions",       "DEEPSEEK_API_KEY",   "openai"),
        "openrouter": ("https://openrouter.ai/api/v1/chat/completions",   "OPENROUTER_API_KEY", "openai"),
        "mistral":    ("https://api.mistral.ai/v1/chat/completions",      "MISTRAL_API_KEY",    "openai"),
        "xai":        ("https://api.x.ai/v1/chat/completions",            "XAI_API_KEY",        "openai"),
        "zai":        ("https://api.z.ai/api/paas/v4/chat/completions",   "ZAI_API_KEY",        "openai"),
        "gemini":     ("",                                                "GEMINI_API_KEY",     "gemini"),
        "ollama":     ("http://localhost:11434/api/chat",                 "",                   "ollama"),
    }

    # نموذج افتراضي لكل مزود (يُستخدم عند توجيه المهمة بالمفتاح فقط)
    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-4-6", "openai": "gpt-4o-mini",
        "groq": "llama-3.3-70b-versatile", "deepseek": "deepseek-chat",
        "openrouter": "meta-llama/llama-3.3-70b", "mistral": "mistral-small-latest",
        "xai": "grok-2", "zai": "glm-4.6", "gemini": "gemini-2.0-flash",
        "ollama": "mistral",
    }

    ALL_ROLES = ["primary", "fast", "coding", "arabic", "research", "fallback", "local"]

    # نوع المهمة → دور المفتاح في config.keys
    TASK_TO_KEYROLE = {
        "chat": "primary_chat", "analysis": "analysis", "code": "analysis",
        "summary": "fast_tasks", "search": "fast_tasks",
    }

    def __init__(self, config: dict):
        # يقبل إمّا الـ config الكامل أو قسم brain فقط (توافق خلفي)
        if "brain" in config or "agent" in config or "keys" in config:
            self.full_config = config
            brain = config.get("brain", {})
        else:
            self.full_config = {"brain": config}
            brain = config
        self.brain      = brain
        self.agent_cfg  = self.full_config.get("agent", {})
        self.keys_cfg   = self.full_config.get("keys", {})

        for role in self.ALL_ROLES:
            setattr(self, role, brain.get(role))
        if not any(getattr(self, r) for r in self.ALL_ROLES):
            self.primary = "anthropic/claude-sonnet-4-6"
            self.fast    = "groq/llama-3.3-70b-versatile"
            self.local   = "ollama/mistral"

        # خريطة مزوّد → "provider/model" من الأدوار المُعدّة
        self._provider_models = {}
        for role in self.ALL_ROLES:
            val = getattr(self, role, None)
            if val and "/" in val:
                prov = val.split("/", 1)[0]
                self._provider_models.setdefault(prov, val)

    # ── task & model selection ───────────────────────────────
    def _detect_task_type(self, message: str) -> str:
        m = (message or "").lower()
        if any(k in m for k in ["code", "function", "bug", "python", "javascript",
                                "كود", "دالة", "برمج", "خطأ برمجي"]):
            return "code"
        if any(k in m for k in ["analyze", "compare", "strategy", "explain",
                                "حلل", "قارن", "استراتيجية", "اشرح", "صمم"]) or len(message) > 200:
            return "analysis"
        if any(k in m for k in ["summarize", "summary", "tldr", "لخّص", "تلخيص", "ملخص"]):
            return "summary"
        if any(k in m for k in ["search", "find", "lookup", "ابحث", "بحث"]):
            return "search"
        return "chat"

    def _select_model_str(self, message, context):
        """يختار "provider/model" بناءً على نوع المهمة وتوجيه المفاتيح."""
        task = self._detect_task_type(message)
        key_role = self.TASK_TO_KEYROLE.get(task)
        provider = self.keys_cfg.get(key_role) if key_role else None
        # 1) مزوّد المهمة معرّف ولديه نموذج مُعدّ → استخدمه
        if provider and provider in self._provider_models:
            return self._provider_models[provider]
        # 2) مزوّد المهمة معرّف ولديه مفتاح بيئة → استخدم نموذجه الافتراضي
        if provider and provider in self.PROVIDERS:
            _, env, _ = self.PROVIDERS[provider]
            if not env or os.environ.get(env):
                return f"{provider}/{self.DEFAULT_MODELS.get(provider, '')}"
        # 3) رجوع لاختيار حسب الدور التقليدي
        if getattr(self, "arabic", None) and any(c in message for c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"):
            return self.arabic
        if task in ("analysis", "code") and getattr(self, "primary", None):
            return self.primary
        return getattr(self, "fast", None) or getattr(self, "primary", None)

    def _parse_model(self, model_str):
        if model_str and "/" in model_str:
            provider, model = model_str.split("/", 1)
            return provider, model
        return "anthropic", (model_str or "")

    def _build_order(self, preferred_str):
        """يرتّب النماذج: المفضّل أولاً ثم بقية الأدوار المُعدّة (fallback chain)."""
        order, seen = [], set()
        for ms in [preferred_str] + [getattr(self, r, None) for r in self.ALL_ROLES]:
            if ms and ms not in seen:
                seen.add(ms)
                order.append(ms)
        return order

    # ── public entry ─────────────────────────────────────────
    async def complete(self, message, context, lang="en", force_model=None):
        system   = self._build_system_prompt(lang, context)
        messages = self._build_messages(message, context)
        preferred = force_model or self._select_model_str(message, context)
        order = self._build_order(preferred)

        errors, tried = [], []
        for model_str in order:
            provider, model = self._parse_model(model_str)
            if provider not in self.PROVIDERS:
                errors.append(f"{provider}: مزود غير مدعوم")
                continue
            tried.append(f"{provider}/{model}")
            try:
                return await self._call(provider, model, system, messages)
            except Exception as e:
                errors.append(f"{provider}: {str(e)[:80]}")
                continue

        detail = "\n".join(f"  - {e}" for e in errors) if errors else "  - لا يوجد نموذج مُعدّ"
        if lang == "ar":
            return ("⚠️ تعذّر الاتصال بأي نموذج.\n\n"
                    f"النماذج المُجرّبة: {', '.join(tried) or 'لا شيء'}\n"
                    f"الأسباب:\n{detail}\n\n"
                    "تأكّد من المفتاح: python setup_wizard.py --models\n"
                    "أو افحص: python main.py doctor")
        return ("⚠️ Could not reach any model.\n\n"
                f"Tried: {', '.join(tried) or 'none'}\n"
                f"Reasons:\n{detail}\n\n"
                "Check your key: python setup_wizard.py --models")

    async def complete_meta(self, message, context, lang="en", force_model=None):
        """مثل complete لكن يُرجع dict فيه النموذج المُستخدَم (للـ API/الـ dashboard)."""
        system   = self._build_system_prompt(lang, context)
        messages = self._build_messages(message, context)
        preferred = force_model or self._select_model_str(message, context)
        order = self._build_order(preferred)
        errors, tried = [], []
        for model_str in order:
            provider, model = self._parse_model(model_str)
            if provider not in self.PROVIDERS:
                continue
            tried.append(f"{provider}/{model}")
            try:
                reply = await self._call(provider, model, system, messages)
                return {"reply": reply, "model_used": f"{provider}/{model}"}
            except Exception as e:
                errors.append(f"{provider}: {str(e)[:80]}")
                continue
        return {"reply": "⚠️ تعذّر الاتصال بأي نموذج. " + ("؛ ".join(errors) or ""),
                "model_used": "none", "tried": tried}

    # ── provider dispatch ────────────────────────────────────
    async def _call(self, provider, model, system, messages):
        url, env_key, api_style = self.PROVIDERS[provider]
        if api_style == "anthropic":
            return await self._call_anthropic(model, system, messages)
        elif api_style == "gemini":
            return await self._call_gemini(model, system, messages)
        elif api_style == "ollama":
            return await self._call_ollama(model, system, messages)
        else:
            return await self._call_openai_compatible(url, env_key, model, system, messages)

    async def _call_anthropic(self, model, system, messages):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("لا يوجد ANTHROPIC_API_KEY")
        payload = json.dumps({"model": model, "max_tokens": 1024,
                              "system": system, "messages": messages}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
              headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                       "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["content"][0]["text"]

    async def _call_openai_compatible(self, url, env_key, model, system, messages):
        api_key = os.environ.get(env_key, "")
        if not api_key:
            raise ValueError(f"لا يوجد {env_key}")
        msgs = [{"role": "system", "content": system}] + messages
        payload = json.dumps({"model": model, "messages": msgs, "max_tokens": 1024}).encode()
        req = urllib.request.Request(url, data=payload,
              headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

    async def _call_gemini(self, model, system, messages):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("لا يوجد GEMINI_API_KEY")
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload = json.dumps({"contents": contents,
                              "systemInstruction": {"parts": [{"text": system}]}}).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=payload, headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_ollama(self, model, system, messages):
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        msgs = [{"role": "system", "content": system}] + messages
        payload = json.dumps({"model": model, "messages": msgs, "stream": False}).encode()
        req = urllib.request.Request(f"{host}/api/chat", data=payload,
              headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["message"]["content"]

    # ── identity-driven system prompt (Section 4.2) ──────────
    def _build_system_prompt(self, lang, context):
        """
        يبني هوية الوكيل تلقائياً من config.agent — لا من إدخال المستخدم.
        يضيف mission_anchor (مرساة المهمة) ضدّ انحراف الهوية،
        ثم يحقن Core Knowledge و Episodic Memory كسياق خلفي.
        """
        a = self.agent_cfg or {}
        name    = a.get("name", "كلاو")
        style   = a.get("style", "professional")
        spec    = a.get("specialization", "general")
        a_lang  = a.get("language", lang)
        anchor  = a.get("mission_anchor", "")

        style_ar = {"professional": "احترافي", "friendly": "ودّي",
                    "direct": "مباشر", "formal": "رسمي"}.get(style, style)
        spec_ar  = {"general": "عام", "trading": "التداول", "academic": "الأكاديميا",
                    "technical": "التقنية", "business": "الأعمال"}.get(spec, spec)
        lang_word = {"ar": "بالعربية", "en": "بالإنجليزية",
                     "both": "بالعربية والإنجليزية"}.get(a_lang, "بالعربية")

        prompt = (
            f"أنت {name}، مساعد ذكاء اصطناعي شخصي ذكي ومتعدّد المهارات تساعد Bashar Hassan.\n"
            f"تتحدّث {lang_word} بأسلوب {style_ar}.\n"
            "ساعد المستخدم في أي موضوع أو مجال يطلبه (معلومات، تحليل، برمجة، كتابة، أفكار، شرح، "
            "ترجمة، حسابات...) بلا أي قيود زمنية أو موضوعية، واتبع تعليماته بدقّة وبأقصى ما تستطيع.\n"
            "استخدم أحدث معارفك في كل الأعوام والمجالات. لا تفترض أبداً أنّ نطاقك محصور بموضوع أو سنة "
            "معيّنة. إن طُلب منك تنفيذ شيء لا تملك أداة مباشرة له، نفّذ ما تستطيع واشرح للمستخدم الخطوات "
            "العملية لإتمام الباقي بدل الاعتذار أو الرفض.\n"
        )
        if spec and spec != "general":
            prompt += f"لديك خبرة إضافية في {spec_ar}، لكن هذا لا يحدّ مساعدتك في بقية المجالات.\n"
        if anchor and anchor.strip():
            prompt += f"عن شخصيتك: {anchor}\n"

        # سياق خلفي (لا يقيّد المواضيع) — Core Knowledge + Episodic
        facts = (context or {}).get("facts", {})
        episodes = (context or {}).get("episodes", [])
        if facts or episodes:
            prompt += ("\nسياق خلفي اختياري عن المستخدم (للاستئناس فقط — لا يقيّد ما يمكنك مناقشته، "
                       "ولا يعني أنّ عليك حصر إجاباتك فيه):\n")
            if facts:
                prompt += "\n".join(f"- {k}: {v}" for k, v in facts.items()) + "\n"
            if episodes:
                prompt += "\n".join(
                    f"- ({e.get('topic','')}) {e.get('key_facts','')}".strip()
                    for e in episodes) + "\n"

        prompt += "\nأجب دائماً بلغة المستخدم في رسالته الحالية."
        return prompt

    def _build_messages(self, message, context):
        """يبني مصفوفة الرسائل: Working Memory (آخر N) ثم الرسالة الحالية."""
        messages = []
        for turn in (context or {}).get("history", [])[-self._history_limit():]:
            messages.append({"role": "user", "content": turn[0]})
            messages.append({"role": "assistant", "content": turn[1]})
        messages.append({"role": "user", "content": message})
        return messages

    def _history_limit(self):
        return int(self.agent_cfg.get("memory_size", 10) or 10)
