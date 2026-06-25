"""
SQLite Store — Layer 1: Permanent facts and conversation history.
"""
import sqlite3
import json
import os
from datetime import datetime


class SQLiteStore:
    """
    Persistent memory using SQLite.
    Stores facts, preferences, and conversation history.
    Never deletes — compresses when old.
    """

    def __init__(self, config: dict):
        db_path = config.get("sqlite_path", os.path.expanduser("~/.cobweaverclaw/memory.db"))
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                created   TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, key)
            );
            CREATE TABLE IF NOT EXISTS history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                message   TEXT NOT NULL,
                response  TEXT NOT NULL,
                lang      TEXT DEFAULT 'en',
                created   TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS skills_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                skill     TEXT NOT NULL,
                success   INTEGER DEFAULT 1,
                created   TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    async def get_context(self, user_id: str, query: str) -> dict:
        """Retrieve relevant context for a user query."""
        facts = dict(self.conn.execute(
            "SELECT key, value FROM facts WHERE user_id=?", (user_id,)
        ).fetchall())

        history = self.conn.execute(
            "SELECT message, response FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user_id,)
        ).fetchall()

        return {"facts": facts, "history": list(reversed(history))}

    async def save(self, user_id: str, message: str, response: str, lang: str = "en"):
        """Save a conversation turn."""
        self.conn.execute(
            "INSERT INTO history (user_id, message, response, lang) VALUES (?,?,?,?)",
            (user_id, message, response, lang)
        )
        self.conn.commit()

    async def set_fact(self, user_id: str, key: str, value: str):
        """Store a permanent fact about a user."""
        self.conn.execute(
            "INSERT OR REPLACE INTO facts (user_id, key, value) VALUES (?,?,?)",
            (user_id, key, value)
        )
        self.conn.commit()
