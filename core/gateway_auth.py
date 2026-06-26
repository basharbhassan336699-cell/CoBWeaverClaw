"""
Gateway Auth — حماية بوابة التحكم بتوكين عشوائي آمن.
يتبع أسلوب OpenClaw: توكين عشوائي حقيقي (secrets), يُحفظ محلياً,
يُسترجع بأمر, ويُحمى به الوصول للوحة التحكم.

لا JWT مُوقّع يدوياً — توكين عشوائي خالص أبسط وأأمن لهذه الحالة.
"""
import os
import json
import secrets
import hashlib
import hmac
from pathlib import Path
from datetime import datetime


class GatewayAuth:
    """
    يدير توكين البوابة:
    - يولّد توكيناً عشوائياً (256-bit) عند أول تشغيل
    - يحفظه في ملف بصلاحيات مقيّدة (0600)
    - يسترجعه بأمر
    - يتحقق منه بمقارنة ثابتة الزمن (timing-safe)
    """

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or os.path.expanduser("~/.cobweaverclaw"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.config_dir / "gateway_token"

    def get_or_create_token(self) -> str:
        """يُعيد التوكين الحالي أو ينشئ واحداً جديداً إن لم يوجد."""
        if self.token_file.exists():
            token = self.token_file.read_text().strip()
            if token:
                return token
        return self._generate_new_token()

    def _generate_new_token(self) -> str:
        """يولّد توكيناً عشوائياً 256-bit ويحفظه بصلاحيات مقيّدة."""
        token = secrets.token_hex(32)  # 64 hex chars = 256 bits
        self.token_file.write_text(token)
        # صلاحيات مقيّدة: المالك فقط يقرأ/يكتب
        try:
            os.chmod(self.token_file, 0o600)
        except Exception:
            pass  # بعض أنظمة الملفات لا تدعم chmod (مثل بعض حالات Android)
        return token

    def regenerate_token(self) -> str:
        """يُلغي التوكين الحالي وينشئ واحداً جديداً (عند الاشتباه بتسرّب)."""
        return self._generate_new_token()

    def verify(self, provided_token: str) -> bool:
        """يتحقق من توكين بمقارنة ثابتة الزمن (تمنع timing attacks)."""
        if not provided_token:
            return False
        actual = self.get_or_create_token()
        return hmac.compare_digest(provided_token, actual)

    def get_dashboard_url(self, host: str = "127.0.0.1", port: int = 8787) -> str:
        """يبني رابط لوحة التحكم مع التوكين."""
        token = self.get_or_create_token()
        return f"http://{host}:{port}/#token={token}"
