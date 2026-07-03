"""Dreaming — صيانة الذاكرة أثناء الخمول.

light_dreaming: تنظيف خفيف عند بدء محادثة جديدة أو تصفير الجلسة.
deep_dreaming:  تنظيف أعمق + ملخص التداول الأسبوعي إلى تيليجرام.
schedule_dreaming: يجدول deep_dreaming كل أحد الساعة 2 صباحاً
(خيط daemon خلفي — نفس آلية مهام الخلفية في المشروع).
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
import time  # noqa: F401 — تستخدمه اليوميات والجدولة

logger = logging.getLogger(__name__)

_SCHEDULED = False

# يوميات الأحلام — سجل JSONL لكل تشغيل light/deep (للوحة التحكم)
from pathlib import Path
_DIARY = Path.home() / ".cobweaverclaw" / "memories" / "dreams.jsonl"


def _diary_append(kind: str, deleted: int, text: str) -> None:
    """يسجّل مدخلة يوميات (آمن — لا يفشل التنظيف بسببها)."""
    try:
        _DIARY.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": int(time.time()),
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": kind, "deleted": int(deleted), "text": (text or "")[:500],
        }
        with open(_DIARY, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("diary append failed: %s", e)


def read_diary(limit: int = 50) -> list:
    """يعيد آخر مدخلات اليوميات (الأحدث أولاً)."""
    try:
        if not _DIARY.exists():
            return []
        lines = _DIARY.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for ln in lines[-max(1, min(int(limit or 50), 200)):]:
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return list(reversed(out))
    except Exception:
        return []


def light_dreaming() -> dict:
    """تنظيف خفيف: يشغّل memory_prune بعتبة 0.1 (يُستدعى عند /new و /reset)."""
    try:
        from tools.agent_tools import execute
        res = json.loads(execute("memory_prune", {"threshold": 0.1}))
        logger.info("light_dreaming: %s", res)
        _diary_append("light", res.get("deleted", 0),
                      f"تنظيف خفيف — حُذفت {res.get('deleted', 0)} ذكرى ضعيفة (عتبة 0.1)")
        return res
    except Exception as e:
        logger.warning("light_dreaming failed: %s", e)
        return {"error": str(e)[:100]}


def deep_dreaming() -> dict:
    """تنظيف عميق: memory_prune بعتبة 0.05 ثم ملخص التداول الأسبوعي إلى تيليجرام."""
    result: dict = {}
    try:
        from tools.agent_tools import execute
        result["prune"] = json.loads(execute("memory_prune", {"threshold": 0.05}))
    except Exception as e:
        result["prune"] = {"error": str(e)[:100]}
    try:
        from memory.trading.trade_memory import init_trade_db, weekly_summary
        init_trade_db()
        summary = weekly_summary()
        result["summary"] = summary
        from tools.agent_tools import send_telegram
        result["telegram"] = send_telegram("💤 Deep Dreaming — صيانة أسبوعية\n\n" + summary)
    except Exception as e:
        result["telegram"] = f"error: {str(e)[:100]}"
    deleted = (result.get("prune") or {}).get("deleted", 0)
    _diary_append("deep", deleted,
                  f"تنظيف عميق — حُذفت {deleted} ذكرى (عتبة 0.05) + ملخص التداول أُرسل لتيليجرام")
    logger.info("deep_dreaming: %s", result)
    return result


def _seconds_until_sunday_2am(now: datetime.datetime | None = None) -> float:
    """يحسب الثواني حتى الأحد القادم الساعة 02:00 (الأحد = weekday 6)."""
    now = now or datetime.datetime.now()
    days_ahead = (6 - now.weekday()) % 7
    target = (now + datetime.timedelta(days=days_ahead)).replace(
        hour=2, minute=0, second=0, microsecond=0
    )
    if target <= now:
        target += datetime.timedelta(days=7)
    return (target - now).total_seconds()


def schedule_dreaming() -> None:
    """يجدول deep_dreaming كل أحد 02:00 في خيط daemon — آمن ولا يتكرّر."""
    global _SCHEDULED
    if _SCHEDULED:
        return
    _SCHEDULED = True

    def _loop() -> None:
        while True:
            time.sleep(_seconds_until_sunday_2am())
            try:
                deep_dreaming()
            except Exception as e:
                logger.warning("scheduled deep_dreaming failed: %s", e)
            time.sleep(60)  # تجاوز دقيقة الهدف قبل حساب الموعد التالي

    threading.Thread(target=_loop, daemon=True, name="dreaming-scheduler").start()
    logger.info("dreaming scheduled: every Sunday 02:00")
