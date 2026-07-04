"""
SimCore — وكيل المراقبة
يراقب أي منصة أو API مرتبطة بمفتاح ويكتشف الإشارات حسب التوجه
"""
import json, logging
from typing import Dict, Any, Optional
from openai import OpenAI
from .source_manager import SourceManager
from ..config import Config

logger = logging.getLogger("simcore.monitor")


class MonitorAgent:
    PROMPT = """\
أنت وكيل مراقبة متخصص في مجال: {domain}.
راجع البيانات التالية من المصدر "{source_name}" وابحث عن إشارات مهمة ذات صلة بتوجهك.

البيانات:
{data}

أجب بـ JSON فقط بدون أي نص إضافي:
{{"has_signal":true,"signal_type":"whale_move|news_break|price_spike|anomaly|trend_shift|none","severity":"low|medium|high|critical","summary":"ملخص الإشارة","details":"تفاصيل إضافية"}}"""

    def __init__(self, domain: str,
                 model_key: Optional[str] = None,
                 model_url: Optional[str] = None,
                 model_name: Optional[str] = None):
        self.domain = domain
        key  = model_key  or Config.SIMCORE_MONITOR_KEY  or Config.LLM_API_KEY
        url  = model_url  or Config.SIMCORE_MONITOR_URL  or Config.LLM_BASE_URL
        name = model_name or Config.SIMCORE_MONITOR_MODEL or Config.LLM_MODEL_NAME
        if not key:
            raise ValueError("MonitorAgent: لا يوجد مفتاح نموذج. أضف LLM_API_KEY في .env")
        self.client = OpenAI(api_key=key, base_url=url)
        self.model  = name

    def monitor_once(self, source_url: str, source_name: str,
                     api_key: Optional[str] = None,
                     account_id: Optional[str] = None) -> Dict[str, Any]:
        fetch = SourceManager.fetch(source_url, api_key, account_id)
        if not fetch["success"]:
            logger.warning("monitor fetch failed %s: %s", source_url, fetch["error"])
            return {"has_signal": False, "error": fetch["error"]}
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.2, max_tokens=512,
                messages=[
                    {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                    {"role": "user",   "content": self.PROMPT.format(
                        domain=self.domain,
                        source_name=source_name,
                        data=fetch["content"][:8000])}])
            result = json.loads(resp.choices[0].message.content.strip())
            logger.info("monitor signal=%s severity=%s from %s",
                        result.get("has_signal"), result.get("severity"), source_name)
            return result
        except json.JSONDecodeError as e:
            logger.error("monitor JSON parse error: %s", e)
            return {"has_signal": False, "error": f"JSON parse error: {e}"}
        except Exception as e:
            logger.error("monitor error: %s", e)
            return {"has_signal": False, "error": str(e)}
