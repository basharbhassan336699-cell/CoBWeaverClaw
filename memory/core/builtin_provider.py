"""
BuiltinMemoryProvider — مزود الذاكرة الأساسي لـ CoBWeaverClaw
يستبدل MEMORY.md النصي بـ SQLite مع أوزان وتناقص زمني وسياقات.
"""
from __future__ import annotations
import logging, math, sqlite3, time
from pathlib import Path
from typing import Any, Dict, List, Optional
from memory.core.memory_provider import MemoryProvider
from cobweaverclaw_constants import get_config_path

logger = logging.getLogger(__name__)

MEMORIES_DIR   = get_config_path() / "memories"
DB_PATH        = MEMORIES_DIR / "memory.db"
CONTEXTS       = ("general", "trading", "academic", "technical")
CHAR_LIMIT     = 2200
HALF_LIFE_DAYS = 30.0
WRITE_LEVELS   = ("auto", "confirm", "permanent")


class BuiltinMemoryProvider(MemoryProvider):

    name = "builtin"

    # مطلوبة لأن MemoryProvider يعرّفها abstractmethod — المزود المدمج متاح دائماً
    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str = "", **kwargs) -> None:
        MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
        user_file = MEMORIES_DIR / "USER.md"
        if not user_file.exists():
            user_file.write_text("# ملف المستخدم\n\n", encoding="utf-8")
        logger.info("BuiltinMemoryProvider initialized: %s", DB_PATH)

    def _init_db(self) -> None:
        con = self._con()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                context      TEXT    NOT NULL DEFAULT 'general',
                content      TEXT    NOT NULL,
                weight       REAL    NOT NULL DEFAULT 1.0,
                write_level  TEXT    NOT NULL DEFAULT 'auto',
                created_at   INTEGER NOT NULL,
                updated_at   INTEGER NOT NULL,
                recall_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_context ON memories(context);
            CREATE INDEX IF NOT EXISTS idx_weight  ON memories(weight DESC);
        """)
        con.commit(); con.close()

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con

    @staticmethod
    def _effective_weight(weight: float, updated_at: int) -> float:
        days  = (time.time() - updated_at) / 86400.0
        decay = math.exp(-math.log(2) * days / HALF_LIFE_DAYS)
        return weight * decay

    def system_prompt_block(self) -> str:
        con  = self._con()
        rows = con.execute(
            "SELECT context,content,weight,updated_at FROM memories ORDER BY weight DESC"
        ).fetchall()
        con.close()
        user_file = MEMORIES_DIR / "USER.md"
        user_text = user_file.read_text(encoding="utf-8").strip() if user_file.exists() else ""
        buckets: Dict[str, List[tuple]] = {c: [] for c in CONTEXTS}
        for row in rows:
            ew = self._effective_weight(row["weight"], row["updated_at"])
            buckets[row["context"]].append((ew, row["content"]))
        parts = []
        if user_text:
            parts.append(f"<user_profile>\n{user_text}\n</user_profile>")
        for ctx in CONTEXTS:
            entries = sorted(buckets[ctx], key=lambda x: x[0], reverse=True)
            if not entries: continue
            block = ""
            for _, content in entries:
                candidate = block + f"- {content}\n"
                if len(candidate) > CHAR_LIMIT: break
                block = candidate
            if block.strip():
                parts.append(f"<memory context=\"{ctx}\">\n{block}</memory>")
        return "\n\n".join(parts)

    def add_entry(self, content: str, context: str = "general",
                  write_level: str = "auto", weight: float = 1.0) -> Dict[str, Any]:
        if context not in CONTEXTS:
            return {"error": f"context غير صالح. المسموح: {CONTEXTS}"}
        if write_level not in WRITE_LEVELS:
            return {"error": f"write_level غير صالح. المسموح: {WRITE_LEVELS}"}
        if write_level == "confirm":
            return {
                "pending_confirm": True,
                "content": content, "context": context,
                "message": f"حفظ في [{context}]؟\n\"{content}\"\nرد بـ /confirm أو /discard",
            }
        now = int(time.time())
        con = self._con()
        con.execute(
            "INSERT INTO memories(context,content,weight,write_level,created_at,updated_at,recall_count)"
            " VALUES (?,?,?,?,?,?,0)",
            (context, content, weight, write_level, now, now),
        )
        con.commit(); con.close()
        logger.info("Memory added [%s|%s]: %s", context, write_level, content[:60])
        return {"ok": True, "context": context, "write_level": write_level}

    def update_weight(self, memory_id: int, delta: float = 0.5) -> Dict[str, Any]:
        now = int(time.time())
        con = self._con()
        con.execute(
            "UPDATE memories SET weight=weight+?,updated_at=?,recall_count=recall_count+1 WHERE id=?",
            (delta, now, memory_id),
        )
        con.commit(); con.close()
        return {"ok": True}

    def delete_entry(self, memory_id: int) -> Dict[str, Any]:
        con = self._con()
        row = con.execute("SELECT write_level FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            con.close(); return {"error": "الذكرى غير موجودة"}
        if row["write_level"] == "permanent":
            con.close(); return {"error": "لا يمكن حذف ذكرى permanent"}
        con.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        con.commit(); con.close()
        return {"ok": True}

    def prune_weak(self, threshold: float = 0.1) -> Dict[str, Any]:
        con  = self._con()
        rows = con.execute(
            "SELECT id,weight,updated_at,write_level FROM memories"
        ).fetchall()
        deleted = 0
        for row in rows:
            if row["write_level"] == "permanent": continue
            if self._effective_weight(row["weight"], row["updated_at"]) < threshold:
                con.execute("DELETE FROM memories WHERE id=?", (row["id"],))
                deleted += 1
        con.commit(); con.close()
        logger.info("prune_weak: deleted %d", deleted)
        return {"ok": True, "deleted": deleted}

    def list_by_context(self, context: str) -> List[Dict]:
        con  = self._con()
        rows = con.execute(
            "SELECT id,content,weight,updated_at,recall_count,write_level"
            " FROM memories WHERE context=? ORDER BY weight DESC", (context,)
        ).fetchall()
        con.close()
        return [{
            "id": r["id"], "content": r["content"],
            "weight": round(r["weight"], 3),
            "eff_weight": round(self._effective_weight(r["weight"], r["updated_at"]), 3),
            "recall_count": r["recall_count"], "write_level": r["write_level"],
        } for r in rows]

    def prefetch(self, query: str, session_id: str = "") -> str: return ""
    def sync_turn(self, user: str, assistant: str, session_id: str = "") -> None: pass
    def get_tool_schemas(self) -> list: return []
    def on_session_end(self, messages: list) -> None: pass
    def shutdown(self) -> None: logger.info("BuiltinMemoryProvider shutdown")
