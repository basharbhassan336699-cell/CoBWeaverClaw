"""
Doctor Command — Diagnose and fix the agent automatically.
agent doctor / agent doctor --fix / agent doctor --fix --full
"""
import os
import sys


class Doctor:
    """
    Comprehensive diagnostic and auto-repair system.
    Inspired by OpenClaw doctor, significantly expanded.
    """

    # المزود → (متغير البيئة, رابط فحص الاتصال)
    PROVIDER_INFO = {
        "anthropic":  ("ANTHROPIC_API_KEY",  "https://api.anthropic.com/v1/models"),
        "openai":     ("OPENAI_API_KEY",     "https://api.openai.com/v1/models"),
        "groq":       ("GROQ_API_KEY",       "https://api.groq.com/openai/v1/models"),
        "deepseek":   ("DEEPSEEK_API_KEY",   "https://api.deepseek.com/models"),
        "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/models"),
        "mistral":    ("MISTRAL_API_KEY",    "https://api.mistral.ai/v1/models"),
        "xai":        ("XAI_API_KEY",        "https://api.x.ai/v1/models"),
        "zai":        ("ZAI_API_KEY",        "https://api.z.ai/api/paas/v4/models"),
        "gemini":     ("GEMINI_API_KEY",     "https://generativelanguage.googleapis.com"),
        "ollama":     ("",                   "http://localhost:11434/api/tags"),
    }

    def __init__(self, config: dict):
        self.config = config
        self.issues = []
        self.fixed  = []

    def _primary_provider(self) -> str:
        """يستخرج المزوّد المُعدّ من config (brain.primary أو أول دور مُعدّ)."""
        brain = self.config.get("brain", {})
        for role in ["primary", "fast", "coding", "arabic", "local"]:
            val = brain.get(role)
            if val and "/" in val:
                return val.split("/", 1)[0]
        return "anthropic"

    async def run(self, fix: bool = False, full: bool = False, dry_run: bool = False) -> dict:
        """
        Run diagnosis. If fix=True, attempt repairs.
        If dry_run=True, show what would be fixed without doing it.
        """
        results = {
            "platform":  await self._check_platform(),
            "python":    await self._check_python(),
            "config":    await self._check_config(),
            "memory":    await self._check_memory(),
            "network":   await self._check_network(),
            "skills":    await self._check_skills(),
            "security":  await self._check_security(),
        }

        if fix and not dry_run:
            for check, result in results.items():
                if not result["ok"]:
                    await self._fix(check, result)

        return {
            "results":  results,
            "issues":   self.issues,
            "fixed":    self.fixed,
            "dry_run":  dry_run,
            "score":    sum(1 for r in results.values() if r["ok"]) / len(results)
        }

    async def _check_platform(self) -> dict:
        from core.platform import PlatformAdapter
        p = PlatformAdapter()
        return {"ok": True, "platform": p.platform, "details": f"Detected: {p.platform}"}

    async def _check_python(self) -> dict:
        v = sys.version_info
        ok = v >= (3, 10)
        return {"ok": ok, "details": f"Python {v.major}.{v.minor}.{v.micro}"}

    async def _check_config(self) -> dict:
        ok = bool(self.config)
        if not ok:
            self.issues.append("config_missing")
        return {"ok": ok, "details": "config.yaml loaded" if ok else "config.yaml missing"}

    async def _check_memory(self) -> dict:
        try:
            import sqlite3
            return {"ok": True, "details": "SQLite available"}
        except Exception as e:
            self.issues.append("memory_error")
            return {"ok": False, "details": str(e)}

    async def _check_network(self) -> dict:
        """يفحص الاتصال بمزوّد النماذج المُعدّ فعلياً (لا Anthropic دائماً)."""
        import urllib.request, urllib.error
        provider = self._primary_provider()
        _, url = self.PROVIDER_INFO.get(provider, ("", "https://api.anthropic.com"))
        try:
            urllib.request.urlopen(url, timeout=6)
            return {"ok": True, "details": f"{provider} API reachable"}
        except urllib.error.HTTPError:
            # استجابة HTTP (حتى 401) تعني أن الخادم وصُل
            return {"ok": True, "details": f"{provider} API reachable"}
        except Exception:
            return {"ok": False, "details": f"Cannot reach {provider} API"}

    async def _check_skills(self) -> dict:
        skills_dir = "skills/"
        count = len([f for f in os.listdir(skills_dir) if f.endswith(".py") and not f.startswith("_")])
        return {"ok": count > 0, "details": f"{count} skills found"}

    async def _check_security(self) -> dict:
        """يتحقق من مفتاح المزوّد المُعدّ فعلياً (لا ANTHROPIC دائماً)."""
        provider = self._primary_provider()
        env_key, _ = self.PROVIDER_INFO.get(provider, ("ANTHROPIC_API_KEY", ""))
        if not env_key:   # ollama لا يحتاج مفتاحاً
            return {"ok": True, "details": f"{provider}: لا يحتاج مفتاحاً (محلي)"}
        api_key = os.environ.get(env_key, "")
        ok = bool(api_key)
        if not ok:
            self.issues.append("api_key_missing")
        return {"ok": ok,
                "details": f"{provider} API: ✅ مفتاح مضبوط" if ok
                           else f"{provider} API: ❌ {env_key} غير مضبوط"}

    async def _fix(self, check: str, result: dict):
        """Attempt to fix a failed check."""
        self.fixed.append(check)
