"""
ExecutorAgent — ينفذ قرارات OracleAgent على المنصة المربوطة
يُفعَّل فقط إذا أذن المستخدم صراحةً
"""
from __future__ import annotations
import inspect
import json
import logging
import time
import hmac
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from .base_agent import BaseAgent

logger = logging.getLogger("simcore.executor_agent")

EXECUTIONS_LOG = Path.home() / ".cobweaverclaw" / "simcore" / "executions.jsonl"


class ExecutorAgent(BaseAgent):
    """
    يستقبل قرار OracleAgent وينفذه على المنصة.
    يسجّل كل تنفيذ في executions.jsonl.
    يُبلّغ عبر notifier بالنتيجة.
    مُعطَّل افتراضياً — يحتاج enabled=True صريحاً.
    """

    def __init__(self, system_config, notifier=None, enabled: bool = False):
        super().__init__(
            config=type('cfg', (), {
                'agent_id': 'executor',
                'role': 'executor',
                'domain': 'trading',
                'model_key': None,
                'model_url': None,
                'model_name': None,
                'activity': 'deep'
            })(),
            system_config=system_config
        )
        self.notifier = notifier
        self.enabled  = enabled

        if self.enabled:
            logger.warning("ExecutorAgent ENABLED — سيُنفذ صفقات حقيقية")

    def execute(self, decision: Dict[str, Any],
                platform: Dict[str, Any]) -> Dict[str, Any]:
        """
        نفّذ قرار OracleAgent على المنصة.
        decision: {"decision": "buy|sell", "confidence": 0.9, ...}
        platform: {"name": "Binance", "base_url": "...", "api_key": "...", "secret_key": "..."}
        """
        if not self.enabled:
            return {"executed": False,
                    "reason": "ExecutorAgent معطّل — فعّله صراحةً من الإعدادات"}

        action = decision.get("decision", "")
        if action not in ("buy", "sell"):
            return {"executed": False,
                    "reason": f"القرار '{action}' لا يستدعي تنفيذاً"}

        confidence = float(decision.get("confidence", 0.0))
        if confidence < 0.75:
            return {"executed": False,
                    "reason": f"الثقة {confidence:.0%} أقل من الحد المطلوب 75%"}

        result = self._execute_on_platform(action, platform, decision)
        self._log(decision, platform, result)

        status = "✅ نُفِّذ" if result.get("success") else "❌ فشل"
        self._notify(
            f"{status} ExecutorAgent\n"
            f"القرار: {action.upper()}\n"
            f"المنصة: {platform.get('name','')}\n"
            f"{result.get('message','')}"
        )

        # نعلّم أنّ التنفيذ جرى فعلاً (نجح أو فشل) لتمييزه عن الرفض المسبق
        result.setdefault("executed", True)
        return result

    def _execute_on_platform(self, action: str,
                              platform: Dict,
                              decision: Dict) -> Dict[str, Any]:
        url_l      = platform.get("base_url", "").lower()
        api_key    = platform.get("api_key", "")
        secret_key = platform.get("secret_key", "")

        try:
            # Binance
            if "binance" in url_l:
                ts    = int(time.time() * 1000)
                side  = "BUY" if action == "buy" else "SELL"
                params = {
                    "symbol":    decision.get("asset", "BTCUSDT"),
                    "side":      side,
                    "type":      "MARKET",
                    "quoteOrderQty": decision.get("amount", 10),
                    "timestamp": ts,
                }
                query = "&".join(f"{k}={v}" for k, v in params.items())
                sig   = hmac.new(secret_key.encode(), query.encode(),
                                 hashlib.sha256).hexdigest()
                params["signature"] = sig

                r = requests.post(
                    "https://api.binance.com/api/v3/order",
                    headers={"X-MBX-APIKEY": api_key},
                    params=params, timeout=10
                )
                data = r.json()
                if r.status_code == 200:
                    return {"success": True,
                            "order_id": data.get("orderId"),
                            "message":  f"أمر {side} نُفِّذ — orderId: {data.get('orderId')}",
                            "data":     data}
                return {"success": False,
                        "message": f"Binance خطأ: {data.get('msg', r.status_code)}"}

            # Bybit
            elif "bybit" in url_l:
                ts    = str(int(time.time() * 1000))
                side  = "Buy" if action == "buy" else "Sell"
                body  = json.dumps({
                    "category": "spot",
                    "symbol":   decision.get("asset", "BTCUSDT"),
                    "side":     side,
                    "orderType": "Market",
                    "qty":      str(decision.get("amount", 10)),
                })
                msg = ts + api_key + "5000" + body
                sig = hmac.new(secret_key.encode(), msg.encode(),
                               hashlib.sha256).hexdigest()
                r = requests.post(
                    "https://api.bybit.com/v5/order/create",
                    headers={"X-BAPI-API-KEY": api_key,
                             "X-BAPI-TIMESTAMP": ts,
                             "X-BAPI-SIGN": sig,
                             "X-BAPI-RECV-WINDOW": "5000",
                             "Content-Type": "application/json"},
                    data=body, timeout=10
                )
                data = r.json()
                if data.get("retCode") == 0:
                    return {"success": True,
                            "message": f"Bybit {side} نُفِّذ",
                            "data":    data.get("result")}
                return {"success": False,
                        "message": f"Bybit خطأ: {data.get('retMsg')}"}

            else:
                return {"success": False,
                        "message": f"المنصة غير مدعومة بعد: {platform.get('name','')}"}

        except requests.exceptions.Timeout:
            return {"success": False, "message": "انتهت مهلة الاتصال بالمنصة"}
        except Exception as e:
            return {"success": False, "message": str(e)}

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
            logger.warning("ExecutorAgent notify failed: %s", e)

    def _log(self, decision: Dict, platform: Dict, result: Dict) -> None:
        try:
            EXECUTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts":       int(time.time()),
                "decision": decision,
                "platform": platform.get("name", ""),
                "result":   result,
            }
            with EXECUTIONS_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("ExecutorAgent log failed: %s", e)
