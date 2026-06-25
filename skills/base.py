"""
Base Skill Class — All skills inherit from this.
"""
from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """
    Every skill in CoBWeaverClaw inherits from this.
    Skills are auto-discovered from the skills/ directory.
    """
    name:        str   = "unnamed"
    trigger:     list  = []
    permissions: list  = []
    sandbox:     bool  = True
    score:       float = 0.8     # 0.0-1.0, updated by SkillClaw

    @abstractmethod
    async def run(self, query: str, context: dict) -> str:
        """Execute the skill. Return response string."""
        ...

    def log_success(self):
        self.score = min(1.0, self.score + 0.02)

    def log_failure(self):
        self.score = max(0.0, self.score - 0.05)
