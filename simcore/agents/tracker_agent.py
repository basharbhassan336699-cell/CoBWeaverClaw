"""
SimCore — وكيل التتبع
يتابع المواقع المدرجة ويستخرج محتوى ذا صلة بالتوجه.
"""
import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..source_manager import SourceManager
from ..config import SourceConfig

logger = logging.getLogger("simcore.tracker")


class TrackerAgent(BaseAgent):
    """
    دوره: تتبع مواقع ومصادر ويب.
    يستخرج: أخبار، تقارير، آراء حسب التوجه.
    يُرسل: ملخص منظم لـ OracleAgent.
    """

    TRACKER_PROMPT = """\
أنت وكيل تتبع متخصص في {domain}.
استخرج من المحتوى التالي ما هو ذو صلة بتوجهك:
المصدر: {source_name}
التوجه: {domain}
المحتوى:
{content}

أجب بـ JSON:
{{
  "relevant": true/false,
  "extracted": [
    {{"point": "نقطة مهمة", "sentiment": "positive|negative|neutral", "weight": 0.0-1.0}}
  ],
  "summary": "ملخص موجز"
}}
"""

    def track(self, sources: List[SourceConfig]) -> List[Dict[str, Any]]:
        """تتبع قائمة مصادر وإعادة نتائج منظمة"""
        import json
        results = []
        domain  = self.config.domain or self.system_config.domain

        for source in sources:
            fetch = SourceManager.fetch_content(source)
            if not fetch["success"]:
                continue
            prompt = self.TRACKER_PROMPT.format(
                domain      = domain,
                source_name = source.name,
                content     = fetch["content"][:8000],
            )
            try:
                raw    = self.think([
                    {"role": "system", "content": "أجب بـ JSON فقط."},
                    {"role": "user",   "content": prompt},
                ], temperature=0.3)
                result = json.loads(raw)
                result["source"] = source.name
                if result.get("relevant"):
                    results.append(result)
            except Exception as e:
                logger.warning("tracker error %s: %s", source.name, e)

        return results
