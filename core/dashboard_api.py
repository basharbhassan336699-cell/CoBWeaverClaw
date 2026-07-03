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
