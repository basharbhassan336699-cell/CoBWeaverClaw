"""
SimCore — الوكيل الأساسي
كل وكيل يرث منه ويأخذ مفتاح نموذجه الخاص أو يرث من النظام
"""
import json
import os
import urllib.request
from typing import Optional, List, Dict, Any
from ..config import AgentConfig, SimCoreConfig


def _system_inherited_runtime():
    """يرث مفتاح/رابط/اسم النموذج من نظام CoBWeaverClaw (أول مزوّد مفعّل).

    يجعل SimCore يعمل فوراً بلا إعداد منفصل — "None = يرث من النظام".
    """
    try:
        from brain.model_router import ModelRouter
        for prov, (url, env, style) in ModelRouter.PROVIDERS.items():
            if style != "openai" or not env:
                continue
            key = os.environ.get(env, "")
            if key:
                model = ModelRouter.DEFAULT_MODELS.get(prov, "")
                return key, url, model
    except Exception:
        pass
    return None, None, None


class BaseAgent:

    def __init__(self, config: AgentConfig, system_config: SimCoreConfig):
        self.config        = config
        self.system_config = system_config
        self._client = None
        self._runtime: Optional[tuple] = None   # (key, url, name) بعد الحسم

    def _resolve_runtime(self) -> tuple:
        """مفتاح الوكيل الخاص — أو المفتاح العام — أو وراثة من نظام CoBWeaverClaw."""
        if self._runtime:
            return self._runtime
        key  = self.config.model_key  or self.system_config.global_model_key
        url  = self.config.model_url  or self.system_config.global_model_url
        name = self.config.model_name or self.system_config.global_model_name
        if not key:
            skey, surl, sname = _system_inherited_runtime()
            key  = key  or skey
            url  = url  or surl
            name = name or sname
        if not key:
            raise ValueError(f"الوكيل {self.config.agent_id}: لا يوجد مفتاح نموذج")
        self._runtime = (key, url, name)
        return self._runtime

    @property
    def client(self):
        """عميل OpenAI إن كانت المكتبة مثبّتة — وإلا None ويُستخدم مسار urllib."""
        if self._client is None:
            key, url, _ = self._resolve_runtime()
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=key, base_url=url)
            except ImportError:
                self._client = None
        return self._client

    @property
    def model_name(self) -> str:
        try:
            _, _, name = self._resolve_runtime()
        except ValueError:
            name = None
        return (self.config.model_name or self.system_config.global_model_name
                or name or "gpt-4o-mini")

    def think(self, messages: List[Dict], temperature: float = 0.5) -> str:
        """استدعاء النموذج بمفتاح هذا الوكيل فقط"""
        client = self.client
        if client is not None:
            resp = client.chat.completions.create(
                model       = self.model_name,
                messages    = messages,
                temperature = temperature,
                max_tokens  = 2048,
            )
            return resp.choices[0].message.content or ""
        # مسار urllib — نفس OpenAI chat/completions بلا تبعيّات (Termux)
        key, url, _ = self._resolve_runtime()
        base = (url or "https://api.openai.com/v1").rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        payload = json.dumps({
            "model": self.model_name, "messages": messages,
            "temperature": temperature, "max_tokens": 2048,
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"].get("content") or ""
