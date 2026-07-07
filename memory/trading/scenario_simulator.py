"""محاكي ما قبل التنفيذ (Pre-Execution Simulator).

يشغّل محاكاة مونت-كارلو بسيطة لتقدير احتمال نجاح الصفقة قبل الدخول،
معتمداً على: إحصاءات الأنماط التاريخية + حالة السوق + احتمال التلاعب.

الصفقة تُنفَّذ فقط إذا signal_score ≥ 75.
بايثون خالص، خفيف على Termux. كل الرسائل بالعربية.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional


def _pattern_winrate(pattern: Optional[str]):
    """(win_rate%, عدد العينات) للنمط من قاعدة التداول، أو (None,0)."""
    if not pattern:
        return None, 0
    try:
        from memory.trading.trade_memory import get_pattern_stats
        for s in get_pattern_stats():
            if s.get("pattern") == pattern:
                samples = (s.get("wins", 0) or 0) + (s.get("losses", 0) or 0)
                return (s.get("win_rate"), samples) if samples else (None, 0)
    except Exception:
        pass
    return None, 0


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def calculate_signal_score(timeframe_alignment: float, order_block_strength: float,
                           volume_confirmation: float, market_direction: float,
                           manipulation_risk: float) -> int:
    """مجموع نقاط الإشارة (0-100).

    manipulation_risk معكوس: قيمة أعلى = خطر تلاعب أقل (أفضل).
    """
    total = (_clamp(timeframe_alignment, 0, 30)
             + _clamp(order_block_strength, 0, 25)
             + _clamp(volume_confirmation, 0, 20)
             + _clamp(market_direction, 0, 15)
             + _clamp(manipulation_risk, 0, 10))
    return int(round(_clamp(total, 0, 100)))


def simulate_trade(asset: str, entry: float, tp: Optional[float] = None,
                   sl: Optional[float] = None, pattern: Optional[str] = None,
                   regime: str = "auto", n_scenarios: int = 100,
                   prices: Optional[List[float]] = None,
                   volumes: Optional[List[float]] = None) -> Dict:
    """يحاكي الصفقة ويعيد توصية مبنية على signal_score."""
    try:
        entry = float(entry)
    except (TypeError, ValueError):
        return {"recommended": False, "win_probability": 0, "expected_pnl": 0.0,
                "risk_reward_actual": 0.0, "signal_score": 0,
                "reasoning": "سعر الدخول غير صالح."}

    tp = float(tp) if tp not in (None, "") else None
    sl = float(sl) if sl not in (None, "") else None

    # نسبة العائد/المخاطرة الفعلية
    risk = abs(entry - sl) if sl is not None else None
    reward = abs(tp - entry) if tp is not None else None
    rr = (reward / risk) if (risk and reward and risk > 0) else 0.0
    reward_pct = (reward / entry * 100) if (reward and entry) else 1.0
    risk_pct = (risk / entry * 100) if (risk and entry) else 1.0

    # احتمال أساسي من تاريخ النمط (وإلا محايد 55%)
    wr, samples = _pattern_winrate(pattern)
    base_win = (wr / 100.0) if wr is not None else 0.55

    # حالة السوق (إن توفّرت أسعار)
    regime_info = None
    if prices and len(prices) >= 5:
        try:
            from memory.trading.regime_detector import detect_regime
            regime_info = detect_regime(prices, volumes)
        except Exception:
            regime_info = None

    # احتمال التلاعب (إن توفّرت أسعار)
    manip = None
    if prices and len(prices) >= 5:
        try:
            from memory.trading.manipulation_detector import detect_manipulation
            manip = detect_manipulation(prices, volumes)
        except Exception:
            manip = None

    # ── مكوّنات النقاط (قيم افتراضية متساهلة تُخفَّض عند خطر حقيقي) ──
    timeframe_alignment = 24.0     # 0-30
    order_block_strength = 20.0    # 0-25
    volume_confirmation = 15.0     # 0-20
    market_direction = 12.0        # 0-15
    manipulation_risk = 8.0        # 0-10 (أعلى = أأمن)
    notes = []

    if wr is not None and samples >= 3:
        order_block_strength = _clamp(wr / 100 * 25, 0, 25)
        if wr < 40:
            timeframe_alignment -= 8
            notes.append(f"النمط «{pattern}» win rate تاريخي {wr}% (ضعيف).")
        elif wr >= 60:
            notes.append(f"النمط «{pattern}» win rate تاريخي {wr}% (قوي).")

    if rr:
        if rr < 1:
            order_block_strength -= 6
            timeframe_alignment -= 4
            notes.append(f"عائد/مخاطرة ضعيف ({rr:.2f} < 1).")
        elif rr >= 2:
            timeframe_alignment = _clamp(timeframe_alignment + 3, 0, 30)
            notes.append(f"عائد/مخاطرة جيّد ({rr:.2f}).")
    else:
        notes.append("لم يُحدَّد TP/SL — تقدير محايد للعائد/المخاطرة.")

    if regime_info:
        reg = regime_info["regime"]
        if reg == "volatile":
            market_direction -= 6
            volume_confirmation -= 5
            notes.append("السوق متقلّب — خطر أعلى.")
        elif reg == "trending":
            market_direction = _clamp(market_direction + 3, 0, 15)
            notes.append(f"سوق باتجاه ({regime_info['strength']}%).")
        else:
            notes.append("سوق عرضي — دخول انتقائي.")

    if manip and manip.get("manipulation_detected"):
        conf = manip.get("confidence", 0)
        manipulation_risk = _clamp(10 - conf / 10, 0, 10)
        volume_confirmation -= 4
        notes.append(manip.get("warning", "تلاعب محتمل."))

    signal_score = calculate_signal_score(
        timeframe_alignment, order_block_strength,
        volume_confirmation, market_direction, manipulation_risk)

    # تعديل احتمال الفوز بعامل الإشارة
    win_prob = _clamp(base_win * (0.6 + 0.4 * signal_score / 100), 0.01, 0.99)

    # مونت-كارلو
    n = max(1, int(n_scenarios))
    rnd = random.Random(hash((asset, round(entry, 6), pattern or "", signal_score)) & 0xFFFFFFFF)
    pnls = [reward_pct if rnd.random() < win_prob else -risk_pct for _ in range(n)]
    expected_pnl = sum(pnls) / n

    recommended = signal_score >= 75
    verdict = "يُنصح بالتنفيذ" if recommended else "لا يُنصح — الإشارة دون العتبة (75)"
    reasoning = (f"{verdict}. signal_score={signal_score}/100، "
                 f"احتمال الفوز≈{win_prob*100:.0f}%، عائد متوقّع≈{expected_pnl:.2f}%. "
                 + " ".join(notes))

    return {"recommended": recommended,
            "win_probability": int(round(win_prob * 100)),
            "expected_pnl": round(expected_pnl, 2),
            "risk_reward_actual": round(rr, 2),
            "signal_score": signal_score,
            "regime": (regime_info or {}).get("regime", regime),
            "reasoning": reasoning}
