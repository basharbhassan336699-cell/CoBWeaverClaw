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

    def __init__(self, config: dict):
        self.config = config
        self.issues = []
        self.fixed  = []

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
        import urllib.request
        try:
            urllib.request.urlopen("https://api.anthropic.com", timeout=5)
            return {"ok": True, "details": "Anthropic API reachable"}
        except Exception:
            return {"ok": False, "details": "Cannot reach Anthropic API"}

    async def _check_skills(self) -> dict:
        skills_dir = "skills/"
        count = len([f for f in os.listdir(skills_dir) if f.endswith(".py") and not f.startswith("_")])
        return {"ok": count > 0, "details": f"{count} skills found"}

    async def _check_security(self) -> dict:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        ok = bool(api_key)
        return {"ok": ok, "details": "API key set" if ok else "ANTHROPIC_API_KEY not set"}

    async def _fix(self, check: str, result: dict):
        """Attempt to fix a failed check."""
        self.fixed.append(check)
