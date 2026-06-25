"""
Command Router — يوجّه الرسائل للمهارة المناسبة أو للنموذج.
"""
import importlib
import os
import glob
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agent import CoBWeaverClaw

logger = logging.getLogger(__name__)


class Router:
    """يوزّع الرسائل الواردة على Skills أو على نموذج AI."""

    def __init__(self, agent: "CoBWeaverClaw"):
        self.agent  = agent
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        """يكتشف ويحمّل كل skills من مجلد skills/."""
        skill_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        pattern   = os.path.join(skill_dir, "*.py")
        for f in glob.glob(pattern):
            name = os.path.basename(f)[:-3]
            if name.startswith("_") or name in ("base", "factory", "evolver"):
                continue
            try:
                mod = importlib.import_module(f"skills.{name}")
                if hasattr(mod, "SKILL"):
                    skill = mod.SKILL()
                    for trigger in skill.trigger:
                        self.skills[trigger.lower()] = skill
                    logger.debug(f"Loaded skill: {name}")
            except Exception as e:
                logger.warning(f"Failed to load skill {name}: {e}")

    async def handle(self, message: str, context: dict, lang: str) -> str:
        """يوجّه الرسالة لمهارة مناسبة أو للنموذج."""
        lower = message.lower().strip()

        # فحص triggers — تطابق كلمة كاملة أو بداية الرسالة
        for trigger, skill in self.skills.items():
            if trigger in lower and skill.score >= 0.3:
                try:
                    result = await skill.run(message, context)
                    skill.log_success()
                    return result
                except Exception as e:
                    skill.log_failure()
                    logger.warning(f"Skill {skill.name} failed: {e}")
                    break

        # لا توجد مهارة مطابقة → النموذج
        return await self.agent.brain.complete(message, context, lang)
