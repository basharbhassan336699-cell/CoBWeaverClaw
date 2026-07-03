"""
SimCore — OracleAgent (مركز التحكم)
يستقبل نتائج كل الوكلاء، يرجّحها، ويصدر قراراً نهائياً واحداً.
يحفظ سجل القرارات لتحسين الدقة مع الوقت.
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger("simcore.oracle")

DECISIONS_FILE = Path.home() / ".cobweaverclaw" / "simcore" / "decisions.jsonl"


class OracleAgent(BaseAgent):
    """
    مركز التحكم النهائي.
    يجمع: نتائج MonitorAgent + TrackerAgent.
    يُصدر: قرار واحد موجّه للمستخدم.
    يتعلم: يرفع وزن الوكلاء الأكثر دقة مع الوقت.
    """

    ORACLE_PROMPT = """\
أنت مركز القرار النهائي لنظام {domain}.
لديك نتائج من وكلاء متخصصين:

نتائج المراقبة (منصات):
{monitor_results}

نتائج التتبع (مواقع):
{tracker_results}

بناءً على كل ما سبق، أصدر قراراً نهائياً واحداً:
- إذا domain=trading: هل تشتري؟ تبيع؟ تنتظر؟
- إذا domain=general: ما التوصية الرئيسية؟
- لأي domain آخر: ما الإجراء المقترح؟

أجب بـ JSON:
{{
  "decision": "buy|sell|wait|alert|monitor|recommend",
  "confidence": 0.0-1.0,
  "reasoning": "شرح مختصر للقرار",
  "action": "ما يجب فعله الآن",
  "risks": ["خطر 1", "خطر 2"],
  "monitor_weight": 0.0-1.0,
  "tracker_weight": 0.0-1.0
}}
"""

    def decide(self,
               monitor_results: List[Dict],
               tracker_results: List[Dict]) -> Dict[str, Any]:
        """إصدار القرار النهائي"""
        domain = self.config.domain or self.system_config.domain

        prompt = self.ORACLE_PROMPT.format(
            domain          = domain,
            monitor_results = json.dumps(monitor_results, ensure_ascii=False, indent=2),
            tracker_results = json.dumps(tracker_results, ensure_ascii=False, indent=2),
        )

        try:
            raw      = self.think([
                {"role": "system", "content": "أجب بـ JSON فقط."},
                {"role": "user",   "content": prompt},
            ], temperature=0.2)
            decision = json.loads(raw)
            self._save_decision(decision, monitor_results, tracker_results)
            return decision
        except Exception as e:
            logger.error("oracle decision failed: %s", e)
            return {"decision": "error", "reasoning": str(e), "confidence": 0.0}

    def _save_decision(self, decision: Dict, monitor: List, tracker: List) -> None:
        """حفظ القرار للتغذية الراجعة"""
        DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts":       int(time.time()),
            "domain":   self.config.domain or self.system_config.domain,
            "decision": decision,
            "inputs":   {"monitor": monitor, "tracker": tracker},
            "outcome":  None,   # يُملأ لاحقاً عند التحقق
        }
        with DECISIONS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def feedback(self, decision_ts: int, actual_outcome: str) -> None:
        """تسجيل ما حدث فعلاً لتحسين الدقة"""
        if not DECISIONS_FILE.exists():
            return
        lines = DECISIONS_FILE.read_text(encoding="utf-8").splitlines()
        updated = []
        for line in lines:
            try:
                entry = json.loads(line)
                if entry["ts"] == decision_ts:
                    entry["outcome"] = actual_outcome
                updated.append(json.dumps(entry, ensure_ascii=False))
            except Exception:
                updated.append(line)
        DECISIONS_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")
