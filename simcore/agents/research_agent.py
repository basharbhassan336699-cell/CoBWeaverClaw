"""
ResearchAgent — يبحث في مصادر متعددة ويلخص لـ OracleAgent
يُستدعى عند طلب تحليل معمق
"""
from __future__ import annotations
import json
import logging
from typing import List, Dict, Any
from .base_agent import BaseAgent
from ..source_manager import SourceManager

logger = logging.getLogger("simcore.research_agent")


class ResearchAgent(BaseAgent):
    """
    يأخذ سؤالاً أو موضوعاً ويبحث في كل المصادر المتاحة.
    يُعيد ملخصاً منظماً لـ OracleAgent.
    """

    RESEARCH_PROMPT = """\
أنت باحث متخصص في مجال: {domain}.
الموضوع المطلوب بحثه: {query}

المحتوى المجموع من المصادر:
{content}

ابنِ تقريراً بحثياً منظماً.
أجب بـ JSON فقط:
{{
  "summary": "ملخص شامل",
  "key_points": ["نقطة 1", "نقطة 2"],
  "sentiment": "positive|negative|neutral|mixed",
  "confidence": 0.0-1.0,
  "sources_used": ["مصدر 1", "مصدر 2"],
  "recommendation": "ما يُقترح بناءً على البحث"
}}"""

    def research(self, query: str, sources: List[Dict],
                 domain: str = "general") -> Dict[str, Any]:
        """ابحث في المصادر وأعد تقريراً منظماً"""
        collected = []

        for src in sources:
            src = src if isinstance(src, dict) else {
                "url": getattr(src, "url", ""), "name": getattr(src, "name", ""),
                "api_key": getattr(src, "api_key", None),
                "account_id": getattr(src, "account_id", None),
            }
            fetch = SourceManager.fetch(
                src.get("url", ""),
                src.get("api_key"),
                src.get("secret"),
                src.get("account_id"),
                query
            )
            if fetch["success"] and fetch["content"].strip():
                collected.append({
                    "source":  src.get("name", src.get("url", "")),
                    "content": fetch["content"][:3000]
                })

        if not collected:
            return {
                "summary":      "لم يتم العثور على محتوى ذي صلة",
                "key_points":   [],
                "sentiment":    "neutral",
                "confidence":   0.0,
                "sources_used": [],
                "recommendation": "لا توصية — لا بيانات كافية"
            }

        content_text = "\n\n---\n\n".join(
            f"[{c['source']}]\n{c['content']}"
            for c in collected
        )

        try:
            raw = self.think([
                {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                {"role": "user",   "content": self.RESEARCH_PROMPT.format(
                    domain=domain,
                    query=query,
                    content=content_text[:12000]
                )}
            ], temperature=0.3)

            result = json.loads(raw.strip())
            result["sources_count"] = len(collected)
            return result

        except json.JSONDecodeError as e:
            logger.error("ResearchAgent JSON error: %s", e)
            return {"summary": "خطأ في معالجة النتائج",
                    "key_points": [], "sentiment": "neutral",
                    "confidence": 0.0, "sources_used": [],
                    "recommendation": "", "error": str(e)}
        except Exception as e:
            logger.error("ResearchAgent error: %s", e)
            return {"summary": str(e), "key_points": [],
                    "sentiment": "neutral", "confidence": 0.0,
                    "sources_used": [], "recommendation": ""}
