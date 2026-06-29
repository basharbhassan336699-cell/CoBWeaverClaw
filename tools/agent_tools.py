"""
Agent Tools — أدوات تنفيذ خارجية يستطيع الوكيل استدعاؤها فعلياً.

  • web_search    : بحث في الويب (DuckDuckGo، بلا مفتاح)
  • fetch_url     : جلب محتوى صفحة وتلخيص نصّها
  • send_telegram : إرسال رسالة عبر بوت تيليجرام المُعدّ
  • current_datetime : التاريخ والوقت الحالي

تُعرَّف بصيغة OpenAI function-calling ويُنفّذها model_router عبر حلقة الأدوات.
كل الأدوات تتعامل مع الأخطاء بلطف وتُعيد نصّاً وصفياً (لا ترفع استثناء).
"""
import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

CONFIG_DIR = os.path.expanduser("~/.cobweaverclaw")


def _load_env():
    """يحمّل مفاتيح .env من المجلد الآمن إلى البيئة."""
    env_path = os.path.join(CONFIG_DIR, ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _load_config() -> dict:
    for p in [os.path.join(CONFIG_DIR, "config.yaml"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")]:
        if os.path.exists(p):
            try:
                import yaml
                return yaml.safe_load(open(p, encoding="utf-8")) or {}
            except Exception:
                return {}
    return {}


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ── tool implementations ─────────────────────────────────────
def web_search(query: str) -> str:
    """بحث ويب عبر DuckDuckGo (إجابة فورية + نتائج مختصرة)."""
    if not query:
        return "لا يوجد استعلام بحث."
    out = []
    try:
        u = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": "1", "no_redirect": "1"})
        with urllib.request.urlopen(u, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        if d.get("AbstractText"):
            out.append(d["AbstractText"])
        for t in (d.get("RelatedTopics") or [])[:5]:
            if isinstance(t, dict) and t.get("Text"):
                out.append("• " + t["Text"])
    except Exception:
        pass
    if not out:
        # احتياط: نسخة lite النصّية
        try:
            u = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = _strip_html(r.read().decode("utf-8", "ignore"))
            return txt[:1500] if txt else "لم أجد نتائج."
        except Exception as e:
            return f"تعذّر البحث: {str(e)[:80]}"
    return "\n".join(out)[:2000]


def fetch_url(url: str) -> str:
    """يجلب صفحة ويب ويُعيد نصّها (بلا وسوم)."""
    if not url:
        return "لا يوجد رابط."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (CoBWeaverClaw)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(600000).decode("utf-8", "ignore")
        text = _strip_html(raw)
        return text[:3000] if text else "الصفحة فارغة أو غير نصّية."
    except Exception as e:
        return f"تعذّر جلب الرابط: {str(e)[:100]}"


def send_telegram(message: str, chat_id: str = None) -> str:
    """يرسل رسالة عبر بوت تيليجرام المُعدّ إلى صاحب الحساب."""
    _load_env()
    cfg = _load_config()
    tg = cfg.get("interfaces", {}).get("telegram", {})
    token = (os.environ.get("TELEGRAM_BOT_TOKEN", "") or tg.get("token", "")
             or cfg.get("channels", {}).get("telegram", {}).get("token", ""))
    chat = (chat_id or tg.get("owner_chat_id", "")
            or cfg.get("channels", {}).get("telegram", {}).get("owner_chat_id", ""))
    if not token:
        return "لا يوجد توكين تيليجرام مضبوط. اضبطه عبر: python main.py setup --channel"
    if not chat:
        return ("لا يوجد owner_chat_id. أرسل /start لبوتك ثم اضبط chat_id "
                "عبر: python main.py setup --channel")
    try:
        payload = json.dumps({"chat_id": chat, "text": message}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
              data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = json.loads(r.read()).get("ok")
        return "✅ أُرسلت الرسالة عبر تيليجرام." if ok else "تعذّر الإرسال (رد غير ناجح)."
    except Exception as e:
        return f"تعذّر إرسال تيليجرام: {str(e)[:100]}"


def current_datetime(_: str = "") -> str:
    """التاريخ والوقت الحاليان."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S") + f" (يوم {now.strftime('%A')})"


# ── OpenAI-style schema + dispatcher ─────────────────────────
TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "ابحث في الويب عن معلومة حديثة أو غير معروفة. استخدمها لأي سؤال يحتاج بيانات حالية.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "نص البحث"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "اجلب محتوى صفحة ويب من رابط معيّن واقرأ نصّها.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "الرابط الكامل"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "send_telegram",
        "description": "أرسل رسالة نصّية إلى المستخدم عبر بوت تيليجرام الخاص به.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string", "description": "نص الرسالة"}}, "required": ["message"]}}},
    {"type": "function", "function": {
        "name": "current_datetime",
        "description": "احصل على التاريخ والوقت الحاليين.",
        "parameters": {"type": "object", "properties": {}}}},
]

_DISPATCH = {
    "web_search": lambda a: web_search(a.get("query", "")),
    "fetch_url": lambda a: fetch_url(a.get("url", "")),
    "send_telegram": lambda a: send_telegram(a.get("message", ""), a.get("chat_id")),
    "current_datetime": lambda a: current_datetime(),
}


def execute(name: str, args: dict) -> str:
    """ينفّذ أداة باسمها ويُعيد نصّ النتيجة."""
    fn = _DISPATCH.get(name)
    if not fn:
        return f"أداة غير معروفة: {name}"
    try:
        return str(fn(args or {}))
    except Exception as e:
        return f"خطأ في تنفيذ {name}: {str(e)[:100]}"
