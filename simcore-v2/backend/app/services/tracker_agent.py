"""
SimCore — وكيل التتبع
يتتبع أي موقع ويب يدرجه المستخدم ويستخرج محتوى ذا صلة بالتوجه
"""
import json, logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from .source_manager import SourceManager
from ..config import Config

logger = logging.getLogger("simcore.tracker")


class TrackerAgent:
    PROMPT = """\
أنت وكيل تتبع متخصص في مجال: {domain}.
استخرج من المحتوى التالي ما هو ذو صلة بتوجهك.

المصدر: {source_name}
المحتوى:
{content}

أجب بـ JSON فقط بدون أي نص إضافي:
{{"relevant":true,"extracted":[{{"point":"نقطة مهمة","sentiment":"positive|negative|neutral","weight":0.8}}],"summary":"ملخص موجز"}}"""

    def __init__(self, domain: str,
                 model_key: Optional[str] = None,
                 model_url: Optional[str] = None,
                 model_name: Optional[str] = None):
        self.domain = domain
        key  = model_key  or Config.SIMCORE_TRACKER_KEY  or Config.LLM_API_KEY
        url  = model_url  or Config.SIMCORE_TRACKER_URL  or Config.LLM_BASE_URL
        name = model_name or Config.SIMCORE_TRACKER_MODEL or Config.LLM_MODEL_NAME
        if not key:
            raise ValueError("TrackerAgent: لا يوجد مفتاح نموذج. أضف LLM_API_KEY في .env")
        self.client = OpenAI(api_key=key, base_url=url)
        self.model  = name

    def track(self, sources: List[Dict]) -> List[Dict[str, Any]]:
        results = []
        for src in sources:
            fetch = SourceManager.fetch(
                src["url"], src.get("api_key"), src.get("account_id"))
            if not fetch["success"]:
                logger.warning("tracker fetch failed %s: %s", src.get("name"), fetch["error"])
                continue
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, temperature=0.3, max_tokens=1024,
                    messages=[
                        {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                        {"role": "user",   "content": self.PROMPT.format(
                            domain=self.domain,
                            source_name=src.get("name", src["url"]),
                            content=fetch["content"][:8000])}])
                r = json.loads(resp.choices[0].message.content.strip())
                if r.get("relevant"):
                    r["source"] = src.get("name", src["url"])
                    results.append(r)
                    logger.info("tracker: relevant content from %s", src.get("name"))
            except json.JSONDecodeError as e:
                logger.error("tracker JSON error %s: %s", src.get("name"), e)
            except Exception as e:
                logger.warning("tracker error %s: %s", src.get("name"), e)
        return results
