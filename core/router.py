"""
Command Router — Directs messages to the right skill or brain.
"""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.agent import CoBWeaverClaw


class Router:
    """Routes incoming messages to skills or the AI brain."""

    def __init__(self, agent: "CoBWeaverClaw"):
        self.agent  = agent
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        """Auto-discover and load all skills from skills/ directory."""
        import importlib, os, glob
        skill_files = glob.glob("skills/*.py")
        for f in skill_files:
            name = os.path.basename(f)[:-3]
            if name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(f"skills.{name}")
                if hasattr(mod, "SKILL"):
                    skill = mod.SKILL()
                    for trigger in skill.trigger:
                        self.skills[trigger.lower()] = skill
            except Exception:
                pass

    async def handle(self, message: str, context: dict, lang: str) -> str:
        """Route message to appropriate skill or fall through to brain."""
        lower = message.lower()

        # Check skill triggers
        for trigger, skill in self.skills.items():
            if trigger in lower:
                if skill.score >= 0.3:  # Only use skills with decent score
                    return await skill.run(message, context)

        # Fall through to AI brain
        return await self.agent.brain.complete(message, context, lang)
