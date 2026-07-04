"""
SimCore — OracleAgent (مركز التحكم)
يجمع نتائج كل الوكلاء ويصدر قراراً نهائياً واحداً مع تغذية راجعة
"""
import json, time, logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
from ..config import Config

logger    = logging.getLogger("simcore.oracle")
DECISIONS = Path.home() / ".cobweaverclaw" / "simcore" / "decisions.jsonl"


class OracleAgent:
    PROMPT = """\
أنت مركز القرار النهائي لنظام متخصص في: {domain}.

نتائج وكيل المراقبة (منصات وAPIs):
{monitor}

نتائج وكيل التتبع (مواقع ويب):
{tracker}

بناءً على كل ما سبق، أصدر قراراً نهائياً واحداً واضحاً ومحدداً.

أجب بـ JSON فقط بدون أي نص إضافي:
{{"decision":"buy|sell|wait|alert|monitor|recommend|no_action","confidence":0.85,"reasoning":"شرح مختصر للقرار","action":"ما يجب فعله الآن بالتحديد","risks":["خطر محدد 1","خطر محدد 2"]}}"""

    def __init__(self, domain: str,
                 model_key: Optional[str] = None,
                 model_url: Optional[str] = None,
                 model_name: Optional[str] = None):
        self.domain = domain
        key  = model_key  or Config.SIMCORE_ORACLE_KEY  or Config.LLM_API_KEY
        url  = model_url  or Config.SIMCORE_ORACLE_URL  or Config.LLM_BASE_URL
        name = model_name or Config.SIMCORE_ORACLE_MODEL or Config.LLM_MODEL_NAME
        if not key:
            raise ValueError("OracleAgent: لا يوجد مفتاح نموذج. أضف LLM_API_KEY في .env")
        self.client = OpenAI(api_key=key, base_url=url)
        self.model  = name

    def decide(self, monitor_results: List[Dict],
               tracker_results: List[Dict]) -> Dict[str, Any]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.2, max_tokens=1024,
                messages=[
                    {"role": "system", "content": "أجب بـ JSON فقط بدون أي نص إضافي."},
                    {"role": "user",   "content": self.PROMPT.format(
                        domain  = self.domain,
                        monitor = json.dumps(monitor_results, ensure_ascii=False, indent=2),
                        tracker = json.dumps(tracker_results, ensure_ascii=False, indent=2))}])
            d = json.loads(resp.choices[0].message.content.strip())
            d["ts"] = int(time.time())
            self._save(d, monitor_results, tracker_results)
            logger.info("oracle decision=%s confidence=%.2f", d.get("decision"), d.get("confidence",0))
            return d
        except json.JSONDecodeError as e:
            logger.error("oracle JSON error: %s", e)
            return {"decision":"error","reasoning":f"JSON parse error: {e}",
                    "confidence":0.0,"ts":int(time.time())}
        except Exception as e:
            logger.error("oracle error: %s", e)
            return {"decision":"error","reasoning":str(e),
                    "confidence":0.0,"ts":int(time.time())}

    def _save(self, decision: Dict, monitor: List, tracker: List) -> None:
        try:
            DECISIONS.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": decision["ts"], "domain": self.domain,
                "decision": decision, "monitor": monitor,
                "tracker": tracker, "outcome": None
            }
            with DECISIONS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("oracle save failed: %s", e)

    def feedback(self, ts: int, outcome: str) -> None:
        if not DECISIONS.exists(): return
        try:
            lines   = DECISIONS.read_text(encoding="utf-8").splitlines()
            updated = []
            for line in lines:
                try:
                    e = json.loads(line)
                    if e["ts"] == ts:
                        e["outcome"] = outcome
                    updated.append(json.dumps(e, ensure_ascii=False))
                except Exception:
                    updated.append(line)
            DECISIONS.write_text("\n".join(updated) + "\n", encoding="utf-8")
            logger.info("oracle feedback saved ts=%d outcome=%s", ts, outcome)
        except Exception as e:
            logger.warning("oracle feedback failed: %s", e)
