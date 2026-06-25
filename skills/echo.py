"""
Echo Skill — مهارة بسيطة للاختبار والترحيب.
"""
from skills.base import BaseSkill


class EchoSkill(BaseSkill):
    name        = "echo"
    trigger     = ["echo", "ردد", "اختبار", "test"]
    permissions = []
    sandbox     = False
    score       = 0.9

    async def run(self, query: str, context: dict) -> str:
        text = query
        for t in self.trigger:
            text = text.replace(t, "").strip()
        return f"🔊 {text}" if text else "🔊 الوكيل يعمل! Agent is working!"


SKILL = EchoSkill
