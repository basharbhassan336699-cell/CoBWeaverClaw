"""
SimCore — API endpoints للوكلاء والمصادر المفتوحة
"""
import json
import time
from pathlib import Path
from flask import Blueprint, request, jsonify
from ..services.source_manager import SourceManager
from ..services.monitor_agent  import MonitorAgent
from ..services.tracker_agent  import TrackerAgent
from ..services.oracle_agent   import OracleAgent
from ..config import Config

simcore_bp = Blueprint("simcore", __name__, url_prefix="/api/simcore")


@simcore_bp.route("/domains", methods=["GET"])
def get_domains():
    return jsonify({"success": True, "domains": Config.SIMCORE_DOMAINS})


@simcore_bp.route("/probe", methods=["POST"])
def probe():
    data    = request.json or {}
    url     = data.get("url","").strip()
    api_key = data.get("api_key")
    secret  = data.get("secret")
    if not url:
        return jsonify({"success":False,"error":"url مطلوب"}),400
    return jsonify({"success":True,"result": SourceManager.probe(url, api_key, secret)})


@simcore_bp.route("/run", methods=["POST"])
def run_cycle():
    """تشغيل دورة تحليل كاملة: monitor → tracker → oracle"""
    d         = request.json or {}
    domain    = d.get("domain", "general")
    sources   = d.get("sources", [])
    platforms = d.get("platforms", [])

    # مفاتيح مشتركة — fallback لـ Config
    mk = d.get("global_model_key")  or None
    mu = d.get("global_model_url")  or None
    mn = d.get("global_model_name") or None

    errors = []

    # وكيل المراقبة — المنصات (exchange/api/social) من platforms + ما كان في sources
    monitor_results = []
    api_sources = platforms + [
        s for s in sources if s.get("source_type") in ("api", "social", "exchange")]
    if api_sources:
        try:
            mon = MonitorAgent(domain,
                               d.get("monitor_key") or mk,
                               d.get("monitor_url") or mu,
                               d.get("monitor_name") or mn)
            for src in api_sources:
                r = mon.monitor_once(src["url"], src.get("name", src["url"]),
                                     src.get("api_key"), src.get("account_id"),
                                     secret=src.get("secret"))
                if r.get("has_signal"):
                    monitor_results.append(r)
        except ValueError as e:
            errors.append(str(e))

    # وكيل التتبع — مواقع ويب
    tracker_results = []
    web_sources = [s for s in sources if s.get("source_type", "web") == "web"]
    if web_sources:
        try:
            trk = TrackerAgent(domain,
                               d.get("tracker_key") or mk,
                               d.get("tracker_url") or mu,
                               d.get("tracker_name") or mn)
            tracker_results = trk.track(web_sources)
        except ValueError as e:
            errors.append(str(e))

    # OracleAgent — القرار النهائي
    try:
        orc      = OracleAgent(domain,
                               d.get("oracle_key") or mk,
                               d.get("oracle_url") or mu,
                               d.get("oracle_name") or mn)
        decision = orc.decide(monitor_results, tracker_results)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({
        "success":         True,
        "domain":          domain,
        "monitor_results": monitor_results,
        "tracker_results": tracker_results,
        "decision":        decision,
        "warnings":        errors if errors else None,
    })


@simcore_bp.route("/platform/connect", methods=["POST"])
def platform_connect():
    from ..services.platforms import connect_platform
    return jsonify(connect_platform(**(request.json or {})))


@simcore_bp.route("/platform/list", methods=["GET"])
def platform_list():
    from ..services.platforms import list_platforms
    return jsonify(list_platforms())


@simcore_bp.route("/platform/delete/<name>", methods=["DELETE"])
def platform_delete(name):
    from ..services.platforms import delete_platform
    return jsonify(delete_platform(name))


@simcore_bp.route("/website/connect", methods=["POST"])
def website_connect():
    from ..services.platforms import connect_website
    return jsonify(connect_website(**(request.json or {})))


@simcore_bp.route("/website/list", methods=["GET"])
def website_list():
    from ..services.platforms import list_websites
    return jsonify(list_websites())


@simcore_bp.route("/feedback", methods=["POST"])
def feedback():
    """تسجيل نتيجة فعلية لقرار سابق لتحسين الدقة"""
    d       = request.json or {}
    ts      = d.get("ts")
    outcome = d.get("outcome")
    if not ts or not outcome:
        return jsonify({"success": False, "error": "ts و outcome مطلوبان"}), 400
    try:
        orc = OracleAgent(d.get("domain", "general"))
        orc.feedback(int(ts), outcome)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── قواعد التنبيه (AlertAgent) + سجل التنفيذ (ExecutorAgent) ──────────
def _alert_rules_path() -> Path:
    return Path.home() / ".cobweaverclaw" / "simcore" / "alert_rules.json"


@simcore_bp.route("/alerts/add", methods=["POST"])
def alert_add():
    d = request.json or {}
    # يُحفظ في ~/.cobweaverclaw/simcore/alert_rules.json
    path = _alert_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    rules = json.loads(path.read_text()) if path.exists() else []
    rules.append({
        "rule_id":     d.get("rule_id", str(int(time.time()))),
        "description": d.get("description", ""),
        "source_url":  d.get("source_url", ""),
        "condition":   d.get("condition", "anomaly"),
        "threshold":   float(d.get("threshold", 0)),
        "api_key":     d.get("api_key", ""),
        "created_at":  int(time.time()),
    })
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2))
    return jsonify({"success": True})


@simcore_bp.route("/alerts/list", methods=["GET"])
def alert_list():
    path  = _alert_rules_path()
    rules = json.loads(path.read_text()) if path.exists() else []
    return jsonify({"success": True, "rules": rules})


@simcore_bp.route("/alerts/delete/<rule_id>", methods=["DELETE"])
def alert_delete(rule_id):
    path  = _alert_rules_path()
    if path.exists():
        rules = json.loads(path.read_text())
        rules = [r for r in rules if r["rule_id"] != rule_id]
        path.write_text(json.dumps(rules, ensure_ascii=False, indent=2))
    return jsonify({"success": True})


@simcore_bp.route("/executions", methods=["GET"])
def executions_list():
    path = Path.home() / ".cobweaverclaw" / "simcore" / "executions.jsonl"
    if not path.exists():
        return jsonify({"success": True, "executions": []})
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return jsonify({"success": True, "executions": list(reversed(entries[-50:]))})


@simcore_bp.route("/executor/toggle", methods=["POST"])
def executor_toggle():
    # يحفظ حالة ExecutorAgent في config
    enabled = (request.json or {}).get("enabled", False)
    path    = Path.home() / ".cobweaverclaw" / "simcore" / "executor_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"enabled": enabled}, ensure_ascii=False))
    return jsonify({"success": True, "enabled": enabled})
