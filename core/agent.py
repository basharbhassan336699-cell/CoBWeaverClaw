"""
CoBWeaverClaw — Main Agent Loop
The heart of the agent.
"""
import asyncio
import logging
import time
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
        mem_cfg = dict(config.get("memory", {}))
        mem_cfg.setdefault("memory_size", config.get("agent", {}).get("memory_size", 20))
        self.memory   = SQLiteStore(mem_cfg)
        self.brain    = ModelRouter(config)   # config الكامل: agent + keys + brain
        self.router   = Router(self)
        self.devices  = DeviceRegistry(
            config.get("devices", {}).get("db_path")
        )
        self.running  = False

        # Notifier (Telegram or CLI)
        self.notifier = self._init_notifier()
        self.updater  = Updater(config.get("updates", {}), self.notifier)

        # ── نظام الذاكرة المُدمج (memory-merge) — إضافي ودفاعي ──
        # يُهيَّأ بشكل كسول ولا يكسر الوكيل إن فشل استيراده أو تهيئته.
        self.session_id      = f"session-{int(time.time())}"
        self._memory_manager = None
        self._memory_messages = []
        self._init_memory_manager()

        logger.info(f"CoBWeaverClaw initialized on {self.platform.platform}")

    def _init_memory_manager(self):
        """يهيّئ MemoryManager مع BuiltinMemoryProvider (اختياري وآمن)."""
        mem_cfg = self.config.get("memory", {}) or {}
        if not mem_cfg.get("manager_enabled", True):
            logger.info("Memory manager disabled via config")
            return
        try:
            from memory.core.memory_manager import MemoryManager
            from memory.core.builtin_provider import BuiltinMemoryProvider
            mm = MemoryManager()
            mm.add_provider(BuiltinMemoryProvider())
            # مزود ذاكرة خارجي اختياري (memory.provider في الإعدادات)
            provider_name = mem_cfg.get("provider")
            if provider_name:
                self._register_external_provider(mm, provider_name)
            mm.initialize_all(session_id=self.session_id)
            self._memory_manager = mm
            logger.info("Memory manager initialized (builtin provider)")
        except Exception as e:
            self._memory_manager = None
            logger.warning(f"Memory manager unavailable: {e}")

    def _register_external_provider(self, mm, provider_name: str):
        """يحمّل ويُسجّل مزوّد ذاكرة خارجي إن كان متاحاً (آمن)."""
        try:
            from memory.plugins._discovery import load_memory_provider
            provider = load_memory_provider(provider_name)
            if provider is None:
                logger.warning(f"Memory provider '{provider_name}' not found")
                return
            if not provider.is_available():
                logger.warning(
                    f"Memory provider '{provider_name}' unavailable "
                    "(missing package or API key) — skipped"
                )
                return
            mm.add_provider(provider)
            logger.info(f"External memory provider registered: {provider_name}")
        except Exception as e:
            logger.warning(
                f"External memory provider '{provider_name}' failed to load: {e}"
            )

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

        # قبل الدورة (pre-turn): حقن كتلة الذاكرة + الاسترجاع المُسبَق
        context = self._memory_pre_turn(message, context)

        response = await self.router.handle(message, context, lang)
        await self.memory.save(user_id, message, response, lang)
        # تلخيص تلقائي في الخلفية (Layer 2) دون مقاطعة المستخدم
        try:
            await self.memory.maybe_summarize(user_id)
        except Exception:
            pass

        # بعد الدورة (post-turn): مزامنة + جدولة استرجاع + مراجعة خلفية
        self._memory_post_turn(message, response)
        return response

    def _memory_pre_turn(self, message: str, context: dict) -> dict:
        """يضيف كتلة نظام الذاكرة والاسترجاع المُسبَق إلى السياق (آمن)."""
        if self._memory_manager is None:
            return context
        context = dict(context or {})
        try:
            block = self._memory_manager.build_system_prompt()
            if block:
                context["memory_block"] = block
        except Exception as e:
            logger.debug(f"memory build_system_prompt failed: {e}")
        try:
            recalled = self._memory_manager.prefetch_all(
                message, session_id=self.session_id
            )
            if recalled:
                context["memory_recall"] = recalled
        except Exception as e:
            logger.debug(f"memory prefetch failed: {e}")
        return context

    def _memory_post_turn(self, message: str, response: str):
        """يزامن الدورة المكتملة ويجدول الاسترجاع والمراجعة الخلفية (آمن)."""
        if self._memory_manager is None:
            return
        self._memory_messages.append({"role": "user", "content": message})
        self._memory_messages.append({"role": "assistant", "content": response})
        try:
            self._memory_manager.sync_all(
                message, response, session_id=self.session_id,
                messages=list(self._memory_messages),
            )
            self._memory_manager.queue_prefetch_all(
                message, session_id=self.session_id
            )
        except Exception as e:
            logger.debug(f"memory sync failed: {e}")
        self._spawn_background_review()

    def _spawn_background_review(self):
        """
        مراجعة خلفية للتعلّم الذاتي — خيط منفصل (اختياري ومعطّل افتراضياً).

        وحدة background_review المنقولة مبنية على واجهة الوكيل الأصلية
        (curator / model client / session_db ...) وهي غير متوفّرة في
        CoBWeaverClaw بعد، لذا تبقى معطّلة افتراضياً وتُفعَّل فقط عبر
        config: memory.background_review = true بعد اكتمال المتطلّبات.
        """
        mem_cfg = self.config.get("memory", {}) or {}
        if not mem_cfg.get("background_review", False):
            return
        try:
            import threading
            from memory.learning.background_review import (
                spawn_background_review_thread,
            )
            target, _prompt = spawn_background_review_thread(
                self, list(self._memory_messages), review_memory=True,
            )
            threading.Thread(target=target, daemon=True).start()
        except Exception as e:
            logger.debug(f"background review skipped: {e}")

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
        self._memory_session_end()
        logger.info("CoBWeaverClaw stopped")

    def _memory_session_end(self):
        """يُنهي جلسة الذاكرة ويُغلق المزوّدين (آمن)."""
        if self._memory_manager is None:
            return
        try:
            self._memory_manager.on_session_end(list(self._memory_messages))
        except Exception as e:
            logger.debug(f"memory on_session_end failed: {e}")
        try:
            self._memory_manager.shutdown_all()
        except Exception as e:
            logger.debug(f"memory shutdown failed: {e}")
        self._memory_manager = None
