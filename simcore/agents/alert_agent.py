"""
AlertAgent — يراقب عتبات محددة ويُبلّغ Telegram فوراً
يعمل بشكل مستقل بدون انتظار دورة تحليل كاملة
"""
from __future__ import annotations
import inspect
import json
import logging
import threading
import time
from typing import List, Dict, Any, Callable, Optional
from .base_agent import BaseAgent
from ..source_manager import SourceManager

logger = logging.getLogger("simcore.alert_agent")


class AlertRule:
    """قاعدة تنبيه واحدة"""
    def __init__(self, rule_id: str, description: str,
                 source_url: str, condition: str,
                 threshold: float = 0.0,
                 api_key: str = None, secret: str = None):
        self.rule_id     = rule_id
        self.description = description
        self.source_url  = source_url
        self.condition   = condition   # "price_above|price_below|keyword|anomaly"
        self.threshold   = threshold
        self.api_key     = api_key
        self.secret      = secret
        self.last_fired  = 0
        self.cooldown    = 300         # 5 دقائق بين كل تنبيه


class AlertAgent(BaseAgent):
    """
    يراقب عتبات: سعر، كلمة مفتاحية، شذوذ.
    عند اكتشاف إشارة يُبلّغ عبر notifier (Telegram).
    يعمل في خيط مستقل بفترة polling قابلة للضبط.
    """

    ALERT_PROMPT = """\
راجع هذه البيانات وتحقق إذا تحقق الشرط التالي:
الشرط: {condition}
العتبة: {threshold}
البيانات: {data}

أجب بـ JSON فقط:
{{
  "triggered": true/false,
  "current_value": "القيمة الحالية",
  "severity": "low|medium|high|critical",
  "message": "رسالة التنبيه للمستخدم"
}}"""

    def __init__(self, system_config, notifier=None):
        super().__init__(
            config=type('cfg', (), {
                'agent_id': 'alert',
                'role': 'alert',
                'domain': 'general',
                'model_key': None,
                'model_url': None,
                'model_name': None,
                'activity': 'background'
            })(),
            system_config=system_config
        )
        self.notifier  = notifier
        self.rules:    List[AlertRule] = []
        self._running  = False
        self._thread:  Optional[threading.Thread] = None

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)
        logger.info("AlertAgent: rule added — %s", rule.description)

    def remove_rule(self, rule_id: str) -> None:
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

    def start(self, interval_seconds: int = 60) -> None:
        """ابدأ المراقبة المستمرة"""
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop,
            args=(interval_seconds,),
            daemon=True,
            name="alert-agent"
        )
        self._thread.start()
        logger.info("AlertAgent started — interval=%ds rules=%d",
                    interval_seconds, len(self.rules))

    def stop(self) -> None:
        self._running = False
        logger.info("AlertAgent stopped")

    def _loop(self, interval: int) -> None:
        while self._running:
            for rule in self.rules:
                try:
                    self._check_rule(rule)
                except Exception as e:
                    logger.warning("AlertAgent rule error %s: %s", rule.rule_id, e)
            time.sleep(interval)

    def _check_rule(self, rule: AlertRule) -> None:
        now   = int(time.time())
        if now - rule.last_fired < rule.cooldown:
            return

        fetch = SourceManager.fetch(rule.source_url, rule.api_key, rule.secret)
        if not fetch["success"]:
            return

        try:
            raw = self.think([
                {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                {"role": "user",   "content": self.ALERT_PROMPT.format(
                    condition=rule.condition,
                    threshold=rule.threshold,
                    data=fetch["content"][:4000]
                )}
            ], temperature=0.1)

            result = json.loads(raw.strip())

            if result.get("triggered"):
                rule.last_fired = now
                msg = f"🚨 تنبيه SimCore\n{rule.description}\n{result.get('message','')}\nالشدة: {result.get('severity','')}"
                logger.warning("AlertAgent TRIGGERED: %s", rule.description)
                self._notify(msg)

        except Exception as e:
            logger.warning("AlertAgent check failed %s: %s", rule.rule_id, e)

    def _notify(self, msg: str) -> None:
        """يُبلّغ عبر notifier — يدعم send المتزامن أو async (core/notifier)."""
        if not self.notifier:
            return
        try:
            res = self.notifier.send(msg)
            if inspect.iscoroutine(res):
                import asyncio
                asyncio.run(res)
        except Exception as e:
            logger.warning("AlertAgent notify failed: %s", e)

    def check_now(self, rule_id: str) -> Dict[str, Any]:
        """اختبار فوري لقاعدة محددة"""
        rule = next((r for r in self.rules if r.rule_id == rule_id), None)
        if not rule:
            return {"error": "القاعدة غير موجودة"}
        self._check_rule(rule)
        return {"ok": True, "last_fired": rule.last_fired}
