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
_UA = ("Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")


def _ddg_html(query: str) -> list:
    """نتائج بحث فعلية من DuckDuckGo HTML (عناوين + روابط + مقتطف)."""
    for host in ("https://html.duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"):
        try:
            data = urllib.parse.urlencode({"q": query}).encode()
            req = urllib.request.Request(host, data=data,
                  headers={"User-Agent": _UA, "Accept-Language": "ar,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode("utf-8", "ignore")
        except Exception:
            continue
        results = []
        for m in re.finditer(r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            url = m.group(1)
            um = re.search(r'uddg=([^&]+)', url)
            if um:
                url = urllib.parse.unquote(um.group(1))
            title = _strip_html(m.group(2))
            if title and url.startswith("http"):
                results.append((title, url))
            if len(results) >= 6:
                break
        if not results:  # نسخة lite: روابط عادية
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S):
                t = _strip_html(m.group(2))
                if t and "duckduckgo" not in m.group(1):
                    results.append((t, m.group(1)))
                if len(results) >= 6:
                    break
        if results:
            return results
    return []


def _wikipedia(query: str) -> str:
    """ملخّص من ويكيبيديا (عربي ثم إنجليزي)."""
    for lang in ("ar", "en"):
        try:
            u = (f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "list": "search", "srsearch": query,
                 "format": "json", "srlimit": "1"}))
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": _UA}), timeout=12) as r:
                d = json.loads(r.read())
            hits = d.get("query", {}).get("search", [])
            if not hits:
                continue
            title = hits[0]["title"]
            su = (f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "prop": "extracts", "exintro": "1", "explaintext": "1",
                 "titles": title, "format": "json"}))
            with urllib.request.urlopen(urllib.request.Request(su, headers={"User-Agent": _UA}), timeout=12) as r:
                d = json.loads(r.read())
            pages = d.get("query", {}).get("pages", {})
            for p in pages.values():
                ex = (p.get("extract") or "").strip()
                if ex:
                    return f"{title} (ويكيبيديا):\n{ex[:1200]}\nhttps://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}"
        except Exception:
            continue
    return ""


def web_search(query: str) -> str:
    """بحث ويب فعلي: نتائج DuckDuckGo + ملخّص ويكيبيديا (بلا مفتاح)."""
    if not query:
        return "لا يوجد استعلام بحث."
    parts = []
    results = _ddg_html(query)
    if results:
        parts.append("نتائج البحث:\n" + "\n".join(
            f"{i+1}. {t}\n   {u}" for i, (t, u) in enumerate(results[:6])))
    wiki = _wikipedia(query)
    if wiki:
        parts.append(wiki)
    if not parts:
        return ("تعذّر جلب نتائج البحث فعلياً (قد تكون الشبكة محجوبة). "
                "لا تختلق معلومات — أخبر المستخدم بصراحة أنّ البحث لم ينجح.")
    return "\n\n".join(parts)[:2600]


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


def youtube_search(query: str) -> str:
    """يبحث في يوتيوب ويُعيد عناوين الفيديوهات مع روابطها."""
    if not query:
        return "لا يوجد استعلام."
    try:
        u = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query})
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ar,en"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "ignore")
        seen, out = set(), []
        for m in re.finditer(r'"videoId":"([\w-]{11})".*?"text":"([^"]{3,120})"', html):
            vid, title = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            out.append(f"- {title}\n  https://www.youtube.com/watch?v={vid}")
            if len(out) >= 8:
                break
        return "نتائج يوتيوب لـ «{}»:\n".format(query) + "\n".join(out) if out else "لم أجد نتائج يوتيوب."
    except Exception as e:
        return f"تعذّر البحث في يوتيوب: {str(e)[:100]}"


def device_report(_: str = "") -> str:
    """تقرير بحالة الجهاز: النظام، المعالج، الذاكرة، القرص، البطارية (إن توفّرت)."""
    import platform as _plat, shutil, multiprocessing
    lines = []
    try:
        lines.append(f"النظام: {_plat.system()} {_plat.release()} ({_plat.machine()})")
    except Exception:
        pass
    try:
        lines.append(f"المعالجات: {multiprocessing.cpu_count()}")
    except Exception:
        pass
    try:  # الذاكرة من /proc/meminfo (Linux/Termux)
        mem = {}
        for ln in open("/proc/meminfo"):
            k, v = ln.split(":", 1)
            mem[k.strip()] = v.strip()
        total = int(mem.get("MemTotal", "0 kB").split()[0]) // 1024
        avail = int(mem.get("MemAvailable", "0 kB").split()[0]) // 1024
        lines.append(f"الذاكرة: {avail}MB متاح من {total}MB")
    except Exception:
        pass
    try:
        du = shutil.disk_usage(os.path.expanduser("~"))
        lines.append(f"التخزين: {du.free // (1024**3)}GB حر من {du.total // (1024**3)}GB")
    except Exception:
        pass
    try:  # البطارية عبر termux-api إن توفّر
        import subprocess
        bat = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=6)
        if bat.returncode == 0 and bat.stdout.strip():
            d = json.loads(bat.stdout)
            lines.append(f"البطارية: {d.get('percentage','?')}% ({d.get('status','?')})")
    except Exception:
        pass
    try:
        lines.append(f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception:
        pass
    return "📟 تقرير الجهاز:\n" + "\n".join(f"• {l}" for l in lines) if lines else "تعذّر جمع بيانات الجهاز."


def run_command(command: str) -> str:
    """ينفّذ أمراً في طرفية الجهاز ويُعيد المخرجات (للمالك على جهازه)."""
    if not command:
        return "لا يوجد أمر."
    import subprocess
    try:
        p = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
        out = out.strip() or f"(نُفّذ — رمز الخروج {p.returncode})"
        return out[:3000]
    except subprocess.TimeoutExpired:
        return "انتهت مهلة الأمر (30s)."
    except Exception as e:
        return f"تعذّر تنفيذ الأمر: {str(e)[:120]}"


def open_url(target: str) -> str:
    """يفتح رابطاً أو تطبيقاً على الجهاز (termux-open-url / xdg-open)."""
    if not target:
        return "لا يوجد هدف."
    import subprocess, shutil
    for opener in ("termux-open-url", "xdg-open", "open"):
        if shutil.which(opener):
            try:
                subprocess.Popen([opener, target],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"✅ جارٍ فتح: {target}"
            except Exception:
                continue
    return f"تعذّر العثور على أداة فتح. الرابط: {target}"


# روابط عميقة تفتح التطبيق مباشرة عند نتيجة بحث/شاشة
_APP_DEEPLINK = {
    "youtube":   "https://www.youtube.com/results?search_query={q}",
    "maps":      "https://www.google.com/maps/search/{q}",
    "google":    "https://www.google.com/search?q={q}",
    "twitter":   "https://twitter.com/search?q={q}",
    "x":         "https://twitter.com/search?q={q}",
    "play":      "https://play.google.com/store/search?q={q}",
    "browser":   "https://www.google.com/search?q={q}",
}


def open_app(app: str, query: str = "") -> str:
    """
    يفتح تطبيقاً على الجهاز، ويفتحه مباشرةً عند نتيجة بحث إن أمكن
    (مثل يوتيوب/الخرائط/المتجر). app: اسم التطبيق، query: نص البحث داخله.
    """
    app = (app or "").strip().lower()
    q = urllib.parse.quote(query or "")
    if app in _APP_DEEPLINK:
        url = _APP_DEEPLINK[app].format(q=q) if query else _APP_DEEPLINK[app].split("?")[0]
        res = open_url(url)
        if query and "✅" in res:
            return f"✅ فتحت {app} على نتائج البحث عن «{query}». ({url})"
        return res
    # تطبيق آخر: حاول فتحه عبر intent (Termux)
    import subprocess, shutil
    if shutil.which("am"):
        try:
            subprocess.Popen(["am", "start", "-a", "android.intent.action.MAIN",
                              "-c", "android.intent.category.LAUNCHER", app],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"✅ محاولة فتح التطبيق: {app}"
        except Exception:
            pass
    return (f"لا أعرف رابطاً مباشراً لتطبيق «{app}». الأشهر مدعومة: "
            "youtube, maps, google, twitter, play.")


# ── memory & settings access (يقرأ/يعدّل ملفاته إن طُلب) ──────
def _memdb():
    import sqlite3
    p = os.path.expanduser("~/.cobweaverclaw/memory.db")
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "user_id TEXT, key TEXT, value TEXT, created TEXT DEFAULT (datetime('now')),"
                "UNIQUE(user_id,key))")
    return con


def get_memory(_: str = "") -> str:
    """يقرأ ما هو مخزّن في ذاكرة الوكيل (الحقائق/التفضيلات)."""
    try:
        rows = _memdb().execute("SELECT key, value FROM facts ORDER BY id DESC LIMIT 60").fetchall()
        return "🧠 الذاكرة:\n" + "\n".join(f"- {r['key']}: {r['value']}" for r in rows) if rows else "الذاكرة فارغة."
    except Exception as e:
        return f"تعذّر قراءة الذاكرة: {str(e)[:100]}"


def set_memory_fact(key: str, value: str) -> str:
    """يضيف/يضبط معلومة في ذاكرة الوكيل الدائمة."""
    if not key:
        return "لا يوجد مفتاح."
    try:
        con = _memdb()
        con.execute("INSERT OR REPLACE INTO facts (user_id, key, value) VALUES ('core',?,?)", (key, value))
        con.commit()
        return f"✅ حُفظت في الذاكرة: {key} = {value}"
    except Exception as e:
        return f"تعذّر الحفظ: {str(e)[:100]}"


def delete_memory_fact(key: str) -> str:
    """يحذف معلومة من ذاكرة الوكيل."""
    try:
        con = _memdb()
        n = con.execute("DELETE FROM facts WHERE key=?", (key,)).rowcount
        con.commit()
        return f"✅ حُذف: {key}" if n else f"لم أجد: {key}"
    except Exception as e:
        return f"تعذّر الحذف: {str(e)[:100]}"


def update_setting(key: str, value: str) -> str:
    """يضبط إعداداً في config (مثل الاسم/الأسلوب/اللغة/التخصّص/حجم الذاكرة)."""
    try:
        import yaml
        p = os.path.join(CONFIG_DIR, "config.yaml")
        cfg = yaml.safe_load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        cfg = cfg or {}
        if key in ("memory_size",):
            try: value = int(value)
            except Exception: pass
        cfg.setdefault("agent", {})[key] = value
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return f"✅ ضُبط الإعداد {key} = {value}"
    except Exception as e:
        return f"تعذّر ضبط الإعداد: {str(e)[:100]}"


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
    {"type": "function", "function": {
        "name": "youtube_search",
        "description": "ابحث في يوتيوب عن فيديوهات وأعِد عناوينها وروابطها.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "كلمات البحث"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "device_report",
        "description": "احصل على تقرير بحالة الجهاز: النظام، المعالج، الذاكرة، القرص، البطارية.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "نفّذ أمراً في طرفية جهاز المستخدم واقرأ مخرجاته (لفحص الجهاز أو تشغيل أدوات).",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "الأمر الصدفي"}}, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "open_url",
        "description": "افتح رابطاً على جهاز المستخدم.",
        "parameters": {"type": "object", "properties": {
            "target": {"type": "string", "description": "الرابط"}}, "required": ["target"]}}},
    {"type": "function", "function": {
        "name": "open_app",
        "description": "افتح تطبيقاً على الجهاز وابحث داخله مباشرةً (youtube/maps/google/twitter/play أو اسم تطبيق).",
        "parameters": {"type": "object", "properties": {
            "app": {"type": "string", "description": "اسم التطبيق، مثل youtube"},
            "query": {"type": "string", "description": "نص البحث داخل التطبيق (اختياري)"}},
            "required": ["app"]}}},
    {"type": "function", "function": {
        "name": "get_memory",
        "description": "اقرأ ما هو مخزّن في ذاكرة الوكيل (الحقائق والتفضيلات والإعدادات المحفوظة).",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "set_memory_fact",
        "description": "أضِف أو اضبط معلومة في ذاكرة الوكيل الدائمة.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {
        "name": "delete_memory_fact",
        "description": "احذف معلومة من ذاكرة الوكيل بالمفتاح.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string"}}, "required": ["key"]}}},
    {"type": "function", "function": {
        "name": "update_setting",
        "description": "اضبط إعداداً للوكيل: name/style/language/specialization/memory_size/mission_anchor.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}}},
]

_DISPATCH = {
    "web_search": lambda a: web_search(a.get("query", "")),
    "fetch_url": lambda a: fetch_url(a.get("url", "")),
    "send_telegram": lambda a: send_telegram(a.get("message", ""), a.get("chat_id")),
    "current_datetime": lambda a: current_datetime(),
    "youtube_search": lambda a: youtube_search(a.get("query", "")),
    "device_report": lambda a: device_report(),
    "run_command": lambda a: run_command(a.get("command", "")),
    "open_url": lambda a: open_url(a.get("target", "")),
    "open_app": lambda a: open_app(a.get("app", ""), a.get("query", "")),
    "get_memory": lambda a: get_memory(),
    "set_memory_fact": lambda a: set_memory_fact(a.get("key", ""), a.get("value", "")),
    "delete_memory_fact": lambda a: delete_memory_fact(a.get("key", "")),
    "update_setting": lambda a: update_setting(a.get("key", ""), a.get("value", "")),
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
