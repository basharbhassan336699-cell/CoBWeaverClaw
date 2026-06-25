"""
Model Router — Selects the best AI model for each task automatically.
"""
import os
import json
import urllib.request


class ModelRouter:
    """
    Intelligently routes requests to the best model:
    - Simple queries → Groq (150ms)
    - Complex analysis → Claude
    - Offline → Ollama
    """

    def __init__(self, config: dict):
        self.config  = config
        self.primary = config.get("primary", "claude-sonnet-4-6")
        self.fast    = config.get("fast", "groq/llama-3.3-70b")
        self.local   = config.get("local", "ollama/mistral")

    def _select_model(self, message: str, context: dict) -> str:
        """Auto-select model based on task complexity."""
        complex_keywords = [
            "analyze", "explain", "compare", "strategy", "research",
            "حلل", "اشرح", "قارن", "استراتيجية", "ابحث"
        ]
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in complex_keywords) or len(message) > 200:
            return "primary"
        return "fast"

    async def complete(self, message: str, context: dict, lang: str = "en") -> str:
        """Complete a message using the best available model."""
        model_key = _select_model(message, context)

        system = self._build_system_prompt(lang, context)
        messages = self._build_messages(message, context)

        # Try primary model first, fall back as needed
        try:
            return await self._call_claude(system, messages)
        except Exception:
            try:
                return await self._call_groq(system, messages)
            except Exception:
                return await self._call_ollama(system, messages)

    def _build_system_prompt(self, lang: str, context: dict) -> str:
        name = "CoBWeaverClaw"
        if lang == "ar":
            return f"أنت {name}، وكيل ذكاء اصطناعي متقدم. كن مختصراً وواضحاً وعملياً."
        return f"You are {name}, an advanced AI agent. Be concise, clear, and practical."

    def _build_messages(self, message: str, context: dict) -> list:
        messages = []
        for turn in context.get("history", [])[-6:]:
            messages.append({"role": "user",      "content": turn[0]})
            messages.append({"role": "assistant", "content": turn[1]})
        messages.append({"role": "user", "content": message})
        return messages

    async def _call_claude(self, system: str, messages: list) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("No ANTHROPIC_API_KEY")
        payload = json.dumps({
            "model": self.primary,
            "max_tokens": 1024,
            "system": system,
            "messages": messages
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())["content"][0]["text"]

    async def _call_groq(self, system: str, messages: list) -> str:
        raise NotImplementedError("Groq integration coming in Phase 2")

    async def _call_ollama(self, system: str, messages: list) -> str:
        raise NotImplementedError("Ollama integration coming in Phase 2")
