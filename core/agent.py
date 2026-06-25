"""
CoBWeaverClaw — Main Agent Loop
The heart of the agent.
"""
import asyncio
import logging
from core.router import Router
from core.platform import PlatformAdapter
from core.devices import DeviceRegistry
from core.updater import Updater
from memory.sqlite_store import SQLiteStore
from brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


class CoBWeaverClaw:
    """
    Main agent class. Receives input, routes to appropriate
    module, returns response. Runs continuously via heartbeat.
    """

    def __init__(self, config: dict):
        self.config   = config
        self.platform = PlatformAdapter()
        self.memory   = SQLiteStore(config.get("memory", {}))
        self.brain    = ModelRouter(config.get("brain", {}))
        self.router   = Router(self)
        self.devices  = DeviceRegistry(
            config.get("devices", {}).get("db_path")
        )
        self.running  = False

        # Notifier (Telegram or CLI)
        self.notifier = self._init_notifier()
        self.updater  = Updater(config.get("updates", {}), self.notifier)

        logger.info(f"CoBWeaverClaw initialized on {self.platform.platform}")

    def _init_notifier(self):
        """ينشئ notifier حسب الإعدادات."""
        tg_cfg  = self.config.get("interfaces", {}).get("telegram", {})
        token   = tg_cfg.get("token", "")
        chat_id = tg_cfg.get("owner_chat_id", "")
        if token and chat_id:
            from core.notifier import TelegramNotifier
            return TelegramNotifier(token, chat_id)
        from core.notifier import CLINotifier
        return CLINotifier()

    async def startup(self):
        """
        يُشغَّل مرة واحدة عند بدء الوكيل:
        1. يسجّل الجهاز الحالي
        2. يُبلّغ بجهاز جديد إن كان كذلك
        3. يفحص التحديثات فوراً
        """
        # تسجيل الجهاز
        dev_cfg = self.config.get("devices", {})
        if dev_cfg.get("auto_register", True):
            info = self.devices.register()
            logger.info(f"Device: {info['device_id']} ({info['platform']})")

            if info.get("is_new") and dev_cfg.get("notify_new_device", True):
                await self.notifier.send_new_device_alert(info)
                logger.info("New device alert sent")

        # فحص التحديثات عند البدء
        if self.config.get("updates", {}).get("auto_check", True):
            update_result = await self.updater.check_and_notify()
            if update_result.get("update_available"):
                logger.info(f"Update available: {update_result['latest_version']}")

    async def process(self, message: str, user_id: str, lang: str = "auto") -> str:
        """
        Main entry point for all user messages.
        """
        if lang == "auto":
            lang = self._detect_language(message)

        context  = await self.memory.get_context(user_id, message)
        response = await self.router.handle(message, context, lang)
        await self.memory.save(user_id, message, response)
        return response

    async def heartbeat(self):
        """Continuous background monitoring loop."""
        interval = self.platform.get_heartbeat_interval()
        while self.running:
            await self._run_heartbeat_tasks()
            await asyncio.sleep(interval)

    async def _run_heartbeat_tasks(self):
        """Tasks that run on each heartbeat tick."""
        logger.debug("Heartbeat tick")
        # فحص التحديثات دورياً
        tasks = self.config.get("heartbeat", {}).get("tasks", [])
        if "check_updates" in tasks:
            await self.updater.check_and_notify()

    def _detect_language(self, text: str) -> str:
        arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
        if any(c in arabic_chars for c in text):
            return "ar"
        return "en"

    async def start(self):
        self.running = True
        await self.startup()
        logger.info("CoBWeaverClaw started")
        await self.heartbeat()

    async def stop(self):
        self.running = False
        logger.info("CoBWeaverClaw stopped")
