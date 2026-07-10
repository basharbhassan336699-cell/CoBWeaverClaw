"""كاشف حالة السوق (Regime Detector).

يحلّل سلسلة الأسعار والأحجام ويحدّد حالة السوق تلقائياً
(اتجاه/تذبذب/تقلّب) ثم يختار الاستراتيجية المناسبة.

مؤشرات مبسّطة بلغة بايثون الخالصة (بلا numpy/pandas) لتبقى خفيفة على Termux.
كل الرسائل بالعربية. يخزّن السجل في نفس قاعدة بيانات التداول.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Dict, List, Optional


# ── مؤشرات مساعدة (بايثون خالص) ──────────────────────────────
def _ema(values: List[float], period: int) -> Optional[float]:
    """المتوسط المتحرك الأسّي لآخر قيمة."""
    if not values or period <= 0 or len(values) < 1:
        return None
    period = min(period, len(values))
    k = 2.0 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _atr(prices: List[float], period: int = 14) -> float:
    """تقريب ATR من فروق الإغلاق المطلقة (متاحة لدينا الإغلاقات فقط)."""
    if len(prices) < 2:
        return 0.0
    trs = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
    window = trs[-period:] if len(trs) > period else trs
    return sum(window) / len(window) if window else 0.0


def _adx_like(prices: List[float], period: int = 14) -> float:
    """مؤشر قوة اتجاه مبسّط (0-100) من اتساق الحركة الاتجاهية.

    ليس ADX الرسمي (يحتاج high/low) بل تقدير من نسبة الحركات المتوافقة
    اتجاهياً مضروبة في اتساع فصل EMA — كافٍ لتصنيف الحالة.
    """
    if len(prices) < period + 1:
        if len(prices) < 3:
            return 0.0
    window = prices[-(period + 1):] if len(prices) > period + 1 else prices
    ups = downs = 0.0
    for i in range(1, len(window)):
        d = window[i] - window[i - 1]
        if d > 0:
            ups += d
        elif d < 0:
            downs += -d
    total = ups + downs
    if total == 0:
        return 0.0
    directional = abs(ups - downs) / total          # 0..1 اتساق الاتجاه
    ema_f = _ema(prices, max(2, period // 3)) or prices[-1]
    ema_s = _ema(prices, period) or prices[-1]
    sep = abs(ema_f - ema_s) / (abs(ema_s) or 1)     # اتساع فصل EMA
    score = directional * 70 + min(sep * 300, 30)    # حتى 100
    return round(min(score, 100.0), 1)


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# ── الكشف ────────────────────────────────────────────────────
def detect_regime(prices: List[float], volumes: Optional[List[float]] = None) -> Dict:
    """يحدّد حالة السوق ويختار الاستراتيجية.

    يعيد: regime, strength (0-100), recommended_strategy, reasoning (عربي).
    """
    prices = [float(p) for p in (prices or []) if p is not None]
    volumes = [float(v) for v in (volumes or []) if v is not None]

    if len(prices) < 5:
        return {"regime": "ranging", "strength": 0,
                "recommended_strategy": "انتظار بيانات كافية",
                "reasoning": "بيانات السعر غير كافية للتحليل (أقل من 5 نقاط)."}

    adx = _adx_like(prices)
    ema20 = _ema(prices, 20) or prices[-1]
    ema50 = _ema(prices, 50) or prices[-1]
    atr = _atr(prices)
    atr_ref = _atr(prices, period=max(20, len(prices)))       # مرجع أطول
    price_ref = _mean(prices[-max(20, len(prices)):]) or 1.0
    atr_pct = (atr / (abs(price_ref) or 1)) * 100

    vol_spike = False
    if len(volumes) >= 4:
        recent_v = volumes[-1]
        avg_v = _mean(volumes[:-1]) or recent_v
        vol_spike = avg_v > 0 and recent_v > 3 * avg_v

    ema_gap = (ema20 - ema50) / (abs(ema50) or 1) * 100
    trend_up = ema20 > ema50

    # قرار الحالة
    if vol_spike or (atr_ref > 0 and atr > 2 * atr_ref) or atr_pct > 4:
        regime = "volatile"
        strength = int(min(100, 50 + atr_pct * 8 + (25 if vol_spike else 0)))
        reasoning = (f"تقلّب مرتفع: ATR≈{atr_pct:.2f}% من السعر"
                     + ("، وقفزة حجم غير معتادة (>3×)." if vol_spike
                        else "، فوق ضعف المتوسط."))
    elif adx > 25 and abs(ema_gap) > 0.15:
        regime = "trending"
        strength = int(min(100, adx))
        d = "صاعد" if trend_up else "هابط"
        reasoning = (f"اتجاه {d} واضح: ADX≈{adx:.0f}>25، "
                     f"وفصل EMA20/50 = {ema_gap:+.2f}%.")
    else:
        regime = "ranging"
        strength = int(min(100, max(0, 60 - adx)))
        reasoning = (f"سوق عرضي: ADX≈{adx:.0f} ضعيف، "
                     f"وفصل EMA ضيّق ({ema_gap:+.2f}%)، تذبذب داخل نطاق.")

    strat = get_strategy_for_regime(regime)
    return {"regime": regime, "strength": max(0, min(100, strength)),
            "recommended_strategy": strat["primary"],
            "strategies": strat["all"],
            "reasoning": reasoning}


def get_strategy_for_regime(regime: str) -> Dict:
    """يعيد الاستراتيجيات المناسبة لحالة السوق."""
    table = {
        "trending": ["ICT Continuation", "EMA Pullback", "Breakout Retest"],
        "ranging":  ["Order Block Fade", "Support/Resistance Bounce"],
        "volatile": ["تضييق الحجم 50%", "انتظار تثبيت", "لا دخول جديد"],
    }
    all_ = table.get(regime, ["انتظار"])
    return {"primary": all_[0], "all": all_}


# ── التخزين ──────────────────────────────────────────────────
def save_regime_log(asset: str, regime: str, strength: int, strategy: str) -> Dict:
    """يحفظ نتيجة كشف الحالة في جدول regime_log."""
    from memory.trading.trade_memory import _con, init_trade_db
    init_trade_db()
    con = _con()
    con.execute(
        "INSERT INTO regime_log(asset,regime,strength,strategy) VALUES (?,?,?,?)",
        (asset, regime, int(strength), strategy),
    )
    con.commit()
    con.close()
    return {"ok": True}


def latest_regime(asset: Optional[str] = None) -> Optional[Dict]:
    """آخر حالة سوق مسجّلة (لأصل معيّن أو عموماً) — للوحة التحكم."""
    try:
        from memory.trading.trade_memory import _con, init_trade_db
        init_trade_db()
        con = _con()
        if asset:
            row = con.execute(
                "SELECT asset,regime,strength,strategy,timestamp FROM regime_log"
                " WHERE asset=? ORDER BY id DESC LIMIT 1", (asset,)).fetchone()
        else:
            row = con.execute(
                "SELECT asset,regime,strength,strategy,timestamp FROM regime_log"
                " ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        return dict(row) if row else None
    except Exception:
        return None
