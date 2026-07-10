"""كاشف التلاعب في السوق (Manipulation Detector).

يرصد أنماط التلاعب الشائعة قبل الدخول:
  • Stop Hunt      : اختراق سريع لمستوى ثم ارتداد فوري.
  • Liquidity Grab : ارتفاع حجم مع حركة عكسية (اقتناص سيولة).
  • Fake Breakout  : اختراق بلا حجم كافٍ يفشل بالتثبيت.

بايثون خالص، خفيف على Termux. كل الرسائل بالعربية.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def detect_manipulation(prices: List[float], volumes: Optional[List[float]] = None,
                        order_book: Optional[dict] = None) -> Dict:
    """يحلّل آخر الحركات ويكشف التلاعب المحتمل.

    يعيد: manipulation_detected, type, confidence (0-100),
          warning (عربي), action ∈ {wait, avoid, opportunity}.
    """
    prices = [float(p) for p in (prices or []) if p is not None]
    volumes = [float(v) for v in (volumes or []) if v is not None]

    none_result = {"manipulation_detected": False, "type": None, "confidence": 0,
                   "warning": "", "action": "opportunity"}
    if len(prices) < 5:
        none_result["warning"] = "بيانات غير كافية لكشف التلاعب."
        return none_result

    last = prices[-1]
    prev = prices[-2]
    swing_high = max(prices[:-1])
    swing_low = min(prices[:-1])
    rng = (swing_high - swing_low) or (abs(last) * 0.001) or 1.0

    avg_vol = _mean(volumes[:-1]) if len(volumes) >= 3 else 0.0
    last_vol = volumes[-1] if volumes else 0.0
    vol_ratio = (last_vol / avg_vol) if avg_vol > 0 else 0.0

    # 1) Stop Hunt: اختراق قمّة/قاع ثم ارتداد فوري داخل النطاق
    pierced_high = prev > swing_high * 0.999 or max(prices[-3:]) > swing_high
    pierced_low = prev < swing_low * 1.001 or min(prices[-3:]) < swing_low
    reverted = swing_low <= last <= swing_high
    if (pierced_high or pierced_low) and reverted:
        depth = (max(prices[-3:]) - swing_high) if pierced_high else (swing_low - min(prices[-3:]))
        conf = int(min(95, 55 + abs(depth) / rng * 200))
        side = "قمّة" if pierced_high else "قاع"
        return {"manipulation_detected": True, "type": "stop_hunt", "confidence": conf,
                "warning": f"صيد وقف (Stop Hunt): اختراق {side} ثم ارتداد فوري — تجنّب الدخول العكسي المتسرّع.",
                "action": "wait"}

    # 2) Liquidity Grab: حجم مرتفع جداً مع حركة سعرية عكسية/ضعيفة
    if vol_ratio >= 2.5:
        move = (last - prev) / (abs(prev) or 1)
        if abs(move) < 0.001 or (move > 0 and last < _mean(prices[-4:-1])) \
                or (move < 0 and last > _mean(prices[-4:-1])):
            conf = int(min(95, 50 + vol_ratio * 12))
            return {"manipulation_detected": True, "type": "liquidity_grab", "confidence": conf,
                    "warning": f"اقتناص سيولة (Liquidity Grab): حجم ×{vol_ratio:.1f} مع حركة عكسية — انتظر التأكيد.",
                    "action": "avoid"}

    # 3) Fake Breakout: اختراق نطاق بحجم ضعيف
    broke_up = last > swing_high
    broke_down = last < swing_low
    if (broke_up or broke_down) and avg_vol > 0 and vol_ratio < 1.0:
        conf = int(min(90, 45 + (1.0 - vol_ratio) * 45))
        d = "صاعد" if broke_up else "هابط"
        return {"manipulation_detected": True, "type": "fake_breakout", "confidence": conf,
                "warning": f"اختراق زائف ({d}) بحجم ضعيف (×{vol_ratio:.1f}) — احتمال فشل الاختراق مرتفع.",
                "action": "wait"}

    return none_result


def log_manipulation_event(asset: str, manip_type: str, confidence: int, action: str) -> Dict:
    """يحفظ حدث تلاعب في جدول manipulation_log."""
    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    con.execute(
        "INSERT INTO manipulation_log(asset,type,confidence,action) VALUES (?,?,?,?)",
        (asset, manip_type, int(confidence), action),
    )
    con.commit()
    con.close()
    return {"ok": True}


def recent_manipulations(limit: int = 10) -> List[Dict]:
    """آخر أحداث التلاعب المسجّلة — للوحة التحكم."""
    try:
        from memory.trading.trade_memory import _con, init_trade_db
        init_trade_db()
        con = _con()
        rows = con.execute(
            "SELECT asset,type,confidence,action,timestamp FROM manipulation_log"
            " ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        con.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
