"""
SimCore — محرك التشغيل
يربط كل الوكلاء معاً ويُشغّل دورة كاملة.
"""
import logging
from typing import Dict, Any, List, Optional
from .config import SimCoreConfig, AgentConfig, SourceConfig
from .source_manager import SourceManager
from .agents.monitor_agent  import MonitorAgent
from .agents.tracker_agent  import TrackerAgent
from .agents.oracle_agent   import OracleAgent
from .agents.memory_agent   import MemoryAgent
from .agents.research_agent import ResearchAgent
from .agents.alert_agent    import AlertAgent, AlertRule
from .agents.executor_agent import ExecutorAgent

logger = logging.getLogger("simcore.engine")

_DEFAULT_MM = None   # مفرد مُخزَّن لمدير الذاكرة الافتراضي (يُبنى مرة واحدة)


class _SyncTelegramNotifier:
    """مُبلِّغ متزامن يوجّه إلى نفس بوت Telegram (tools.agent_tools.send_telegram)."""
    def send(self, message: str) -> bool:
        try:
            from tools.agent_tools import send_telegram
            res = send_telegram(message)
            return isinstance(res, str) and "✅" in res
        except Exception as e:
            logger.debug("notifier send failed: %s", e)
            return False


class SimCoreEngine:
    """
    المحرك الرئيسي.
    يُشغّل: monitor → tracker → oracle
    يُعيد: قرار نهائي موجّه للمستخدم
    """

    def __init__(self, config: SimCoreConfig, memory_manager=None, notifier=None):
        self.config = config

        # مُبلِّغ افتراضي متزامن (Telegram) إن لم يُمرَّر
        notifier = notifier or _SyncTelegramNotifier()
        self.notifier = notifier

        # مدير ذاكرة افتراضي (نفس قاعدة النظام) إن لم يُمرَّر
        if memory_manager is None:
            memory_manager = self._default_memory_manager()
        self.memory_manager = memory_manager

        # إنشاء الوكلاء
        self.monitor = MonitorAgent(
            config        = AgentConfig(agent_id="monitor", role="monitor",
                                        domain=config.domain,
                                        activity="background"),
            system_config = config,
        )
        self.tracker = TrackerAgent(
            config        = AgentConfig(agent_id="tracker", role="tracker",
                                        domain=config.domain,
                                        activity="background"),
            system_config = config,
        )
        self.oracle = OracleAgent(
            config        = AgentConfig(agent_id="oracle", role="oracle",
                                        domain=config.domain,
                                        activity="deep"),
            system_config = config,
        )

        # الوكلاء الجدد
        self.memory_agent   = MemoryAgent(config, memory_manager)
        self.research_agent = ResearchAgent(
            config        = AgentConfig(agent_id="research", role="research",
                                        domain=config.domain),
            system_config = config,
        )
        self.alert_agent    = AlertAgent(config, notifier=notifier)
        self.executor_agent = ExecutorAgent(
            config, notifier=notifier,
            enabled=getattr(config, "executor_enabled", False))

    @staticmethod
    def _default_memory_manager():
        """يبني MemoryManager بنفس مزوّد النظام المدمج (مفرد مُخزَّن، فشل آمن → None)."""
        global _DEFAULT_MM
        if _DEFAULT_MM is not None:
            return _DEFAULT_MM
        try:
            from memory.core.memory_manager import MemoryManager
            from memory.core.builtin_provider import BuiltinMemoryProvider
            mm = MemoryManager()
            mm.add_provider(BuiltinMemoryProvider())
            mm.initialize_all(session_id="simcore")
            _DEFAULT_MM = mm
            return mm
        except Exception as e:
            logger.debug("default memory manager unavailable: %s", e)
            return None

    def run_cycle(self) -> Dict[str, Any]:
        """دورة تحليل كاملة"""
        monitor_results = []
        tracker_results = []

        # المراقبة — المنصات (exchange/api/social) من platforms + ما كان في sources
        platforms = getattr(self.config, "platforms", None) or []
        api_sources = list(platforms) + [
            s for s in self.config.sources
            if isinstance(s, dict) and s.get("source_type") in ("api", "social", "exchange")]
        for src in api_sources:
            result = self.monitor.monitor_once(
                source_url  = src["url"],
                source_name = src.get("name", src.get("url", "")),
                api_key     = src.get("api_key"),
                account_id  = src.get("account_id"),
                secret      = src.get("secret") or src.get("secret_key"),
            )
            if result.get("has_signal"):
                monitor_results.append(result)

        # التتبع — مواقع ويب (نُبقي حقول SourceConfig المعروفة فقط)
        _sc_fields = {"url", "name", "api_key", "account_id", "connected", "source_type"}
        web_sources = [
            SourceConfig(**{k: v for k, v in s.items() if k in _sc_fields})
            for s in self.config.sources
            if isinstance(s, dict) and s.get("source_type", "web") == "web" and s.get("url")
        ]
        if web_sources:
            tracker_results = self.tracker.track(web_sources)

        # بحث معمّق اختياري عبر ResearchAgent
        if getattr(self.config, "deep_research", False):
            research = self.research_agent.research(
                query   = getattr(self.config, "research_query", "") or self.config.domain,
                sources = web_sources,
                domain  = self.config.domain,
            )
            tracker_results.append({"source": "ResearchAgent", **research})

        # القرار النهائي
        decision = self.oracle.decide(monitor_results, tracker_results)

        # تنفيذ اختياري على أول منصة (ExecutorAgent مُعطَّل افتراضياً)
        executor_result = (
            self.executor_agent.execute(decision, platforms[0])
            if platforms and decision.get("decision") in ("buy", "sell")
            else None
        )

        return {
            "monitor_results": monitor_results,
            "tracker_results": tracker_results,
            "decision":        decision,
            "executor_result": executor_result,
            "domain":          self.config.domain,
        }

    def probe_source(self, url: str) -> Dict[str, Any]:
        """اختبار مصدر جديد قبل إضافته"""
        return SourceManager.probe(url)
