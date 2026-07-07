"""مكابح الطوارئ (Emergency Stop).

يراقب أداء التداول ويوقف الدخول تلقائياً عند تجاوز حدود الخطر
(خسارة يومية/أسبوعية أو خسائر متتالية)، مع فترة تهدئة وتنبيه Telegram.

يقرأ/يكتب نفس قاعدة بيانات التداول. كل الرسائل بالعربية.
"""
from __future__ import annotations

import datetime
import time
from typing import Dict, List, Optional

EMERGENCY_RULES = {
    "max_daily_loss_pct": -3.0,
    "max_consecutive_losses": 3,
    "max_weekly_loss_pct": -7.0,
    "cooldown_hours": 24,
}


# ── قراءة الإحصاءات من قاعدة التداول ──────────────────────────
def _closed_trades(since_ts: int) -> List[Dict]:
    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    rows = con.execute(
        "SELECT outcome,pnl_pct,closed_at FROM trades"
        " WHERE closed_at IS NOT NULL AND closed_at>=? ORDER BY closed_at DESC",
        (since_ts,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def _consecutive_losses() -> int:
    """عدد الخسائر المتتالية من أحدث الصفقات المغلقة للخلف."""
    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    rows = con.execute(
        "SELECT outcome,pnl_pct FROM trades WHERE closed_at IS NOT NULL"
        " ORDER BY closed_at DESC LIMIT 50").fetchall()
    con.close()
    n = 0
    for r in rows:
        loss = (r["outcome"] == "hit_sl") or ((r["pnl_pct"] or 0) < 0)
        if loss:
            n += 1
        else:
            break
    return n


def check_emergency_conditions() -> Dict:
    """يفحص شروط الطوارئ ويعيد الحالة والإحصاءات."""
    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 7 * 86400

    daily = sum((t["pnl_pct"] or 0) for t in _closed_trades(day_ago))
    weekly = sum((t["pnl_pct"] or 0) for t in _closed_trades(week_ago))
    consec = _consecutive_losses()

    stats = {"daily_loss_pct": round(daily, 2),
             "weekly_loss_pct": round(weekly, 2),
             "consecutive_losses": consec}

    reason = ""
    if daily <= EMERGENCY_RULES["max_daily_loss_pct"]:
        reason = (f"تجاوز حدّ الخسارة اليومية: {daily:.2f}% "
                  f"(الحدّ {EMERGENCY_RULES['max_daily_loss_pct']}%).")
    elif consec >= EMERGENCY_RULES["max_consecutive_losses"]:
        reason = (f"خسائر متتالية: {consec} "
                  f"(الحدّ {EMERGENCY_RULES['max_consecutive_losses']}).")
    elif weekly <= EMERGENCY_RULES["max_weekly_loss_pct"]:
        reason = (f"تجاوز حدّ الخسارة الأسبوعية: {weekly:.2f}% "
                  f"(الحدّ {EMERGENCY_RULES['max_weekly_loss_pct']}%).")

    emergency = bool(reason)
    cooldown_until = None
    if emergency:
        cooldown_until = datetime.datetime.now() + datetime.timedelta(
            hours=EMERGENCY_RULES["cooldown_hours"])

    return {"emergency": emergency, "reason": reason,
            "cooldown_until": cooldown_until, "stats": stats}


# ── التخزين + التفعيل ─────────────────────────────────────────
def _active_cooldown_row() -> Optional[Dict]:
    """آخر إيقاف طوارئ لا تزال فترة تهدئته سارية."""
    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    row = con.execute(
        "SELECT reason,cooldown_until,report,timestamp FROM emergency_log"
        " ORDER BY id DESC LIMIT 1").fetchone()
    con.close()
    if not row:
        return None
    cu = row["cooldown_until"]
    if not cu:
        return None
    try:
        until = datetime.datetime.fromisoformat(cu)
    except Exception:
        return None
    return dict(row) if until > datetime.datetime.now() else None


def activate_emergency_stop(reason: str) -> Dict:
    """يسجّل الطوارئ، يولّد تقريراً، ويرسل تنبيه Telegram."""
    cond = check_emergency_conditions()
    stats = cond["stats"]
    cooldown_until = (cond["cooldown_until"]
                      or datetime.datetime.now()
                      + datetime.timedelta(hours=EMERGENCY_RULES["cooldown_hours"]))
    report = generate_emergency_report(reason, stats, cooldown_until)

    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    con.execute(
        "INSERT INTO emergency_log(reason,daily_loss_pct,consecutive_losses,"
        "cooldown_until,report) VALUES (?,?,?,?,?)",
        (reason, stats["daily_loss_pct"], stats["consecutive_losses"],
         cooldown_until.isoformat(), report),
    )
    con.commit()
    con.close()

    sent = _send_alert(report)
    return {"ok": True, "reason": reason, "report": report,
            "cooldown_until": cooldown_until.isoformat(), "telegram_sent": sent}


def is_trading_allowed() -> bool:
    """يُستدعى قبل أي صفقة — False إذا كان النظام في طوارئ سارية.

    يفعّل الطوارئ تلقائياً عند تحقّق شروطها لأول مرة.
    """
    try:
        if _active_cooldown_row():
            return False
        cond = check_emergency_conditions()
        if cond["emergency"]:
            activate_emergency_stop(cond["reason"])
            return False
        return True
    except Exception:
        # عند أي خلل لا نمنع التداول (فشل آمن)
        return True


def generate_emergency_report(reason: str = "", stats: Optional[Dict] = None,
                              cooldown_until=None) -> str:
    """يولّد تقرير Markdown بالعربية يشرح سبب الإيقاف."""
    if stats is None:
        cond = check_emergency_conditions()
        stats = cond["stats"]
        reason = reason or cond["reason"]
        cooldown_until = cooldown_until or cond["cooldown_until"]
    cu = ""
    if cooldown_until:
        cu = (cooldown_until.strftime("%Y-%m-%d %H:%M")
              if hasattr(cooldown_until, "strftime") else str(cooldown_until))
    lines = [
        "🚨 *تفعيل مكابح الطوارئ*",
        "",
        f"*السبب:* {reason or 'غير محدّد'}",
        "",
        "*الإحصاءات:*",
        f"• الخسارة اليومية: {stats.get('daily_loss_pct', 0)}%",
        f"• الخسارة الأسبوعية: {stats.get('weekly_loss_pct', 0)}%",
        f"• خسائر متتالية: {stats.get('consecutive_losses', 0)}",
        "",
        f"⏸️ التداول موقوف حتى: `{cu}`" if cu else "⏸️ التداول موقوف.",
        "",
        "راجع خطتك وأدِر المخاطر قبل استئناف الدخول.",
    ]
    return "\n".join(lines)


def emergency_state() -> Dict:
    """الحالة الحالية للطوارئ — للوحة التحكم (لا يفعّل شيئاً)."""
    active = _active_cooldown_row()
    cond = check_emergency_conditions()
    return {"active": bool(active),
            "reason": (active or {}).get("reason") or cond["reason"],
            "cooldown_until": (active or {}).get("cooldown_until"),
            "stats": cond["stats"],
            "rules": EMERGENCY_RULES}


# ── تنبيه Telegram (عبر قناة المشروع الموحّدة) ────────────────
def _send_alert(text: str) -> bool:
    """يرسل تنبيه الطوارئ عبر نفس بوت Telegram المستخدم في core/notifier."""
    try:
        from tools.agent_tools import send_telegram
        res = send_telegram(text)
        if isinstance(res, str) and "✅" in res:
            return True
    except Exception:
        pass
    # احتياط: إشعار طرفية عبر core/notifier
    try:
        import asyncio
        from core.notifier import CLINotifier
        asyncio.run(CLINotifier().send(text))
    except Exception:
        pass
    return False
