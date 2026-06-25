"""
Updater — نظام التحديثات التلقائية مع إشعارات.
يتحقق من GitHub ويُبلّغ المستخدم بأي تحديث جديد.
"""
import json
import urllib.request
import os
import sqlite3
from datetime import datetime, timedelta


CURRENT_VERSION = "0.1.0"
GITHUB_REPO     = "basharbhassan336699-cell/CoBWeaverClaw"


class Updater:
    """
    يتحقق دورياً من وجود تحديثات جديدة على GitHub
    ويُرسل إشعاراً عبر Telegram أو CLI.
    """

    def __init__(self, config: dict = None, notifier=None):
        self.config        = config or {}
        self.notifier      = notifier      # TelegramNotifier أو CLINotifier
        self.github_token  = os.environ.get("GITHUB_TOKEN", "")
        self.check_interval_hours = self.config.get("update_check_interval_hours", 6)
        self.db_path       = os.path.expanduser("~/.cobweaverclaw/updates.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn          = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS update_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                version      TEXT,
                checked_at   TEXT DEFAULT (datetime('now')),
                notified     INTEGER DEFAULT 0,
                installed    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS last_check (
                id           INTEGER PRIMARY KEY,
                checked_at   TEXT
            );
        """)
        self.conn.commit()

    def get_latest_version(self) -> dict | None:
        """
        يجلب آخر إصدار من GitHub Releases API.
        يعيد dict بالبيانات أو None عند الفشل.
        """
        url     = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            return {
                "version":      data.get("tag_name", "").lstrip("v"),
                "name":         data.get("name", ""),
                "body":         data.get("body", "")[:500],
                "published_at": data.get("published_at", ""),
                "url":          data.get("html_url", ""),
            }
        except Exception:
            return None

    def get_latest_commit(self) -> dict | None:
        """
        يجلب آخر commit من GitHub (للنسخ التطويرية).
        """
        url     = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            commit = data.get("commit", {})
            return {
                "sha":       data.get("sha", "")[:8],
                "message":   commit.get("message", "").split("\n")[0],
                "author":    commit.get("author", {}).get("name", ""),
                "date":      commit.get("author", {}).get("date", ""),
                "url":       data.get("html_url", ""),
            }
        except Exception:
            return None

    def is_update_available(self) -> bool:
        """هل يوجد تحديث أحدث من النسخة الحالية؟"""
        latest = self.get_latest_version()
        if not latest:
            return False
        return self._version_gt(latest["version"], CURRENT_VERSION)

    def _version_gt(self, v1: str, v2: str) -> bool:
        """هل v1 أحدث من v2؟"""
        try:
            p1 = [int(x) for x in v1.split(".")]
            p2 = [int(x) for x in v2.split(".")]
            return p1 > p2
        except Exception:
            return v1 != v2

    def should_check(self) -> bool:
        """هل حان وقت فحص التحديثات؟"""
        row = self.conn.execute(
            "SELECT checked_at FROM last_check WHERE id=1"
        ).fetchone()
        if not row:
            return True
        last = datetime.fromisoformat(row[0])
        return datetime.utcnow() - last > timedelta(hours=self.check_interval_hours)

    def mark_checked(self):
        """تسجيل وقت آخر فحص."""
        self.conn.execute("""
            INSERT OR REPLACE INTO last_check (id, checked_at)
            VALUES (1, datetime('now'))
        """)
        self.conn.commit()

    async def check_and_notify(self) -> dict:
        """
        يتحقق من التحديثات ويُرسل إشعاراً إن وُجد.
        يُستدعى تلقائياً من heartbeat.
        """
        if not self.should_check():
            return {"checked": False, "reason": "too_soon"}

        self.mark_checked()

        # فحص آخر Release
        latest  = self.get_latest_version()
        # فحص آخر commit (للتطوير)
        commit  = self.get_latest_commit()

        result = {
            "checked":          True,
            "current_version":  CURRENT_VERSION,
            "latest_version":   latest["version"] if latest else None,
            "latest_commit":    commit["sha"] if commit else None,
            "update_available": False,
            "notified":         False,
        }

        # هل يوجد إصدار جديد؟
        if latest and self._version_gt(latest["version"], CURRENT_VERSION):
            result["update_available"] = True
            msg = self._build_update_message(latest, commit)

            # إرسال الإشعار
            if self.notifier:
                await self.notifier.send(msg)
                result["notified"] = True

            # تسجيل في قاعدة البيانات
            self.conn.execute(
                "INSERT INTO update_log (version, notified) VALUES (?,1)",
                (latest["version"],)
            )
            self.conn.commit()

        elif commit:
            # إشعار بـ commit جديد (للمطور)
            already = self.conn.execute(
                "SELECT id FROM update_log WHERE version=?", (commit["sha"],)
            ).fetchone()
            if not already:
                msg = self._build_commit_message(commit)
                if self.notifier:
                    await self.notifier.send(msg)
                    result["notified"] = True
                self.conn.execute(
                    "INSERT INTO update_log (version, notified) VALUES (?,1)",
                    (commit["sha"],)
                )
                self.conn.commit()

        return result

    def _build_update_message(self, latest: dict, commit: dict = None) -> str:
        msg = (
            f"🕷️ *CoBWeaverClaw — تحديث جديد!*\n\n"
            f"📦 الإصدار الجديد: `{latest['version']}`\n"
            f"📌 الحالي: `{CURRENT_VERSION}`\n"
            f"📅 تاريخ النشر: {latest['published_at'][:10]}\n\n"
            f"📝 *ملخص التغييرات:*\n{latest['body']}\n\n"
            f"🔗 {latest['url']}\n\n"
            f"⚡ للتحديث:\n`agent update`"
        )
        return msg

    def _build_commit_message(self, commit: dict) -> str:
        msg = (
            f"🕷️ *CoBWeaverClaw — commit جديد*\n\n"
            f"🔖 `{commit['sha']}`\n"
            f"💬 {commit['message']}\n"
            f"👤 {commit['author']}\n"
            f"📅 {commit['date'][:10]}\n\n"
            f"🔗 {commit['url']}"
        )
        return msg

    def get_update_history(self) -> list:
        """سجل التحديثات السابقة."""
        rows = self.conn.execute(
            "SELECT version, checked_at, notified, installed FROM update_log ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return [
            {"version": r[0], "date": r[1], "notified": bool(r[2]), "installed": bool(r[3])}
            for r in rows
        ]
