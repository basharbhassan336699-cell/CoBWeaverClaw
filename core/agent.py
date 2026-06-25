"""
CoBWeaverClaw — Main Agent Loop
The heart of the agent.
"""
import asyncio
import logging
from core.router import Router
from core.platform import PlatformAdapter
from memory.sqlite_store import SQLiteStore
from brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


class CoBWeaverClaw:
    """
    Main agent class. Receives input, routes to appropriate
    module, returns response. Runs continuously via heartbeat.
    """

    def __init__(self, config: dict):
        self.config    = config
        self.platform  = PlatformAdapter()
        self.memory    = SQLiteStore(config.get("memory", {}))
        self.brain     = ModelRouter(config.get("brain", {}))
        self.router    = Router(self)
        self.running   = False
        logger.info(f"CoBWeaverClaw initialized on {self.platform.platform}")

    async def process(self, message: str, user_id: str, lang: str = "auto") -> str:
        """
        Main entry point for all user messages.
        1. Detect language
        2. Load relevant memory context
        3. Route to skill or brain
        4. Save to memory
        5. Return response
        """
        if lang == "auto":
            lang = self._detect_language(message)

        context = await self.memory.get_context(user_id, message)
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
        # Override in specialization modules

    def _detect_language(self, text: str) -> str:
        """Auto-detect language from user message."""
        arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
        if any(c in arabic_chars for c in text):
            return "ar"
        return "en"

    async def start(self):
        self.running = True
        logger.info("CoBWeaverClaw started")
        await self.heartbeat()

    async def stop(self):
        self.running = False
        logger.info("CoBWeaverClaw stopped")
