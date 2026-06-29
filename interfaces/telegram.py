"""
Telegram Interface — بوت Telegram كامل يعمل عبر long-polling.

  • يقرأ TELEGRAM_BOT_TOKEN من ~/.cobweaverclaw/.env
  • long-polling (لا يحتاج webhook — يعمل على Android/Termux)
  • يمرّر الرسائل عبر الوكيل (مع سياق الذاكرة الكامل)
  • أوامر: /start /help /memory /clear

التشغيل:  python main.py telegram
"""
import os
import json
import asyncio
import urllib.request


class TelegramBot:
    """بوت Telegram لـ CoBWeaverClaw مع أوامر وذاكرة."""

    def __init__(self, agent, token: str):
        self.agent  = agent
        self.token  = token
        self.offset = 0
        self.base   = f"https://api.telegram.org/bot{token}"

    async def start(self):
        print("🕷️  CoBWeaverClaw Telegram Bot — يعمل (long-polling)")
        me = self._get_me()
        if me:
            print(f"   @{me.get('username','?')} جاهز. أرسل /start في تيليجرام.")
        while True:
            for update in await self._get_updates():
                await self._handle(update)
            await asyncio.sleep(1)

    def _get_me(self):
        try:
            with urllib.request.urlopen(f"{self.base}/getMe", timeout=10) as r:
                d = json.loads(r.read())
            return d.get("result") if d.get("ok") else None
        except Exception:
            return None

    async def _get_updates(self) -> list:
        try:
            url = f"{self.base}/getUpdates?offset={self.offset}&timeout=30"
            with urllib.request.urlopen(url, timeout=35) as r:
                data = json.loads(r.read())
            updates = data.get("result", [])
            if updates:
                self.offset = updates[-1]["update_id"] + 1
            return updates
        except Exception:
            return []

    async def _handle(self, update: dict):
        msg = update.get("message", {})
        if not msg:
            return
        text    = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        # معرّف ثابت حتى تظهر محادثة تيليجرام في لوحة التحكم
        user_id = "telegram"
        if not text:
            return

        # ── الأوامر ──
        if text.startswith("/"):
            await self._command(text, chat_id, user_id)
            return

        await self._send(chat_id, "🕷️ ...")
        try:
            response = await self.agent.process(text, user_id)
            await self._send(chat_id, response)
        except Exception as e:
            await self._send(chat_id, f"❌ خطأ: {str(e)}")

    async def _command(self, text: str, chat_id: int, user_id: str):
        cmd = text.split()[0].lower().lstrip("/").split("@")[0]
        if cmd == "start":
            await self._send(chat_id,
                "🕷️ أهلاً بك في CoBWeaverClaw!\n"
                "وكيلك الشخصي الذي يتذكّر ويتعلّم.\n\n"
                "اكتب أي رسالة وسأردّ عليك.\n"
                "الأوامر: /help /memory /clear")
        elif cmd == "help":
            await self._send(chat_id,
                "الأوامر المتاحة:\n"
                "/start — البداية\n"
                "/help — هذه القائمة\n"
                "/memory — إحصائيات الذاكرة\n"
                "/clear — مسح ذاكرة الجلسة (Working)")
        elif cmd == "memory":
            try:
                s = self.agent.memory.stats(user_id)
                await self._send(chat_id,
                    "🧠 الذاكرة:\n"
                    f"• العاملة (Working): {s['working_memory_count']}\n"
                    f"• الحلقات (Episodic): {s['episodes']}\n"
                    f"• المعرفة الأساسية (Core): {s['core_facts']}")
            except Exception as e:
                await self._send(chat_id, f"❌ {e}")
        elif cmd == "clear":
            try:
                self.agent.memory.clear("working", user_id)
                await self._send(chat_id, "✅ مُسحت ذاكرة الجلسة (Working).")
            except Exception as e:
                await self._send(chat_id, f"❌ {e}")
        else:
            await self._send(chat_id, "أمر غير معروف. جرّب /help")

    async def _send(self, chat_id: int, text: str):
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(f"{self.base}/sendMessage", data=payload,
              headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            pass


def _load_token() -> str:
    """يقرأ TELEGRAM_BOT_TOKEN من البيئة ثم من ~/.cobweaverclaw/.env و config.yaml."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if tok:
        return tok
    env_path = os.path.expanduser("~/.cobweaverclaw/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN=") and "=" in line:
                return line.split("=", 1)[1].strip()
    return ""


def run_telegram(config: dict):
    """ينشئ الوكيل ويشغّل بوت تيليجرام (يُستدعى من main.py telegram)."""
    import sys
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, base)
    from core.agent import CoBWeaverClaw

    token = _load_token() or config.get("interfaces", {}).get("telegram", {}).get("token", "")
    if not token:
        print("❌ لا يوجد TELEGRAM_BOT_TOKEN.")
        print("   أضِفه عبر: python setup_wizard.py --channel  (أو في ~/.cobweaverclaw/.env)")
        return
    agent = CoBWeaverClaw(config)
    bot   = TelegramBot(agent, token)
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n   تم إيقاف بوت تيليجرام.")


_BG_STARTED = False

def start_in_background(config: dict) -> bool:
    """
    يشغّل بوت تيليجرام في خيط خلفي مع البوابة (بوابة اتصال دائمة).
    يُعيد True إن بدأ فعلاً. آمن للاستدعاء مرّة واحدة.
    """
    global _BG_STARTED
    if _BG_STARTED:
        return True
    token = _load_token() or config.get("interfaces", {}).get("telegram", {}).get("token", "")
    if not token:
        return False
    import threading

    def _run():
        try:
            import sys
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, base)
            from core.agent import CoBWeaverClaw
            agent = CoBWeaverClaw(config)
            bot = TelegramBot(agent, token)
            asyncio.run(bot.start())
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    _BG_STARTED = True
    print("🤖 بوت تيليجرام يعمل في الخلفية (بوابة اتصال).")
    return True
