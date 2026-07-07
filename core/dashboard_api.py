"""
Dashboard API v2 — البيانات الخلفية لتبويبات اللوحة الجديدة:
الذاكرة الموزونة، Dreaming، التداول، Workboard، الإقران، الاستخدام، السجلات.
كل الدوال دفاعية: أي فشل يعيد بنية فارغة ولا يكسر اللوحة.
"""
from __future__ import annotations

import collections
import datetime
import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_HOME = Path.home() / ".cobweaverclaw"


# ══════════════════════════════════════════════════════════════
# السجلات (Logs) — حلقة تخزين في الذاكرة تتغذّى من logging
# ══════════════════════════════════════════════════════════════
LOG_BUFFER: collections.deque = collections.deque(maxlen=500)
_LOG_LOCK = threading.Lock()
_LOG_SEQ = [0]
_LOG_INSTALLED = [False]


class _DashLogHandler(logging.Handler):
    """يلتقط سجلات المشروع في حلقة تخزين للوحة."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            name = (record.name or "").lower()
            if name.startswith(("urllib3", "asyncio")):
                return
            level = record.levelname
            if "memory" in name or "dreaming" in name:
                cat = "MEM"
            elif "skill" in name:
                cat = "SKILL"
            elif level in ("WARNING", "WARN"):
                cat = "WARN"
            elif level in ("ERROR", "CRITICAL"):
                cat = "ERROR"
            else:
                cat = "INFO"
            with _LOG_LOCK:
                _LOG_SEQ[0] += 1
                LOG_BUFFER.append({
                    "id": _LOG_SEQ[0],
                    "ts": int(record.created),
                    "time": datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                    "level": "WARN" if level == "WARNING" else level,
                    "cat": cat,
                    "src": record.name,
                    "msg": record.getMessage()[:400],
                })
        except Exception:
            pass


def install_log_handler() -> None:
    """يركّب مُلتقط السجلات على الجذر مرة واحدة."""
    if _LOG_INSTALLED[0]:
        return
    _LOG_INSTALLED[0] = True
    h = _DashLogHandler()
    h.setLevel(logging.INFO)
    root = logging.getLogger()
    root.addHandler(h)
    # الجذر افتراضياً WARNING فيُسقط INFO قبل وصولها للمُلتقط —
    # المشروع بلا معالجات أخرى، فرفعه لا يغيّر مخرجات الطرفية.
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    logger.info("Dashboard log capture installed")


def logs_list(limit: int = 20, since: int = 0, level: str = "") -> dict:
    """آخر السجلات؛ since=آخر id شوهد (للتدفق بالـ polling)."""
    with _LOG_LOCK:
        items = list(LOG_BUFFER)
    if since:
        items = [x for x in items if x["id"] > since]
    if level and level != "ALL":
        items = [x for x in items if x["cat"] == level or x["level"] == level]
    return {"logs": items[-max(1, min(int(limit or 20), 200)):],
            "last_id": _LOG_SEQ[0]}


# ══════════════════════════════════════════════════════════════
# الاستخدام (Usage) — تسجيل tokens/تكلفة لكل نداء نموذج
# ══════════════════════════════════════════════════════════════
_USAGE_DB = _HOME / "usage.db"

# أسعار تقريبية $/مليون توكن (دخل، خرج) — للتقدير فقط؛ 0 للمجاني/غير المعروف
_PRICES = {
    "claude": (3.0, 15.0), "gpt-4o": (2.5, 10.0), "gpt-4": (10.0, 30.0),
    "deepseek": (0.27, 1.1), "mistral": (0.4, 2.0), "grok": (2.0, 10.0),
    "gemini": (0.15, 0.6), "kimi": (0.6, 2.5), "glm": (0.6, 2.2),
}


def _usage_con() -> sqlite3.Connection:
    _USAGE_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_USAGE_DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL, day TEXT NOT NULL,
        model TEXT NOT NULL, tokens_in INTEGER, tokens_out INTEGER, cost REAL)""")
    return con


def _price_for(model: str) -> tuple:
    m = (model or "").lower()
    for key, p in _PRICES.items():
        if key in m:
            return p
    return (0.0, 0.0)


def record_usage(model: str, tokens_in: int, tokens_out: int) -> None:
    """يسجّل نداءً واحداً (يُستدعى من ModelRouter — آمن تماماً)."""
    try:
        pin, pout = _price_for(model)
        cost = (tokens_in * pin + tokens_out * pout) / 1_000_000
        now = int(time.time())
        con = _usage_con()
        con.execute("INSERT INTO usage(ts,day,model,tokens_in,tokens_out,cost) VALUES(?,?,?,?,?,?)",
                    (now, datetime.date.today().isoformat(), model, tokens_in, tokens_out, cost))
        con.commit(); con.close()
    except Exception:
        pass


def usage_report(days: int = 7) -> dict:
    """تجميع يومي + حسب النموذج لآخر N يوماً."""
    try:
        days = max(1, min(int(days or 7), 365))
        since = (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()
        con = _usage_con()
        daily = [dict(r) for r in con.execute(
            "SELECT day, SUM(tokens_in+tokens_out) tokens, SUM(cost) cost, COUNT(*) calls"
            " FROM usage WHERE day>=? GROUP BY day ORDER BY day", (since,))]
        models = [dict(r) for r in con.execute(
            "SELECT model, COUNT(*) calls, SUM(tokens_in+tokens_out) tokens, SUM(cost) cost"
            " FROM usage WHERE day>=? GROUP BY model ORDER BY tokens DESC", (since,))]
        con.close()
        # سلسلة أيام كاملة (حتى الفارغة) للمخطط
        by_day = {d["day"]: d for d in daily}
        series = []
        for i in range(days):
            day = (datetime.date.today() - datetime.timedelta(days=days - 1 - i)).isoformat()
            e = by_day.get(day, {})
            series.append({"day": day, "tokens": int(e.get("tokens") or 0),
                           "cost": round(float(e.get("cost") or 0), 4),
                           "calls": int(e.get("calls") or 0)})
        total_today = next((d for d in series if d["day"] == datetime.date.today().isoformat()),
                           {"tokens": 0, "cost": 0})
        return {"days": days, "series": series, "models": models,
                "today_tokens": total_today["tokens"], "today_cost": total_today["cost"]}
    except Exception as e:
        logger.debug("usage_report failed: %s", e)
        return {"days": days, "series": [], "models": [], "today_tokens": 0, "today_cost": 0}


# ══════════════════════════════════════════════════════════════
# الذاكرة الموزونة (memory.db)
# ══════════════════════════════════════════════════════════════
def memory_list(context: str = "general") -> dict:
    try:
        from memory.core.builtin_provider import BuiltinMemoryProvider, CONTEXTS, CHAR_LIMIT
        if context not in CONTEXTS:
            return {"error": "context غير صالح", "entries": []}
        p = BuiltinMemoryProvider()
        p._init_db()
        con = p._con()
        rows = con.execute(
            "SELECT id,content,weight,write_level,created_at,updated_at,recall_count"
            " FROM memories WHERE context=? ORDER BY weight DESC", (context,)).fetchall()
        con.close()
        entries = [dict(r) for r in rows]
        used = sum(len(e["content"]) + 3 for e in entries)
        return {"context": context, "entries": entries,
                "used_chars": used, "char_limit": CHAR_LIMIT}
    except Exception as e:
        logger.debug("memory_list failed: %s", e)
        return {"context": context, "entries": [], "used_chars": 0, "char_limit": 2200}


def memory_delete(memory_id: int) -> dict:
    try:
        from memory.core.builtin_provider import BuiltinMemoryProvider
        p = BuiltinMemoryProvider()
        p._init_db()
        return p.delete_entry(int(memory_id))
    except Exception as e:
        return {"error": str(e)[:100]}


# ══════════════════════════════════════════════════════════════
# Dreaming — الحالة واليوميات والتشغيل اليدوي
# ══════════════════════════════════════════════════════════════
def dreaming_status() -> dict:
    try:
        from memory.learning.dreaming import _seconds_until_sunday_2am, _SCHEDULED, read_diary
        secs = _seconds_until_sunday_2am()
        nxt = datetime.datetime.now() + datetime.timedelta(seconds=secs)
        diary = read_diary(1)
        last = diary[0] if diary else None
        return {"scheduled": bool(_SCHEDULED),
                "next_run": nxt.strftime("%Y-%m-%d %H:%M"),
                "next_secs": int(secs),
                "last_run": (last or {}).get("time", "—"),
                "last_type": (last or {}).get("type", "")}
    except Exception as e:
        return {"scheduled": False, "next_run": "—", "next_secs": 0,
                "last_run": "—", "error": str(e)[:80]}


def dreaming_diary(limit: int = 50) -> dict:
    try:
        from memory.learning.dreaming import read_diary
        return {"entries": read_diary(limit)}
    except Exception:
        return {"entries": []}


def dreaming_run() -> dict:
    try:
        from memory.learning.dreaming import deep_dreaming
        return deep_dreaming()
    except Exception as e:
        return {"error": str(e)[:120]}


def dreaming_weekly_summary() -> dict:
    try:
        from memory.trading.trade_memory import init_trade_db, get_pattern_stats, weekly_summary
        init_trade_db()
        return {"summary": weekly_summary(), "patterns": get_pattern_stats()}
    except Exception as e:
        return {"summary": "", "patterns": [], "error": str(e)[:80]}


# ══════════════════════════════════════════════════════════════
# التداول (trades.db)
# ══════════════════════════════════════════════════════════════
def trades_list(outcome: str = "") -> dict:
    try:
        from memory.trading.trade_memory import init_trade_db, _con
        init_trade_db()
        con = _con()
        q = ("SELECT id,asset,entry,tp,sl,outcome,pattern,session,pnl_pct,notes,opened_at,closed_at"
             " FROM trades")
        args = ()
        if outcome and outcome != "all":
            q += " WHERE outcome=?"
            args = (outcome,)
        q += " ORDER BY opened_at DESC LIMIT 200"
        rows = [dict(r) for r in con.execute(q, args)]
        con.close()
        return {"trades": rows}
    except Exception as e:
        logger.debug("trades_list failed: %s", e)
        return {"trades": []}


def trades_patterns() -> dict:
    try:
        from memory.trading.trade_memory import init_trade_db, get_pattern_stats
        init_trade_db()
        return {"patterns": get_pattern_stats()}
    except Exception:
        return {"patterns": []}


def trades_log(body: dict) -> dict:
    """يسجّل صفقة جديدة (asset + entry إلزاميّان)."""
    try:
        from memory.trading.trade_memory import init_trade_db, log_trade
        init_trade_db()
        asset = str((body or {}).get("asset", "")).strip()
        if not asset:
            return {"ok": False, "error": "asset مطلوب"}
        try:
            entry = float((body or {}).get("entry"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "entry رقم مطلوب"}

        def _num(k):
            v = (body or {}).get(k)
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def _txt(k):
            v = (body or {}).get(k)
            v = str(v).strip() if v not in (None, "") else ""
            return v or None

        return log_trade(asset, entry, tp=_num("tp"), sl=_num("sl"),
                         pattern=_txt("pattern"), session=_txt("session"),
                         notes=_txt("notes"))
    except Exception as e:
        logger.debug("trades_log failed: %s", e)
        return {"ok": False, "error": str(e)[:120]}


def trades_close(body: dict) -> dict:
    """يُغلق صفقة: trade_id + outcome (hit_tp/hit_sl/manual) + pnl_pct."""
    try:
        from memory.trading.trade_memory import init_trade_db, close_trade
        init_trade_db()
        try:
            trade_id = int((body or {}).get("trade_id"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "trade_id مطلوب"}
        outcome = str((body or {}).get("outcome", "")).strip()
        if not outcome:
            return {"ok": False, "error": "outcome مطلوب"}
        try:
            pnl_pct = float((body or {}).get("pnl_pct", 0) or 0)
        except (TypeError, ValueError):
            pnl_pct = 0.0
        return close_trade(trade_id, outcome, pnl_pct)
    except Exception as e:
        logger.debug("trades_close failed: %s", e)
        return {"ok": False, "error": str(e)[:120]}


def _num_list(body: dict, key: str) -> list:
    """يحوّل قيمة body[key] (قائمة أو نص مفصول بفواصل) إلى قائمة أرقام."""
    v = (body or {}).get(key)
    if isinstance(v, str):
        v = [x for x in v.replace("\n", ",").split(",") if x.strip()]
    out = []
    for x in (v or []):
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            pass
    return out


def regime_status(body: dict = None) -> dict:
    """حالة السوق: يكتشف من أسعار مُرسَلة أو يعيد آخر سجل."""
    try:
        from memory.trading.regime_detector import detect_regime, save_regime_log, latest_regime
        prices = _num_list(body or {}, "prices")
        volumes = _num_list(body or {}, "volumes")
        if prices:
            r = detect_regime(prices, volumes)
            asset = str((body or {}).get("asset", "")).strip() or "—"
            try:
                save_regime_log(asset, r["regime"], r["strength"], r["recommended_strategy"])
            except Exception:
                pass
            r["asset"] = asset
            return r
        last = latest_regime((body or {}).get("asset"))
        return {"latest": last} if last else {"regime": None, "reasoning": "لا سجلّ حالة بعد."}
    except Exception as e:
        logger.debug("regime_status failed: %s", e)
        return {"regime": None, "error": str(e)[:120]}


def manipulation_alerts(body: dict = None) -> dict:
    """تنبيهات التلاعب: يفحص أسعاراً مُرسَلة + آخر الأحداث المسجّلة."""
    try:
        from memory.trading.manipulation_detector import (
            detect_manipulation, log_manipulation_event, recent_manipulations)
        result = {}
        prices = _num_list(body or {}, "prices")
        volumes = _num_list(body or {}, "volumes")
        if prices:
            d = detect_manipulation(prices, volumes)
            if d.get("manipulation_detected"):
                asset = str((body or {}).get("asset", "")).strip() or "—"
                try:
                    log_manipulation_event(asset, d["type"], d["confidence"], d["action"])
                except Exception:
                    pass
            result["current"] = d
        result["recent"] = recent_manipulations(10)
        return result
    except Exception as e:
        logger.debug("manipulation_alerts failed: %s", e)
        return {"recent": [], "error": str(e)[:120]}


def emergency_status(_: dict = None) -> dict:
    """حالة مكابح الطوارئ الحالية + الإحصاءات."""
    try:
        from memory.trading.emergency_stop import emergency_state
        return emergency_state()
    except Exception as e:
        logger.debug("emergency_status failed: %s", e)
        return {"active": False, "error": str(e)[:120]}


def emergency_report(_: dict = None) -> dict:
    """يولّد تقرير الطوارئ الحالي (Markdown عربي)."""
    try:
        from memory.trading.emergency_stop import generate_emergency_report
        return {"report": generate_emergency_report()}
    except Exception as e:
        logger.debug("emergency_report failed: %s", e)
        return {"report": "", "error": str(e)[:120]}


def simulate_entry(body: dict) -> dict:
    """محاكاة صفقة قبل التنفيذ (asset + entry إلزاميّان)."""
    try:
        from memory.trading.scenario_simulator import simulate_trade
        b = body or {}
        asset = str(b.get("asset", "")).strip()
        if not asset:
            return {"error": "asset مطلوب"}
        try:
            entry = float(b.get("entry"))
        except (TypeError, ValueError):
            return {"error": "entry رقم مطلوب"}

        def _n(k):
            v = b.get(k)
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        return simulate_trade(asset, entry, tp=_n("tp"), sl=_n("sl"),
                              pattern=(str(b.get("pattern", "")).strip() or None),
                              regime="auto",
                              prices=_num_list(b, "prices"),
                              volumes=_num_list(b, "volumes"))
    except Exception as e:
        logger.debug("simulate_entry failed: %s", e)
        return {"error": str(e)[:120]}


# ══════════════════════════════════════════════════════════════
# Workboard — لوحة مهام Kanban (ملف JSON)
# ══════════════════════════════════════════════════════════════
_WB_FILE = _HOME / "workboard.json"
_WB_LOCK = threading.Lock()
_WB_STATUSES = ("pending", "doing", "done")


def _wb_load() -> list:
    try:
        if _WB_FILE.exists():
            return json.loads(_WB_FILE.read_text(encoding="utf-8")) or []
    except Exception:
        pass
    return []


def _wb_save(tasks: list) -> None:
    _WB_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WB_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")


def workboard_list() -> dict:
    with _WB_LOCK:
        return {"tasks": _wb_load(), "statuses": list(_WB_STATUSES)}


def workboard_add(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"error": "نص المهمة فارغ"}
    with _WB_LOCK:
        tasks = _wb_load()
        tid = (max((t.get("id", 0) for t in tasks), default=0)) + 1
        tasks.append({"id": tid, "text": text[:300], "status": "pending",
                      "created_at": int(time.time())})
        _wb_save(tasks)
    return {"ok": True, "id": tid}


def workboard_move(task_id: int, direction: str) -> dict:
    """direction: next (→) أو prev (←)."""
    with _WB_LOCK:
        tasks = _wb_load()
        for t in tasks:
            if t.get("id") == int(task_id):
                i = _WB_STATUSES.index(t.get("status", "pending"))
                i = min(i + 1, 2) if direction == "next" else max(i - 1, 0)
                t["status"] = _WB_STATUSES[i]
                _wb_save(tasks)
                return {"ok": True, "status": t["status"]}
    return {"error": "المهمة غير موجودة"}


def workboard_clear_done() -> dict:
    with _WB_LOCK:
        tasks = _wb_load()
        kept = [t for t in tasks if t.get("status") != "done"]
        removed = len(tasks) - len(kept)
        _wb_save(kept)
    return {"ok": True, "removed": removed}


# ══════════════════════════════════════════════════════════════
# SimCore — جسر v2 + تغذية ذاكرة الوكيل وتيليجرام بالقرارات
# ══════════════════════════════════════════════════════════════
SIMCORE_V2_URL = os.environ.get("SIMCORE_V2_URL", "http://127.0.0.1:5001")
SIMCORE_V2_UI  = os.environ.get("SIMCORE_V2_UI", "http://127.0.0.1:5173/simcore")
_V2_CACHE = {"ts": 0.0, "alive": False}

_SIMCORE_DIR = _HOME / "simcore"
_DECISIONS_FILE = _SIMCORE_DIR / "decisions.jsonl"
_INGEST_MARKER = _SIMCORE_DIR / ".agent_ingested"

# توجه SimCore ← سياق الذاكرة الموزونة
_DOMAIN_TO_CONTEXT = {
    "trading": "trading", "education": "academic",
    "engineering": "technical", "security": "technical",
}


def simcore_v2_alive(force: bool = False) -> bool:
    """هل باكند SimCore v2 يعمل؟ (نتيجة مخبأة 5 ثوانٍ)."""
    now = time.time()
    if not force and now - _V2_CACHE["ts"] < 5:
        return _V2_CACHE["alive"]
    alive = False
    try:
        import urllib.request
        req = urllib.request.Request(SIMCORE_V2_URL + "/health")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            alive = r.status == 200
    except Exception:
        alive = False
    _V2_CACHE.update(ts=now, alive=alive)
    return alive


def simcore_v2_forward(method: str, path: str, body: dict = None):
    """يمرّر طلب SimCore إلى باكند v2 ويعيد (json_dict, status)."""
    import urllib.request
    data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8") \
        if method == "POST" else None
    req = urllib.request.Request(
        SIMCORE_V2_URL + path, data=data, method=method,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read()), r.status
    except Exception as e:
        try:
            # أخطاء HTTP تحمل جسم JSON غالباً
            return json.loads(e.read()), e.code            # type: ignore[attr-defined]
        except Exception:
            return {"success": False, "error": f"v2 unreachable: {str(e)[:80]}"}, 502


def simcore_v2_status() -> dict:
    """حالة محرك v2 للوحة + مزامنة قرارات جديدة إن وجدت."""
    alive = simcore_v2_alive(force=True)
    synced = simcore_sync_decisions()
    return {"alive": alive, "url": SIMCORE_V2_URL, "ui": SIMCORE_V2_UI,
            "synced": synced.get("ingested", 0)}


def _read_marker() -> int:
    try:
        return int(_INGEST_MARKER.read_text().strip() or 0)
    except Exception:
        return 0


def _write_marker(ts: int) -> None:
    try:
        _SIMCORE_DIR.mkdir(parents=True, exist_ok=True)
        _INGEST_MARKER.write_text(str(int(ts)))
    except Exception:
        pass


def simcore_sync_decisions() -> dict:
    """يغذي ذاكرة الوكيل وتيليجرام بقرارات SimCore الجديدة (مرة لكل قرار).

    يقرأ decisions.jsonl المشترك (تكتبه النواة المدمجة وv2 كلاهما) ويستوعب
    كل مدخلة أحدث من العلامة. أول تشغيل يضبط العلامة على أحدث قرار دون
    استيعاب رجعي (منعاً لإغراق الذاكرة/تيليجرام بالتاريخ القديم).
    """
    try:
        if not _DECISIONS_FILE.exists():
            return {"ingested": 0}
        lines = _DECISIONS_FILE.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for ln in lines:
            try:
                entries.append(json.loads(ln))
            except Exception:
                continue
        if not entries:
            return {"ingested": 0}
        latest_ts = max(int(e.get("ts", 0)) for e in entries)
        marker = _read_marker()
        if marker == 0:
            _write_marker(latest_ts)
            return {"ingested": 0, "initialized": True}
        new = [e for e in entries if int(e.get("ts", 0)) > marker]
        if not new:
            return {"ingested": 0}
        ingested = 0
        for e in new:
            if _feed_one_decision(e):
                ingested += 1
        _write_marker(latest_ts)
        return {"ingested": ingested}
    except Exception as ex:
        logger.debug("simcore_sync_decisions failed: %s", ex)
        return {"ingested": 0, "error": str(ex)[:80]}


def _feed_one_decision(entry: dict) -> bool:
    """قرار واحد → ذاكرة الوكيل الموزونة + تنبيه تيليجرام عند الخطورة."""
    d = entry.get("decision") or {}
    verdict = str(d.get("decision", "")).strip()
    if not verdict or verdict == "error":
        return False
    domain = str(entry.get("domain", "general"))
    ctx = _DOMAIN_TO_CONTEXT.get(domain, "general")
    conf = float(d.get("confidence") or 0)
    reason = str(d.get("reasoning", ""))[:160]
    action = str(d.get("action", ""))[:120]

    text = (f"قرار SimCore [{domain}] {verdict} (ثقة {round(conf*100)}%)"
            + (f" — {reason}" if reason else "")
            + (f" — الإجراء: {action}" if action else ""))
    try:
        from memory.core.builtin_provider import BuiltinMemoryProvider
        p = BuiltinMemoryProvider()
        p._init_db()
        # الثقة الأعلى تعيش أطول أمام التناقص الزمني
        p.add_entry(text, context=ctx, write_level="auto",
                    weight=1.0 + min(max(conf, 0.0), 1.0) * 0.5)
    except Exception as e:
        logger.debug("simcore memory feed failed: %s", e)
        return False

    # تنبيه تيليجرام: قرار alert، أو إشارة مراقبة high/critical، أو ثقة ≥ 0.85
    try:
        monitor = ((entry.get("inputs") or {}).get("monitor")) or []
        severities = {str(m.get("severity", "")) for m in monitor if isinstance(m, dict)}
        if verdict == "alert" or severities & {"high", "critical"} or conf >= 0.85:
            from tools.agent_tools import send_telegram
            risks = d.get("risks") or []
            msg = ("🚨 SimCore — " + domain + "\n"
                   f"القرار: {verdict} | الثقة: {round(conf*100)}%\n"
                   + (f"السبب: {reason}\n" if reason else "")
                   + (f"الإجراء: {action}\n" if action else "")
                   + (("المخاطر: " + "، ".join(str(r) for r in risks[:3])) if risks else ""))
            send_telegram(msg.strip())
    except Exception as e:
        logger.debug("simcore telegram alert failed: %s", e)
    return True


# ══════════════════════════════════════════════════════════════
# الإقران (Pairing) — طلبات وصول القنوات (ملف JSON)
# ══════════════════════════════════════════════════════════════
_PAIR_FILE = _HOME / "pairing.json"
_PAIR_LOCK = threading.Lock()


def _pair_load() -> dict:
    try:
        if _PAIR_FILE.exists():
            d = json.loads(_PAIR_FILE.read_text(encoding="utf-8")) or {}
            return {"pending": d.get("pending", []), "approved": d.get("approved", [])}
    except Exception:
        pass
    return {"pending": [], "approved": []}


def _pair_save(d: dict) -> None:
    _PAIR_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PAIR_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def pairing_request(platform: str, user_id: str, name: str = "") -> dict:
    """يسجّل طلب إقران جديد (تستدعيه القنوات عند رسالة من غريب)."""
    with _PAIR_LOCK:
        d = _pair_load()
        uid = str(user_id)
        if any(str(p.get("user_id")) == uid and p.get("platform") == platform
               for p in d["pending"] + d["approved"]):
            return {"ok": True, "already": True}
        d["pending"].append({
            "id": (max((p.get("id", 0) for p in d["pending"] + d["approved"]), default=0)) + 1,
            "platform": platform, "user_id": uid, "name": name or "",
            "requested_at": int(time.time()),
        })
        _pair_save(d)
    logger.info("Pairing request: %s/%s", platform, uid)
    return {"ok": True}


def pairing_is_approved(platform: str, user_id: str) -> bool:
    d = _pair_load()
    uid = str(user_id)
    return any(str(p.get("user_id")) == uid and p.get("platform") == platform
               for p in d["approved"])


def pairing_pending() -> dict:
    return {"pending": _pair_load()["pending"]}


def pairing_approved() -> dict:
    return {"approved": _pair_load()["approved"]}


def pairing_approve(req_id: int) -> dict:
    with _PAIR_LOCK:
        d = _pair_load()
        for p in d["pending"]:
            if p.get("id") == int(req_id):
                d["pending"].remove(p)
                p["approved_at"] = int(time.time())
                d["approved"].append(p)
                _pair_save(d)
                return {"ok": True}
    return {"error": "الطلب غير موجود"}


def pairing_reject(req_id: int) -> dict:
    with _PAIR_LOCK:
        d = _pair_load()
        before = len(d["pending"])
        d["pending"] = [p for p in d["pending"] if p.get("id") != int(req_id)]
        _pair_save(d)
    return {"ok": before != len(d["pending"])}


def pairing_unpair(req_id: int) -> dict:
    with _PAIR_LOCK:
        d = _pair_load()
        before = len(d["approved"])
        d["approved"] = [p for p in d["approved"] if p.get("id") != int(req_id)]
        _pair_save(d)
    return {"ok": before != len(d["approved"])}
