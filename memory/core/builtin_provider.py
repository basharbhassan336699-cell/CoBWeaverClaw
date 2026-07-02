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

    # ── كتابة الذاكرة (تستدعيها مراجعة الخلفية) ──────────────────────
    @staticmethod
    def _append_bullets(path: Path, bullets: List[str]) -> int:
        """يضيف نقاطاً جديدة (يتجاهل المكرّر) لملف Markdown ويعيد عدد المضاف."""
        _MEM_DIR.mkdir(parents=True, exist_ok=True)
        try:
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception:
            existing = ""
        existing_lines = {
            ln.strip().lstrip("- ").strip().lower()
            for ln in existing.splitlines() if ln.strip().startswith("-")
        }
        added = []
        for b in bullets:
            b = (b or "").strip().lstrip("-").strip()
            if not b:
                continue
            if b.lower() in existing_lines:
                continue
            existing_lines.add(b.lower())
            added.append(f"- {b}")
        if not added:
            return 0
        body = existing.rstrip("\n") + "\n" if existing.strip() else existing
        path.write_text(body + "\n".join(added) + "\n", encoding="utf-8")
        return len(added)

    def add_user_facts(self, bullets: List[str]) -> int:
        """يخزّن حقائق عن المستخدم في USER.md."""
        return self._append_bullets(_USER_MD, bullets)

    def add_memories(self, bullets: List[str]) -> int:
        """يخزّن ملاحظات/تفضيلات دائمة في MEMORY.md."""
        return self._append_bullets(_MEMORY_MD, bullets)
