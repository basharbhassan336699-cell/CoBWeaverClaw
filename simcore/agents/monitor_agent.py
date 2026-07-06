"""
SimCore — وكيل المراقبة
مرتبط بمنصة عبر مفتاحها. مثال: Binance لتتبع الحيتان.
يعمل في الخلفية ويُبلّغ عند اكتشاف إشارة.
"""
import time
import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..source_manager import SourceManager

logger = logging.getLogger("simcore.monitor")


class MonitorAgent(BaseAgent):
    """
    دوره: مراقبة مستمرة لمنصة محددة.
    يكتشف: تحركات كبيرة، حيتان، أخبار عاجلة.
    يُبلّغ: OracleAgent بما وجد.
    """

    MONITOR_PROMPT = """\
أنت وكيل مراقبة متخصص في {domain}.
راجع البيانات التالية من {source_name} وابحث عن:
- تحركات غير عادية أو إشارات مهمة
- أي شيء يستحق تنبيه فوري

البيانات:
{data}

أجب بـ JSON:
{{
  "has_signal": true/false,
  "signal_type": "whale_move|news_break|anomaly|none",
  "severity": "low|medium|high|critical",
  "summary": "ملخص قصير",
  "details": "تفاصيل"
}}
"""

    def monitor_once(self, source_url: str, source_name: str,
                     api_key: str = None, account_id: str = None,
                     secret: str = None) -> Dict[str, Any]:
        """دورة مراقبة واحدة"""
        fetch = SourceManager.fetch(source_url, api_key=api_key,
                                    secret=secret, account_id=account_id)
        if not fetch["success"]:
            return {"has_signal": False, "error": fetch["error"]}

        domain = self.config.domain or self.system_config.domain
        prompt = self.MONITOR_PROMPT.format(
            domain=domain,
            source_name=source_name,
            data=fetch["content"][:8000],
        )
        try:
            import json
            raw = self.think([
                {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                {"role": "user",   "content": prompt},
            ], temperature=0.2)
            return json.loads(raw)
        except Exception as e:
            return {"has_signal": False, "error": str(e)}
