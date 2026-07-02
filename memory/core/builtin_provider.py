"""
BuiltinMemoryProvider — موفّر الذاكرة المدمج (ملفات MEMORY.md و USER.md).
يقرأ الملفين في system prompt؛ الكتابة تتولّاها مراجعة الخلفية (background_review).
"""
from pathlib import Path
from typing import Any, Dict, List

from memory.core.memory_provider import MemoryProvider

_MEM_DIR = Path.home() / ".cobweaverclaw" / "memories"
_MEMORY_MD = _MEM_DIR / "MEMORY.md"
_USER_MD = _MEM_DIR / "USER.md"


class BuiltinMemoryProvider(MemoryProvider):
    """موفّر ذاكرة محلي بسيط قائم على ملفات Markdown."""

    @property
    def name(self) -> str:
        return "builtin"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        _MEM_DIR.mkdir(parents=True, exist_ok=True)
        if not _MEMORY_MD.exists():
            _MEMORY_MD.write_text("# Memory\n", encoding="utf-8")
        if not _USER_MD.exists():
            _USER_MD.write_text("# User\n", encoding="utf-8")

    def system_prompt_block(self) -> str:
        parts = []
        for p in (_USER_MD, _MEMORY_MD):
            try:
                if p.exists():
                    txt = p.read_text(encoding="utf-8").strip()
                    if txt:
                        parts.append(txt)
            except Exception:
                pass
        return "\n\n".join(parts)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        return ""

    def sync_turn(self, *args, **kwargs) -> None:
        # لا شيء — الكتابة تتم عبر background_review
        return None

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []
