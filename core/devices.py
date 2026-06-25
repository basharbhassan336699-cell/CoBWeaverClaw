"""
Device Registry — كشف وتسجيل الأجهزة المتصلة.
يسجل كل جهاز تلقائياً عند أول تشغيل ويحفظ بياناته.
"""
import sqlite3
import hashlib
import platform
import socket
import os
import json
from datetime import datetime


class DeviceRegistry:
    """
    يكشف الجهاز الحالي ويسجّله في قاعدة البيانات.
    يُبلّغ المالك بأي جهاز جديد يتصل.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/.cobweaverclaw/devices.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id    TEXT UNIQUE NOT NULL,
                device_name  TEXT,
                platform     TEXT,
                os_info      TEXT,
                hostname     TEXT,
                first_seen   TEXT DEFAULT (datetime('now')),
                last_seen    TEXT DEFAULT (datetime('now')),
                is_active    INTEGER DEFAULT 1,
                token_hash   TEXT,
                notes        TEXT
            );
            CREATE TABLE IF NOT EXISTS device_sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id    TEXT NOT NULL,
                started_at   TEXT DEFAULT (datetime('now')),
                ended_at     TEXT,
                ip_hash      TEXT
            );
        """)
        self.conn.commit()

    def get_device_id(self) -> str:
        """
        ينشئ معرّفاً فريداً للجهاز من خصائصه الثابتة.
        لا يتغيّر حتى لو أُعيد التثبيت.
        """
        parts = [
            platform.node(),           # اسم الجهاز
            platform.machine(),        # نوع المعالج
            platform.system(),         # نظام التشغيل
            str(os.getuid()) if hasattr(os, 'getuid') else "0",
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get_device_info(self) -> dict:
        """يجمع معلومات الجهاز الكاملة."""
        from core.platform import PlatformAdapter
        p = PlatformAdapter()

        info = {
            "device_id":   self.get_device_id(),
            "device_name": platform.node() or "Unknown",
            "platform":    p.platform,
            "os_info":     f"{platform.system()} {platform.release()}",
            "hostname":    socket.gethostname(),
            "python":      platform.python_version(),
            "arch":        platform.machine(),
        }
        return info

    def register(self, token_hash: str = None) -> dict:
        """
        يسجّل الجهاز الحالي.
        يُعيد: معلومات الجهاز + هل هو جديد؟
        """
        info = self.get_device_info()
        did  = info["device_id"]

        existing = self.conn.execute(
            "SELECT * FROM devices WHERE device_id=?", (did,)
        ).fetchone()

        is_new = existing is None

        if is_new:
            self.conn.execute("""
                INSERT INTO devices
                (device_id, device_name, platform, os_info, hostname, token_hash)
                VALUES (?,?,?,?,?,?)
            """, (did, info["device_name"], info["platform"],
                  info["os_info"], info["hostname"], token_hash))
        else:
            self.conn.execute("""
                UPDATE devices SET last_seen=datetime('now'), is_active=1
                WHERE device_id=?
            """, (did,))

        self.conn.execute(
            "INSERT INTO device_sessions (device_id) VALUES (?)", (did,)
        )
        self.conn.commit()

        info["is_new"]     = is_new
        info["registered"] = datetime.now().isoformat()
        return info

    def list_devices(self) -> list:
        """قائمة بكل الأجهزة المسجّلة."""
        rows = self.conn.execute("""
            SELECT device_id, device_name, platform, os_info,
                   hostname, first_seen, last_seen, is_active
            FROM devices ORDER BY last_seen DESC
        """).fetchall()
        return [
            {
                "device_id":   r[0],
                "device_name": r[1],
                "platform":    r[2],
                "os_info":     r[3],
                "hostname":    r[4],
                "first_seen":  r[5],
                "last_seen":   r[6],
                "is_active":   bool(r[7]),
            }
            for r in rows
        ]

    def revoke_device(self, device_id: str) -> bool:
        """إلغاء تفعيل جهاز معيّن."""
        self.conn.execute(
            "UPDATE devices SET is_active=0 WHERE device_id=?", (device_id,)
        )
        self.conn.commit()
        return True

    def get_current_device(self) -> dict:
        """معلومات الجهاز الحالي فقط."""
        did = self.get_device_id()
        row = self.conn.execute(
            "SELECT * FROM devices WHERE device_id=?", (did,)
        ).fetchone()
        return self.get_device_info() if not row else {
            "device_id":  row[1],
            "device_name": row[2],
            "platform":   row[3],
            "os_info":    row[4],
            "hostname":   row[5],
            "first_seen": row[6],
            "last_seen":  row[7],
        }
