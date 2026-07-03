"""
SimCore — API endpoints
مُكيّفة لبوابة CoBWeaverClaw (http.server) — لا Flask في المشروع.
نفس المسارات والعقود المطلوبة تحت /api/simcore/*:
  POST /api/simcore/probe     ← probe_source(data)
  POST /api/simcore/run       ← run_cycle(data)
  GET  /api/simcore/domains   ← get_domains()
  POST /api/simcore/feedback  ← record_feedback(data)
كل دالة تعيد (json_dict, status_code).
"""
from typing import Any, Dict, Tuple

from .config import SimCoreConfig, SourceConfig
from .engine import SimCoreEngine
from .source_manager import SourceManager


def probe_source(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """اختبار اتصال مصدر"""
    data = data or {}
    url = data.get("url", "")
    if not url:
        return {"success": False, "error": "url مطلوب"}, 400
    result = SourceManager.probe(url)
    return {"success": True, "result": result}, 200


def run_cycle(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """تشغيل دورة تحليل كاملة"""
    data = data or {}

    config = SimCoreConfig(
        domain            = data.get("domain", "general"),
        domain_custom     = data.get("domain_custom", ""),
        mode              = data.get("mode", "general"),
        global_model_key  = data.get("global_model_key"),
        global_model_url  = data.get("global_model_url"),
        global_model_name = data.get("global_model_name"),
        sources           = data.get("sources", []),
    )

    try:
        engine = SimCoreEngine(config)
        # مفاتيح الوكلاء الفردية (اختيارية) — القاعدة: مفتاح خاص أو وراثة من global
        if data.get("monitor_model_key"):
            engine.monitor.config.model_key = data["monitor_model_key"]
        if data.get("tracker_model_key"):
            engine.tracker.config.model_key = data["tracker_model_key"]
        if data.get("oracle_model_key"):
            engine.oracle.config.model_key = data["oracle_model_key"]
        result = engine.run_cycle()
        return {"success": True, "result": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def get_domains() -> Tuple[Dict[str, Any], int]:
    """قائمة التخصصات المتاحة"""
    from .config import DOMAINS
    return {"success": True, "domains": DOMAINS}, 200


def record_feedback(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """تسجيل نتيجة فعلية لقرار سابق"""
    data = data or {}
    ts      = data.get("decision_ts")
    outcome = data.get("outcome")
    if not ts or not outcome:
        return {"success": False, "error": "decision_ts و outcome مطلوبان"}, 400

    config = SimCoreConfig(
        global_model_key  = data.get("global_model_key"),
        global_model_url  = data.get("global_model_url"),
        global_model_name = data.get("global_model_name"),
    )
    from .config import AgentConfig
    from .agents.oracle_agent import OracleAgent
    oracle = OracleAgent(
        config        = AgentConfig(agent_id="oracle", role="oracle"),
        system_config = config,
    )
    oracle.feedback(int(ts), outcome)
    return {"success": True}, 200
