"""
SQLite Store — Three-layer memory system.

  LAYER 1  Working Memory   — آخر N رسالة من الجلسة الحالية (history)
  LAYER 2  Episodic Memory  — ملخّصات المحادثات السابقة (episodes)
  LAYER 3  Core Knowledge   — تفضيلات وحقائق دائمة عن المستخدم (facts)

كل البيانات في ~/.cobweaverclaw/memory.db — تبقى رغم git clone/pull.
This is the core differentiator vs Hermes (forgets) and OpenClaw (drifts).
"""
import sqlite3
import os
import re
from collections import Counter
from datetime import datetime


# كلمات شائعة تُستبعد عند استخراج المواضيع (عربي + إنجليزي)
_STOPWORDS = {
    "the", "and", "for", "you", "are", "with", "that", "this", "what",
    "how", "can", "from", "have", "your", "about", "please", "would",
    "في", "من", "على", "إلى", "عن", "هذا", "هذه", "هل", "ما", "كيف",
    "أن", "أنت", "أنا", "هو", "هي", "مع", "كان", "يكون", "الذي", "التي",
}


class SQLiteStore:
    """
    Persistent three-layer memory using SQLite.
    Never auto-deletes Core Knowledge — only manual clear.
    """

    def __init__(self, config: dict):
        db_path = config.get("sqlite_path", "~/.cobweaverclaw/memory.db")
        db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.memory_size = int(config.get("memory_size", 20))
        self._init_schema()
        self._self_heal()      # تنظيف تلقائي للذاكرة عند كل تشغيل

    def _self_heal(self):
        """
        صيانة تلقائية: يحذف "اهتمامات" ضوضائية رُفعت سابقاً للمعرفة الأساسية
        (أرقام مثل 2001، أو كلمات قصيرة جداً) حتى لا تقيّد الوكيل. يعمل بصمت.
        """
        try:
            rows = self.conn.execute(
                "SELECT id, key FROM facts WHERE key LIKE 'interest:%'").fetchall()
            for r in rows:
                topic = r["key"].split("interest:", 1)[-1]
                if topic.isdigit() or len(topic) < 4:
                    self.conn.execute("DELETE FROM facts WHERE id=?", (r["id"],))
            self.conn.execute("DELETE FROM interests WHERE LENGTH(topic) < 4 OR topic GLOB '[0-9]*'")
            self.conn.commit()
        except Exception:
            pass

    def _init_schema(self):
        self.conn.executescript("""
            -- LAYER 1 + raw log: Working Memory (last N of current session)
            CREATE TABLE IF NOT EXISTS history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                message   TEXT NOT NULL,
                response  TEXT NOT NULL,
                lang      TEXT DEFAULT 'en',
                created   TEXT DEFAULT (datetime('now'))
            );
            -- LAYER 2: Episodic Memory (summaries of past conversations)
            CREATE TABLE IF NOT EXISTS episodes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                topic     TEXT NOT NULL,
                key_facts TEXT NOT NULL,
                outcome   TEXT DEFAULT '',
                keywords  TEXT DEFAULT '',
                created   TEXT DEFAULT (datetime('now'))
            );
            -- LAYER 3: Core Knowledge (permanent user facts/preferences/rules)
            CREATE TABLE IF NOT EXISTS facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                created   TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, key)
            );
            -- topic interest counters (feeds self-learning into Core Knowledge)
            CREATE TABLE IF NOT EXISTS interests (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                topic     TEXT NOT NULL,
                hits      INTEGER DEFAULT 1,
                created   TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, topic)
            );
        """)
        self.conn.commit()

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _keywords(text: str, limit: int = 8) -> list:
        """يستخرج كلمات مفتاحية (للتشابه والمواضيع)."""
        words = re.findall(r"[A-Za-z؀-ۿ]{3,}", (text or "").lower())
        words = [w for w in words if w not in _STOPWORDS]
        common = [w for w, _ in Counter(words).most_common(limit)]
        return common

    # ── retrieval: build full context (all 3 layers) ─────────
    async def get_context(self, user_id: str, query: str) -> dict:
        """
        يبني السياق الكامل للرسالة الحالية:
          - facts    : Core Knowledge (Layer 3)
          - history  : Working Memory  (Layer 1, آخر N)
          - episodes : Episodic Memory المتعلّقة بالموضوع (Layer 2)
        """
        facts = dict(self.conn.execute(
            "SELECT key, value FROM facts WHERE user_id=?", (user_id,)
        ).fetchall())

        rows = self.conn.execute(
            "SELECT message, response FROM history WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, self.memory_size)
        ).fetchall()
        history = [(r["message"], r["response"]) for r in reversed(rows)]

        episodes = self._find_relevant_episodes(user_id, query)

        return {"facts": facts, "history": history, "episodes": episodes}

    def _find_relevant_episodes(self, user_id: str, query: str, limit: int = 3) -> list:
        """يجلب ملخّصات سابقة متعلّقة بموضوع الرسالة (تشابه كلمات مفتاحية)."""
        rows = self.conn.execute(
            "SELECT topic, key_facts, outcome, keywords FROM episodes "
            "WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user_id,)
        ).fetchall()
        if not rows:
            return []
        q_kw = set(self._keywords(query))
        scored = []
        for r in rows:
            ep_kw = set((r["keywords"] or "").split(","))
            overlap = len(q_kw & ep_kw)
            if overlap > 0:
                scored.append((overlap, {
                    "topic": r["topic"],
                    "key_facts": r["key_facts"],
                    "outcome": r["outcome"],
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    # ── writes ───────────────────────────────────────────────
    async def save(self, user_id: str, message: str, response: str, lang: str = "en"):
        """يحفظ دورة محادثة في Working Memory ويُحدّث اهتمامات المستخدم."""
        self.conn.execute(
            "INSERT INTO history (user_id, message, response, lang) VALUES (?,?,?,?)",
            (user_id, message, response, lang)
        )
        self.conn.commit()
        self._track_interest(user_id, message)

    async def set_fact(self, user_id: str, key: str, value: str):
        """يخزّن حقيقة دائمة في Core Knowledge (Layer 3)."""
        self.conn.execute(
            "INSERT OR REPLACE INTO facts (user_id, key, value) VALUES (?,?,?)",
            (user_id, key, value)
        )
        self.conn.commit()

    # ── LAYER 2: auto-summarization ──────────────────────────
    async def maybe_summarize(self, user_id: str) -> bool:
        """
        بعد كل (memory_size) رسالة جديدة منذ آخر ملخّص، يُلخّص الجلسة
        ويحفظها في Episodic Memory. يعمل في الخلفية دون مقاطعة المستخدم.
        """
        total = self.conn.execute(
            "SELECT COUNT(*) AS c FROM history WHERE user_id=?", (user_id,)
        ).fetchone()["c"]
        summarized = self.conn.execute(
            "SELECT COUNT(*) AS c FROM episodes WHERE user_id=?", (user_id,)
        ).fetchone()["c"]
        # كل دفعة memory_size من الرسائل = حلقة جديدة
        if total >= (summarized + 1) * self.memory_size:
            self._summarize_recent(user_id, self.memory_size)
            return True
        return False

    def _summarize_recent(self, user_id: str, n: int):
        """تلخيص استخراجي خفيف (بلا نموذج) — موضوع + حقائق + نتيجة."""
        rows = self.conn.execute(
            "SELECT message, response FROM history WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, n)
        ).fetchall()
        if not rows:
            return
        turns = list(reversed(rows))
        all_text = " ".join(r["message"] for r in turns)
        kws = self._keywords(all_text, limit=8)
        topic = "، ".join(kws[:3]) if kws else "محادثة عامة"
        key_facts = " | ".join(r["message"][:80] for r in turns[:5])
        outcome = turns[-1]["response"][:120] if turns else ""
        self.conn.execute(
            "INSERT INTO episodes (user_id, topic, key_facts, outcome, keywords) "
            "VALUES (?,?,?,?,?)",
            (user_id, topic, key_facts, outcome, ",".join(kws))
        )
        self.conn.commit()

    def add_episode(self, user_id: str, topic: str, key_facts: str,
                    outcome: str = "", keywords: str = ""):
        """إضافة ملخّص محادثة يدوياً/من نموذج إلى Episodic Memory."""
        if not keywords:
            keywords = ",".join(self._keywords(topic + " " + key_facts))
        self.conn.execute(
            "INSERT INTO episodes (user_id, topic, key_facts, outcome, keywords) "
            "VALUES (?,?,?,?,?)",
            (user_id, topic, key_facts, outcome, keywords)
        )
        self.conn.commit()

    # ── LAYER 3: self-learning ───────────────────────────────
    def _track_interest(self, user_id: str, message: str):
        """
        يعدّ تكرار المواضيع. إذا ظهر موضوع 3+ مرات يُرفَع تلقائياً
        إلى Core Knowledge كاهتمام للمستخدم (تعلّم الأنماط مع الوقت).
        """
        # تجاهل الأرقام والكلمات القصيرة جداً (تمنع ضوضاء مثل 2001 / رقم)
        for kw in self._keywords(message, limit=5):
            if kw.isdigit() or len(kw) < 4:
                continue
            self.conn.execute(
                "INSERT INTO interests (user_id, topic, hits) VALUES (?,?,1) "
                "ON CONFLICT(user_id, topic) DO UPDATE SET hits = hits + 1",
                (user_id, kw)
            )
        self.conn.commit()
        # رفع الاهتمامات المتكرّرة (5+) إلى Core Knowledge (عتبة أعلى = أقل ضوضاء)
        hot = self.conn.execute(
            "SELECT topic, hits FROM interests WHERE user_id=? AND hits >= 5",
            (user_id,)
        ).fetchall()
        for r in hot:
            self.conn.execute(
                "INSERT OR REPLACE INTO facts (user_id, key, value) VALUES (?,?,?)",
                (user_id, f"interest:{r['topic']}",
                 f"يهتمّ المستخدم بـ {r['topic']} (تكرّر {r['hits']} مرة)")
            )
        if hot:
            self.conn.commit()

    # ── stats & maintenance ──────────────────────────────────
    # ── conversations (sessions) ─────────────────────────────
    def list_conversations(self, prefix: str = "conv:") -> list:
        """يسرد محادثات اللوحة السابقة (id + عنوان من أول رسالة + العدد)."""
        rows = self.conn.execute(
            "SELECT user_id, MAX(created) AS last, COUNT(*) AS n, "
            " (SELECT message FROM history h2 WHERE h2.user_id = history.user_id "
            "  ORDER BY id ASC LIMIT 1) AS title "
            "FROM history WHERE user_id = ? OR user_id LIKE ? "
            "GROUP BY user_id ORDER BY last DESC",
            ("dashboard", prefix + "%")).fetchall()
        return [{"id": r["user_id"],
                 "title": (r["title"] or "محادثة").strip()[:48],
                 "count": r["n"], "last": r["last"]} for r in rows]

    def conversation_messages(self, conv_id: str, limit: int = 200) -> list:
        """يُعيد كل رسائل محادثة معيّنة بالترتيب الزمني."""
        rows = self.conn.execute(
            "SELECT message, response, created FROM history WHERE user_id = ? "
            "ORDER BY id ASC LIMIT ?", (conv_id, limit)).fetchall()
        return [{"message": r["message"], "response": r["response"],
                 "time": r["created"]} for r in rows]

    def stats(self, user_id: str = None) -> dict:
        """إحصائيات الطبقات الثلاث."""
        if user_id:
            w = self.conn.execute(
                "SELECT COUNT(*) AS c FROM history WHERE user_id=?", (user_id,)).fetchone()["c"]
            e = self.conn.execute(
                "SELECT COUNT(*) AS c FROM episodes WHERE user_id=?", (user_id,)).fetchone()["c"]
            f = self.conn.execute(
                "SELECT COUNT(*) AS c FROM facts WHERE user_id=?", (user_id,)).fetchone()["c"]
        else:
            w = self.conn.execute("SELECT COUNT(*) AS c FROM history").fetchone()["c"]
            e = self.conn.execute("SELECT COUNT(*) AS c FROM episodes").fetchone()["c"]
            f = self.conn.execute("SELECT COUNT(*) AS c FROM facts").fetchone()["c"]
        return {"working_memory_count": w, "episodes": e, "core_facts": f}

    def clear(self, layer: str = "working", user_id: str = None) -> dict:
        """يمسح طبقة محدّدة: working | episodic | core | all."""
        tables = {"working": ["history"], "episodic": ["episodes"],
                  "core": ["facts", "interests"],
                  "all": ["history", "episodes", "facts", "interests"]}
        cleared = []
        for t in tables.get(layer, []):
            if user_id:
                self.conn.execute(f"DELETE FROM {t} WHERE user_id=?", (user_id,))
            else:
                self.conn.execute(f"DELETE FROM {t}")
            cleared.append(t)
        self.conn.commit()
        return {"cleared": cleared, "layer": layer}
