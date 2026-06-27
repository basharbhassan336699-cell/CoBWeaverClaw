"""
Model Router — يختار أفضل نموذج لكل مهمة تلقائياً.
يدعم: Anthropic, OpenAI, Groq, Gemini, DeepSeek, OpenRouter,
       Mistral, xAI (Grok), Z.AI (GLM), Ollama
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

    ALL_ROLES = ["primary", "fast", "coding", "arabic", "research", "fallback", "local"]

    def __init__(self, config: dict):
        self.config = config
        for role in self.ALL_ROLES:
            setattr(self, role, config.get(role))
        if not any(getattr(self, r) for r in self.ALL_ROLES):
            self.primary = "anthropic/claude-sonnet-4-6"
            self.fast    = "groq/llama-3.3-70b-versatile"
            self.local   = "ollama/mistral"

    def _select_model(self, message, context):
        msg_lower = message.lower()
        if getattr(self, "arabic", None) and any(c in message for c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"):
            return "arabic"
        if getattr(self, "coding", None) and any(k in msg_lower for k in
                ["code", "function", "bug", "python", "javascript", "كود", "دالة", "برمج"]):
            return "coding"
        complex_kw = ["analyze", "explain", "compare", "strategy", "research",
                      "حلل", "اشرح", "قارن", "استراتيجية", "ابحث", "صمم", "اكتب"]
        if any(kw in msg_lower for kw in complex_kw) or len(message) > 200:
            return "primary"
        return "fast"

    def _parse_model(self, model_str):
        if model_str and "/" in model_str:
            provider, model = model_str.split("/", 1)
            return provider, model
        return "anthropic", (model_str or "")

    async def complete(self, message, context, lang="en"):
        system   = self._build_system_prompt(lang, context)
        messages = self._build_messages(message, context)
        preferred = self._select_model(message, context)
        order = [preferred] + [r for r in self.ALL_ROLES if r != preferred]

        errors, tried = [], []
        for role in order:
            model_str = getattr(self, role, None)
            if not model_str:
                continue
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

    def _build_system_prompt(self, lang, context):
        name = "CoBWeaverClaw"
        facts = context.get("facts", {})
        facts_str = ""
        if facts:
            facts_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
            facts_str = f"\n\nمعلومات عن المستخدم:\n{facts_lines}"
        if lang == "ar":
            return f"أنت {name}، وكيل ذكاء اصطناعي متقدّم. كن مختصراً وواضحاً وعملياً.{facts_str}"
        return f"You are {name}, an advanced AI agent. Be concise, clear, practical.{facts_str}"

    def _build_messages(self, message, context):
        messages = []
        for turn in context.get("history", [])[-6:]:
            messages.append({"role": "user", "content": turn[0]})
            messages.append({"role": "assistant", "content": turn[1]})
        messages.append({"role": "user", "content": message})
        return messages
