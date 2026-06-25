"""
Model Router — Selects the best AI model for each task automatically.
يدعم: Anthropic, OpenAI, Groq, Gemini, Cohere, OpenRouter, Mistral, Ollama
"""
import os
import json
import urllib.request
import urllib.error


class ModelRouter:
    """
    يوجّه الطلبات للنموذج الأنسب تلقائياً:
    - أسئلة بسيطة  → Groq (سريع)
    - تحليل معقد   → Claude
    - بدون إنترنت  → Ollama
    """

    def __init__(self, config: dict):
        self.config  = config
        self.primary = config.get("primary", "anthropic/claude-sonnet-4-6")
        self.fast    = config.get("fast",    "groq/llama-3.3-70b-versatile")
        self.local   = config.get("local",   "ollama/mistral")

    def _select_model(self, message: str, context: dict) -> str:
        complex_keywords = [
            "analyze", "explain", "compare", "strategy", "research",
            "حلل", "اشرح", "قارن", "استراتيجية", "ابحث", "صمم", "اكتب"
        ]
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in complex_keywords) or len(message) > 200:
            return "primary"
        return "fast"

    def _parse_model(self, model_str: str):
        """يفصل 'provider/model' إلى (provider, model)."""
        if "/" in model_str:
            provider, model = model_str.split("/", 1)
            return provider, model
        return "anthropic", model_str

    def _available_providers(self) -> list:
        """قائمة النماذج المتاحة فعلياً (لها مفتاح)."""
        available = []
        checks = [
            ("primary", self.primary, "ANTHROPIC_API_KEY", "anthropic"),
            ("fast",    self.fast,    "GROQ_API_KEY",      "groq"),
        ]
        for role, model_str, env_key, prov in checks:
            provider, _ = self._parse_model(model_str)
            if provider == "ollama" or os.environ.get(env_key):
                available.append((role, model_str))
        # Ollama دائماً متاح كـ fallback محلي
        available.append(("local", self.local))
        return available

    async def complete(self, message: str, context: dict, lang: str = "en") -> str:
        """يكمل رسالة باستخدام أفضل نموذج متاح."""
        system   = self._build_system_prompt(lang, context)
        messages = self._build_messages(message, context)

        preferred = self._select_model(message, context)

        # ترتيب المحاولة: المفضّل أولاً ثم البقية
        order = [preferred] + [r for r in ["primary","fast","local"] if r != preferred]

        last_error = None
        for role in order:
            model_str = getattr(self, role, None)
            if not model_str:
                continue
            provider, model = self._parse_model(model_str)
            try:
                if provider == "anthropic":
                    return await self._call_anthropic(model, system, messages)
                elif provider == "openai":
                    return await self._call_openai(model, system, messages)
                elif provider == "groq":
                    return await self._call_groq(model, system, messages)
                elif provider == "gemini":
                    return await self._call_gemini(model, system, messages)
                elif provider == "ollama":
                    return await self._call_ollama(model, system, messages)
                elif provider == "openrouter":
                    return await self._call_openrouter(model, system, messages)
            except Exception as e:
                last_error = e
                continue

        # كل النماذج فشلت — رسالة واضحة بدل crash
        if lang == "ar":
            return (
                "⚠️ لم أتمكن من الاتصال بأي نموذج ذكاء اصطناعي.\n"
                "تأكد من إعداد مفتاح API بتشغيل:\n"
                "python setup_wizard.py --models\n"
                "أو شغّل نموذجاً محلياً عبر Ollama."
            )
        return (
            "⚠️ Could not reach any AI model.\n"
            "Set up an API key by running:\n"
            "python setup_wizard.py --models\n"
            "Or run a local model via Ollama."
        )

    def _build_system_prompt(self, lang: str, context: dict) -> str:
        name  = "CoBWeaverClaw"
        facts = context.get("facts", {})
        facts_str = ""
        if facts:
            facts_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
            facts_str   = f"\n\nKnown facts about user:\n{facts_lines}"
        if lang == "ar":
            return f"أنت {name}، وكيل ذكاء اصطناعي متقدم. كن مختصراً وواضحاً وعملياً.{facts_str}"
        return f"You are {name}, an advanced AI agent. Be concise, clear, and practical.{facts_str}"

    def _build_messages(self, message: str, context: dict) -> list:
        messages = []
        for turn in context.get("history", [])[-6:]:
            messages.append({"role": "user",      "content": turn[0]})
            messages.append({"role": "assistant", "content": turn[1]})
        messages.append({"role": "user", "content": message})
        return messages

    # ── Anthropic ────────────────────────────────────────────
    async def _call_anthropic(self, model, system, messages):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("No ANTHROPIC_API_KEY")
        payload = json.dumps({
            "model": model, "max_tokens": 1024,
            "system": system, "messages": messages
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=payload,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["content"][0]["text"]

    # ── OpenAI ───────────────────────────────────────────────
    async def _call_openai(self, model, system, messages):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("No OPENAI_API_KEY")
        msgs = [{"role":"system","content":system}] + messages
        payload = json.dumps({"model": model, "messages": msgs, "max_tokens": 1024}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

    # ── Groq ─────────────────────────────────────────────────
    async def _call_groq(self, model, system, messages):
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("No GROQ_API_KEY")
        msgs = [{"role":"system","content":system}] + messages
        payload = json.dumps({"model": model, "messages": msgs, "max_tokens": 1024}).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

    # ── Gemini ───────────────────────────────────────────────
    async def _call_gemini(self, model, system, messages):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("No GEMINI_API_KEY")
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload = json.dumps({
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system}]}
        }).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=payload, headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]

    # ── OpenRouter ───────────────────────────────────────────
    async def _call_openrouter(self, model, system, messages):
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("No OPENROUTER_API_KEY")
        msgs = [{"role":"system","content":system}] + messages
        payload = json.dumps({"model": model, "messages": msgs}).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

    # ── Ollama (محلي) ────────────────────────────────────────
    async def _call_ollama(self, model, system, messages):
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        msgs = [{"role":"system","content":system}] + messages
        payload = json.dumps({"model": model, "messages": msgs, "stream": False}).encode()
        req = urllib.request.Request(
            f"{host}/api/chat", data=payload,
            headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["message"]["content"]
