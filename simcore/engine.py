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

logger = logging.getLogger("simcore.engine")


class SimCoreEngine:
    """
    المحرك الرئيسي.
    يُشغّل: monitor → tracker → oracle
    يُعيد: قرار نهائي موجّه للمستخدم
    """

    def __init__(self, config: SimCoreConfig):
        self.config = config

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

        # القرار النهائي
        decision = self.oracle.decide(monitor_results, tracker_results)

        return {
            "monitor_results": monitor_results,
            "tracker_results": tracker_results,
            "decision":        decision,
            "domain":          self.config.domain,
        }

    def probe_source(self, url: str) -> Dict[str, Any]:
        """اختبار مصدر جديد قبل إضافته"""
        return SourceManager.probe(url)
