"""
Help Skill — يعرض المساعدة والأوامر المتاحة.
"""
from skills.base import BaseSkill


class HelpSkill(BaseSkill):
    name        = "help"
    trigger     = ["help", "مساعدة", "الاوامر", "commands", "?"]
    permissions = []
    sandbox     = False
    score       = 0.95

    async def run(self, query: str, context: dict) -> str:
        is_ar = any(c in query for c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
        if is_ar:
            return (
                "🕷️ CoBWeaverClaw — الأوامر المتاحة:\n\n"
                "• اكتب أي سؤال وسأجيبك\n"
                "• 'اختبار' — للتأكد أن الوكيل يعمل\n"
                "• في الطرفية:\n"
                "  python main.py doctor — تشخيص\n"
                "  python main.py status — الحالة\n"
                "  python setup_wizard.py — إعادة الإعداد\n\n"
                "للإعداد الكامل شغّل: python setup_wizard.py"
            )
        return (
            "🕷️ CoBWeaverClaw — Available commands:\n\n"
            "• Type any question and I'll answer\n"
            "• 'test' — verify the agent works\n"
            "• In terminal:\n"
            "  python main.py doctor — diagnose\n"
            "  python main.py status — status\n"
            "  python setup_wizard.py — reconfigure\n\n"
            "For full setup run: python setup_wizard.py"
        )


SKILL = HelpSkill
