"""
MemoryAgent — يدير الذاكرة تلقائياً بعد كل دورة
يستبدل background_review اليدوي بوكيل ذكي
"""
from __future__ import annotations
import json
import logging
import threading
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from memory.core.memory_manager import MemoryManager

logger = logging.getLogger("simcore.memory_agent")


class MemoryAgent(BaseAgent):
    """
    يعمل في daemon thread بعد كل دورة.
    يقرر: هل يحفظ؟ في أي سياق؟ بأي وزن؟
    يحذف الضعيف عبر prune_weak.
    """

    REVIEW_PROMPT = """\
راجع هذه المحادثة وقرر ما يستحق الحفظ في الذاكرة الدائمة.

المحادثة:
{conversation}

الذاكرة الحالية (ملخص):
{current_memory}

أجب بـ JSON فقط:
{{
  "should_save": true/false,
  "entries": [
    {{
      "content": "ما يُحفظ",
      "context": "general|trading|academic|technical",
      "weight": 0.1-2.0,
      "write_level": "auto|confirm|permanent"
    }}
  ],
  "should_prune": true/false,
  "prune_threshold": 0.1
}}"""

    def __init__(self, system_config, memory_manager: MemoryManager):
        super().__init__(
            config=type('cfg', (), {
                'agent_id': 'memory',
                'role': 'memory',
                'domain': 'general',
                'model_key': None,
                'model_url': None,
                'model_name': None,
                'activity': 'background'
            })(),
            system_config=system_config
        )
        self.memory_manager = memory_manager

    def review_async(self, messages: List[Dict], session_id: str = "") -> None:
        """استدعه بعد كل دورة — يعمل في خيط منفصل"""
        t = threading.Thread(
            target=self._review,
            args=(messages, session_id),
            daemon=True
        )
        t.start()

    def _review(self, messages: List[Dict], session_id: str) -> None:
        try:
            conversation = "\n".join(
                f"{m['role'].upper()}: {str(m.get('content',''))[:300]}"
                for m in messages[-6:]  # آخر 6 رسائل فقط
            )
            snapshot = self.memory_manager.build_system_prompt()[:500]

            raw = self.think([
                {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                {"role": "user",   "content": self.REVIEW_PROMPT.format(
                    conversation=conversation,
                    current_memory=snapshot
                )}
            ], temperature=0.2)

            result = json.loads(raw.strip())

            if result.get("should_save"):
                for entry in result.get("entries", []):
                    self.memory_manager.handle_tool_call(
                        "memory_add",
                        {
                            "content":     entry.get("content", ""),
                            "context":     entry.get("context", "general"),
                            "weight":      float(entry.get("weight", 1.0)),
                            "write_level": entry.get("write_level", "auto"),
                        }
                    )
                    logger.info("MemoryAgent saved: %s", entry.get("content","")[:60])

            if result.get("should_prune"):
                self.memory_manager.handle_tool_call(
                    "memory_prune",
                    {"threshold": result.get("prune_threshold", 0.1)}
                )
                logger.info("MemoryAgent pruned weak memories")

        except json.JSONDecodeError as e:
            logger.warning("MemoryAgent JSON error: %s", e)
        except Exception as e:
            logger.warning("MemoryAgent review failed: %s", e)
