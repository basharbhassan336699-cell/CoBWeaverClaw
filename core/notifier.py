"""
Notifier — إرسال الإشعارات عبر Telegram أو CLI.
يُستخدم لإشعارات التحديث والأجهزة الجديدة.
"""
import json
import urllib.request
import os


class TelegramNotifier:
    """
    يرسل إشعارات مباشرة لـ Telegram.
    يحتاج: BOT_TOKEN + OWNER_CHAT_ID في الإعدادات.
    """

    def __init__(self, bot_token: str, chat_id: str):
        self.token   = bot_token
        self.chat_id = chat_id
        self.base    = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        """إرسال رسالة نصية."""
        payload = json.dumps({
            "chat_id":    self.chat_id,
            "text":       message,
            "parse_mode": parse_mode,
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False

    async def send_new_device_alert(self, device_info: dict) -> bool:
        """إشعار بجهاز جديد تم تسجيله."""
        msg = (
            f"🕷️ *جهاز جديد تم تسجيله*\n\n"
            f"📱 الجهاز: `{device_info.get('device_name', 'Unknown')}`\n"
            f"🖥️ المنصة: `{device_info.get('platform', 'Unknown')}`\n"
            f"💻 النظام: `{device_info.get('os_info', 'Unknown')}`\n"
            f"🌐 Hostname: `{device_info.get('hostname', 'Unknown')}`\n"
            f"🆔 Device ID: `{device_info.get('device_id', 'Unknown')}`\n"
            f"📅 التوقيت: `{device_info.get('registered', 'Unknown')}`\n\n"
            f"⚠️ إذا لم تكن أنت، ألغِ هذا الجهاز:\n"
            f"`agent token revoke {device_info.get('device_id', '')}`"
        )
        return await self.send(msg)

    async def send_update_alert(self, version: str, changelog: str, url: str) -> bool:
        """إشعار بتحديث جديد."""
        msg = (
            f"🔔 *تحديث جديد متاح!*\n\n"
            f"📦 الإصدار: `{version}`\n"
            f"📝 التغييرات:\n{changelog[:300]}\n\n"
            f"🔗 {url}\n\n"
            f"⚡ للتحديث الآن:\n`agent update`"
        )
        return await self.send(msg)


class CLINotifier:
    """إشعارات عبر الطرفية (للاستخدام بدون Telegram)."""

    async def send(self, message: str) -> bool:
        clean = message.replace("*", "").replace("`", "")
        print(f"\n🔔 إشعار:\n{clean}\n")
        return True
