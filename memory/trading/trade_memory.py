"""ذاكرة التداول المتخصصة — مستقلة عن memory_manager."""
from __future__ import annotations
import sqlite3, time
from pathlib import Path
from typing import Dict, List, Optional
from cobweaverclaw_constants import get_config_path

TRADE_DB = get_config_path() / "memories" / "trades.db"

def _con() -> sqlite3.Connection:
    TRADE_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(TRADE_DB)
    con.row_factory = sqlite3.Row
    return con

def init_trade_db() -> None:
    con = _con()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            asset      TEXT    NOT NULL,
            entry      REAL    NOT NULL,
            tp         REAL, sl REAL,
            outcome    TEXT, pattern TEXT, session TEXT,
            pnl_pct    REAL, notes TEXT,
            opened_at  INTEGER NOT NULL,
            closed_at  INTEGER
        );
        CREATE TABLE IF NOT EXISTS pattern_stats (
            pattern   TEXT PRIMARY KEY,
            wins      INTEGER DEFAULT 0,
            losses    INTEGER DEFAULT 0,
            total_pnl REAL    DEFAULT 0.0,
            last_seen INTEGER
        );
        CREATE TABLE IF NOT EXISTS regime_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT, regime TEXT, strength INTEGER,
            strategy TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS manipulation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT, type TEXT, confidence INTEGER,
            action TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS emergency_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reason TEXT, daily_loss_pct REAL,
            consecutive_losses INTEGER, cooldown_until DATETIME,
            report TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    con.commit(); con.close()

def log_trade(asset: str, entry: float, tp: Optional[float]=None,
              sl: Optional[float]=None, pattern: Optional[str]=None,
              session: Optional[str]=None, notes: Optional[str]=None) -> Dict:
    # ── حارس ما قبل التنفيذ: مكابح الطوارئ + محاكاة قوة الإشارة ──
    # (فشل آمن: أي خلل في الوحدات لا يمنع التسجيل؛ فقط قرار صريح يمنع)
    try:
        from memory.trading.emergency_stop import is_trading_allowed
        if not is_trading_allowed():
            return {"ok": False, "error": "النظام في وضع الطوارئ، التداول موقوف"}
    except Exception:
        pass
    try:
        from memory.trading.scenario_simulator import simulate_trade
        simulation = simulate_trade(asset, entry, tp, sl, pattern, regime="auto")
        if simulation.get("signal_score", 100) < 75:
            return {"ok": False,
                    "error": f"الإشارة ضعيفة ({simulation['signal_score']}/100)، لم تُنفَّذ",
                    "simulation": simulation}
    except Exception:
        pass
    now = int(time.time())
    con = _con()
    cur = con.execute(
        "INSERT INTO trades(asset,entry,tp,sl,pattern,session,notes,opened_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (asset, entry, tp, sl, pattern, session, notes, now),
    )
    trade_id = cur.lastrowid
    con.commit(); con.close()
    return {"ok": True, "trade_id": trade_id}

def close_trade(trade_id: int, outcome: str, pnl_pct: float) -> Dict:
    now = int(time.time())
    con = _con()
    con.execute(
        "UPDATE trades SET outcome=?,pnl_pct=?,closed_at=? WHERE id=?",
        (outcome, pnl_pct, now, trade_id),
    )
    row = con.execute("SELECT pattern FROM trades WHERE id=?", (trade_id,)).fetchone()
    if row and row["pattern"]:
        won = 1 if outcome == "hit_tp" else 0
        con.execute("""
            INSERT INTO pattern_stats(pattern,wins,losses,total_pnl,last_seen)
            VALUES (?,?,?,?,?)
            ON CONFLICT(pattern) DO UPDATE SET
                wins=wins+excluded.wins, losses=losses+excluded.losses,
                total_pnl=total_pnl+excluded.total_pnl, last_seen=excluded.last_seen
        """, (row["pattern"], won, 1-won, pnl_pct, now))
    con.commit(); con.close()
    return {"ok": True}

def get_pattern_stats() -> List[Dict]:
    con  = _con()
    rows = con.execute(
        "SELECT pattern,wins,losses,total_pnl FROM pattern_stats ORDER BY total_pnl DESC"
    ).fetchall()
    con.close()
    return [{
        "pattern": r["pattern"], "wins": r["wins"], "losses": r["losses"],
        "win_rate": round(r["wins"]/(r["wins"]+r["losses"])*100,1) if (r["wins"]+r["losses"]) else 0,
        "total_pnl": round(r["total_pnl"], 2),
    } for r in rows]

def weekly_summary() -> str:
    stats = get_pattern_stats()
    if not stats: return "لا توجد صفقات مسجّلة."
    lines = ["📊 *ملخص التداول الأسبوعي*\n"]
    for s in stats[:5]:
        lines.append(
            f"• `{s['pattern']}` — ربح: {s['wins']} | خسارة: {s['losses']}"
            f" | win rate: {s['win_rate']}% | PnL: {s['total_pnl']}%"
        )
    return "\n".join(lines)
