#!/usr/bin/env python3
"""
CoBWeaverClaw — Setup Wizard (الترتيب الكامل 1→12)
معالج تثبيت تفاعلي بأسلوب احترافي، تنقّل بالأسهم والمسافة وBack.

الترتيب:
 1. Security disclaimer       تنبيه أمني
 2. Setup mode                QuickStart / Manual
 3. Config handling           عند وجود إعداد سابق
 4. Model / auth provider     اختيار المزود (بحث)
 5. Model definition          تعريف النموذج
 6. Channel + خطوات فرعية     قناة الاتصال (Telegram → توكين/رابط/Back ...)
 7. Search provider           محرك البحث + المتصفح الداخلي
 8. Skills status             حالة المهارات
 9. Hooks                     multi-select
10. Run agent                 Terminal / Browser / لاحقاً
11. Control Gateway           رابط البوابة + التوكين (منفذنا الخاص)
12. لوحة التحكم               ملخص نهائي

python setup_wizard.py
"""
import os
import sys
import getpass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import tui
from tui import select, multi_select, BACK, CANCEL, R, B, G, Y, C, RD, O, DIM, GRN

# منفذ بوابتنا الخاص (مميز لنا)
GATEWAY_PORT = 7878


def clear():
    os.system("clear" if os.name != "nt" else "cls")

# لغة المعالج (تُحدَّد في أول شاشة). تؤثّر على النصوص اللاحقة.
LANG = "ar"
ORANGE = "\033[38;5;208m"   # برتقالي ANSI لاسم المالك

def T(ar, en):
    """يُعيد النص حسب اللغة المختارة."""
    return ar if LANG == "ar" else en

def banner():
    clear()
    print(f"{O}{B}")
    print("   ██████╗██████╗ ██╗    ██╗")
    print("  ██╔════╝██╔══██╗██║    ██║    CoBWeaverClaw")
    print("  ██║     ██████╔╝██║ █╗ ██║    🕷️  Setup Wizard")
    print("  ██║     ██╔══██╗██║███╗██║")
    print("  ╚██████╗██████╔╝╚███╔███╔╝")
    print("   ╚═════╝╚═════╝  ╚══╝╚══╝")
    print(f"{R}")
    # اسم المالك — برتقالي عريض، أسفل الشعار مباشرة وفوق سطر الإصدار
    print(f"  {ORANGE}{B}Bashar Hassan{R}")
    print(f"  {DIM}Setup v0.1.0{R}\n")

def diamond(title):
    print(f"\n{G}◇{R}  {O}{B}{title}{R}")

def ask(prompt, default="", secret=False):
    disp = f"  {prompt}" + (f" [{C}{default}{R}]" if default else "") + ": "
    try:
        v = getpass.getpass(disp) if secret else input(disp).strip()
        return v or default
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Y}تم الإلغاء.{R}")
        sys.exit(0)

def ask_yn(prompt, default=True):
    sel = select(prompt, [("نعم", ""), ("لا", "")], allow_back=False)
    if sel == CANCEL:
        return default
    return sel == 0

def ok(m):   print(f"  {G}✅ {m}{R}")
def warn(m): print(f"  {Y}⚠️  {m}{R}")
def info(m): print(f"  {C}ℹ️  {m}{R}")
def err(m):  print(f"  {RD}❌ {m}{R}")

CONFIG_DIR = os.path.expanduser("~/.cobweaverclaw")

def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return CONFIG_DIR

def load_config():
    # يُحمّل من المجلد الآمن أولاً (لا يُحذف مع git)، ثم المحلي كاحتياط
    for p in [os.path.join(CONFIG_DIR, "config.yaml"), "config.yaml"]:
        if os.path.exists(p):
            try:
                import yaml
                with open(p) as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
    return {}

def save_config(cfg):
    # يُحفظ في المجلد الآمن ~/.cobweaverclaw (يبقى رغم git clone/pull)
    _ensure_config_dir()
    try:
        import yaml
        path = os.path.join(CONFIG_DIR, "config.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        warn(f"تعذّر حفظ config.yaml: {e}")

def save_env(env_vars):
    # يُحفظ في المجلد الآمن ~/.cobweaverclaw/.env (يبقى رغم git)
    from pathlib import Path
    _ensure_config_dir()
    env_path = Path(CONFIG_DIR) / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                existing[line.split("=")[0]] = line
    for k, v in env_vars.items():
        existing[k] = f"{k}={v}"
    env_path.write_text("\n".join(existing.values()) + "\n")
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass

# ════════════════════════════════════════════════════════════
# البيانات
# ════════════════════════════════════════════════════════════

# (الاسم, id, النموذج الافتراضي, متغير البيئة, رابط المفتاح, مجاني؟, قائمة النماذج)
PROVIDERS = [
    ("Anthropic",     "anthropic",  "claude-sonnet-4-6",        "ANTHROPIC_API_KEY",  "console.anthropic.com/settings/keys", False,
        ["claude-sonnet-4-6","claude-opus-4-6","claude-haiku-4-5"]),
    ("OpenAI",        "openai",     "gpt-4o-mini",              "OPENAI_API_KEY",     "platform.openai.com/api-keys", False,
        ["gpt-4o","gpt-4o-mini","gpt-4-turbo","o1-mini"]),
    ("Google Gemini", "gemini",     "gemini-2.0-flash",         "GEMINI_API_KEY",     "aistudio.google.com/app/apikey", True,
        ["gemini-2.0-flash","gemini-1.5-pro","gemini-1.5-flash"]),
    ("Groq",          "groq",       "llama-3.3-70b-versatile",  "GROQ_API_KEY",       "console.groq.com/keys", True,
        ["llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768"]),
    ("DeepSeek",      "deepseek",   "deepseek-chat",            "DEEPSEEK_API_KEY",   "platform.deepseek.com/api_keys", False,
        ["deepseek-chat","deepseek-reasoner"]),
    ("OpenRouter",    "openrouter", "meta-llama/llama-3.3-70b", "OPENROUTER_API_KEY", "openrouter.ai/keys", True,
        ["meta-llama/llama-3.3-70b","qwen/qwen-2.5-72b","mistralai/mistral-7b"]),
    ("Mistral AI",    "mistral",    "mistral-small-latest",     "MISTRAL_API_KEY",    "console.mistral.ai/api-keys", False,
        ["mistral-large-latest","mistral-small-latest","open-mistral-7b"]),
    ("xAI (Grok)",    "xai",        "grok-2",                   "XAI_API_KEY",        "console.x.ai", False,
        ["grok-2","grok-2-mini"]),
    ("Z.AI (GLM)",    "zai",        "glm-4.6",                  "ZAI_API_KEY",        "z.ai", False,
        ["glm-4.6","glm-4.5","glm-4.5-air","glm-4-flash"]),
    ("Ollama (محلي)", "ollama",     "mistral",                  "",                   "ollama.ai", True,
        ["mistral","llama3.3","qwen2.5","gemma3","phi4"]),
]

# القنوات + نوع الإعداد الفرعي
CHANNELS = [
    ("Terminal (الطرفية)", "terminal", "تشغيل مباشر — موصى به للبداية"),
    ("Telegram",           "telegram", "بوت Telegram للتحكم عن بُعد"),
    ("Discord",            "discord",  "بوت Discord"),
    ("Slack",              "slack",    "Slack Socket Mode"),
    ("WhatsApp",           "whatsapp", "WhatsApp Business API"),
    ("Signal",             "signal",   "Signal عبر signal-cli"),
]

SEARCH_PROVIDERS = [
    ("CoBWeaver Browser الداخلي", "internal",   "متصفح الوكيل المدمج — جلب وبحث وتلخيص (موصى به)"),
    ("DuckDuckGo",                "duckduckgo", "بحث ويب مجاني بلا مفتاح"),
    ("Brave Search",             "brave",      "يحتاج مفتاح API"),
    ("Tavily",                   "tavily",     "بحث مخصص للذكاء الاصطناعي — يحتاج مفتاح"),
    ("تخطّي الآن",                "skip",       "إعداده لاحقاً"),
]

HOOKS = [
    ("session-memory",      "حفظ سياق الجلسة في الذاكرة عند /new أو /reset"),
    ("command-logger",      "تسجيل كل الأوامر المنفّذة"),
    ("boot-notify",         "إشعار عند بدء تشغيل الوكيل"),
    ("update-notify",       "إشعار عند توفّر تحديث جديد"),
    ("backup-reminder",     "تذكير دوري بأخذ نسخة احتياطية"),
]

def test_key(provider, key):
    import urllib.request, urllib.error
    try:
        if provider == "anthropic":
            req = urllib.request.Request("https://api.anthropic.com/v1/models",
                  headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
        elif provider in ("openai","groq","deepseek","openrouter","mistral","xai"):
            urls = {"openai":"https://api.openai.com/v1/models","groq":"https://api.groq.com/openai/v1/models",
                    "deepseek":"https://api.deepseek.com/models","openrouter":"https://openrouter.ai/api/v1/models",
                    "mistral":"https://api.mistral.ai/v1/models","xai":"https://api.x.ai/v1/models"}
            req = urllib.request.Request(urls[provider], headers={"Authorization": f"Bearer {key}"})
        elif provider == "gemini":
            urllib.request.urlopen(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=8)
            return True
        else:
            return None
        urllib.request.urlopen(req, timeout=8)
        return True
    except urllib.error.HTTPError as e:
        return e.code != 401
    except Exception:
        return None

def test_telegram(token):
    import urllib.request, json
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=8) as r:
            d = json.loads(r.read())
        return d.get("result") if d.get("ok") else None
    except Exception:
        return None

# ════════════════════════════════════════════════════════════
# الخطوات (كل خطوة تُرجع: "next" | BACK)
# ════════════════════════════════════════════════════════════

def step0_language(cfg):
    """أول شاشة على الإطلاق — اختيار اللغة (بالإنجليزية فقط قبل أي اختيار)."""
    global LANG
    banner()
    print(f"  {O}{B}┌─────────────────────────────────────────┐{R}")
    print(f"  {O}{B}│  Choose your language / اختر لغتك       │{R}")
    print(f"  {O}{B}│  1. العربية                             │{R}")
    print(f"  {O}{B}│  2. English                             │{R}")
    print(f"  {O}{B}└─────────────────────────────────────────┘{R}")
    sel = select("Choose your language / اختر لغتك:",
                 [("العربية", "Arabic"), ("English", "الإنجليزية")], allow_back=False)
    LANG = "en" if sel == 1 else "ar"     # CANCEL/default → عربية
    cfg.setdefault("agent", {})["language"] = LANG
    cfg.setdefault("interface", {})["language"] = LANG
    return "next"


def step1_security(cfg):
    diamond("١/١٢ — Security disclaimer · تنبيه أمني")
    print(f"""
  {DIM}CoBWeaverClaw وكيل شخصي بحدّ ثقة واحد (أنت).
  • يقرأ الملفات وينفّذ أوامر إذا فُعّلت الأدوات.
  • prompt خبيث قد يخدعه — لا تُدخِل ما لا تثق به.
  • البوابة محمية بتوكين عشوائي، localhost افتراضياً.
  • أبقِ المفاتيح الحساسة بعيدة عن متناول الوكيل.{R}""")
    if not ask_yn("أفهم أن هذا وكيل شخصي. أتابع؟", default=True):
        print(f"  {Y}تم الإيقاف.{R}")
        sys.exit(0)
    return "next"

def step2_mode(cfg):
    diamond("٢/١٢ — Setup mode · نمط الإعداد")
    sel = select("اختر نمط الإعداد:", [
        ("QuickStart (موصى به)", "إعداد محلي سريع — يمكن تغييره لاحقاً"),
        ("Manual setup",         "إعداد يدوي مفصّل لكل خيار"),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    cfg["_setup_mode"] = "quick" if sel == 0 else "manual"
    return "next"

def step3_config_handling(cfg):
    # تظهر فقط إن وُجد إعداد سابق (في المجلد الآمن فقط)
    existing = bool(cfg.get("brain", {}).get("primary")
                    or os.path.exists(os.path.join(CONFIG_DIR, ".env")))
    if not existing:
        return "next"
    diamond("٣/١٢ — Config handling · معالجة الإعداد السابق")
    info("تم اكتشاف إعداد سابق")
    sel = select("ماذا تريد أن نفعل به؟", [
        ("الإبقاء على القيم الحالية", "لا تغيّر شيئاً"),
        ("مراجعة وتحديث",            "أعد المرور على الخطوات"),
        ("إعادة الضبط قبل الإعداد",  "امسح القديم وابدأ نظيفاً"),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    if sel == 2:
        # إعادة ضبط — تحذف من المجلد الآمن (لا مجلد المشروع)
        for f in [".env", "config.yaml"]:
            p = os.path.join(CONFIG_DIR, f)
            if os.path.exists(p):
                os.remove(p)
        cfg.clear()
        ok("تمت إعادة الضبط")
    cfg["_config_handling"] = ["keep","review","reset"][sel]
    return "next"

def step4_provider(cfg):
    diamond("٤/١٢ — Model / auth provider · مزوّد النماذج")
    opts = []
    for name, pid, model, env, url, free, models in PROVIDERS:
        badge = f"{G}مجاني{R}" if free else f"{Y}مدفوع{R}"
        opts.append((f"{name}", f"{badge} · {model}"))
    sel = select("اختر مزوّد النماذج:", opts, allow_back=True,
                 hint="يمكن إضافة أكثر من مزود — كرّر الخطوة لاحقاً")
    if sel == BACK:
        return BACK
    cfg["_chosen_provider"] = sel
    return "next"

def step5_model_def(cfg):
    idx = cfg.get("_chosen_provider", 0)
    name, pid, default_model, env, url, free, models = PROVIDERS[idx]
    diamond(f"٥/١٢ — Model definition · تعريف نموذج {name}")

    if pid == "ollama":
        if ask_yn("هل Ollama مثبّت محلياً؟", default=False):
            opts = [(m, "") for m in models] + [("✏️ كتابة يدوياً", "أدخل اسم النموذج")]
            sel = select("اختر النموذج المحلي:", opts, allow_back=True)
            if sel == BACK: return BACK
            model = ask("اسم النموذج", default=default_model) if sel == len(opts)-1 else models[sel]
            cfg.setdefault("brain", {})["local"] = f"ollama/{model}"
            ok(f"Ollama → {model}")
        return "next"

    # إدخال المفتاح
    print(f"  {DIM}المفتاح من: {C}{url}{R}")
    key = ask(f"مفتاح {name} API", secret=True)
    if not key:
        warn(f"تُخطّي {name}")
        return "next"
    print(f"  {Y}⟳ اختبار المفتاح...{R}")
    res = test_key(pid, key)
    if res is True:
        ok("المفتاح صحيح ويعمل")
    elif res is False:
        err("المفتاح مرفوض (401)")
        sel = select("ماذا تفعل؟", [("إعادة الإدخال",""),("حفظه رغم ذلك",""),("تخطّي",""),], allow_back=True)
        if sel == BACK or sel == 3: return BACK
        if sel == 0: return step5_model_def(cfg)
        if sel == 2: return "next"
    else:
        warn("تعذّر التحقق — سيُحفظ")

    # تعريف النموذج: اختيار أو يدوي
    opts = [(m, "") for m in models] + [("✏️ كتابة التعريف يدوياً", "أدخل اسم نموذج مخصّص")]
    sel = select(f"اختر نموذج {name} أو عرّفه يدوياً:", opts, allow_back=True)
    if sel == BACK:
        return BACK
    model = ask("اسم النموذج", default=default_model) if sel == len(opts)-1 else models[sel]

    # تعيين الدور
    role_opts = [
        ("primary — التحليل العميق", ""),
        ("fast — الردود السريعة", ""),
        ("coding — البرمجة", ""),
        ("arabic — العربية", ""),
        ("fallback — احتياطي", ""),
    ]
    rsel = select("ما دور هذا النموذج؟", role_opts, allow_back=True)
    if rsel == BACK:
        return BACK
    role = ["primary","fast","coding","arabic","fallback"][rsel]

    cfg.setdefault("brain", {})[role] = f"{pid}/{model}"
    if env:
        save_env({env: key})
    ok(f"{name} → {model} ({role})")

    # إضافة مزود آخر؟
    if ask_yn("إضافة مزوّد آخر؟", default=False):
        r = step4_provider(cfg)
        if r == BACK:
            return "next"  # رجع من اختيار المزود → نكمل
        return step5_model_def(cfg)
    return "next"

def step6_channel(cfg):
    diamond("٦/١٢ — Channel · قناة الاتصال")
    sel = select("كيف تريد التحكم بالوكيل؟", CHANNELS, allow_back=True)
    if sel == BACK:
        return BACK
    name, cid, desc = CHANNELS[sel]

    # ── الخطوة الفرعية لكل قناة ──
    cfg.setdefault("interfaces", {})

    if cid == "terminal":
        cfg["interfaces"]["cli"] = {"enabled": True}
        ok("Terminal — تشغيل مباشر في الطرفية")
        return "next"

    if cid == "telegram":
        sub = select("Telegram — طريقة الربط:", [
            ("إدخال توكين البوت", "من @BotFather (الأضمن)"),
            ("عرض رابط البوت",    "للوصول السريع بعد الإدخال"),
        ], allow_back=True)
        if sub == BACK:
            return step6_channel(cfg)  # رجوع لاختيار قناة أخرى
        print(f"\n  {DIM}خطوات: افتح @BotFather → /newbot → انسخ التوكين{R}")
        token = ask("BOT_TOKEN", secret=True)
        if not token:
            warn("تُخطّي Telegram")
            return step6_channel(cfg)
        print(f"  {Y}⟳ اختبار البوت...{R}")
        bot = test_telegram(token)
        if bot:
            ok(f"البوت يعمل: @{bot.get('username','')}")
            if sub == 1:
                info(f"رابط البوت: https://t.me/{bot.get('username','')}")
        else:
            err("توكين غير صحيح")
            retry = select("ماذا تفعل؟", [("إعادة الإدخال",""),("تخطّي Telegram","")], allow_back=True)
            if retry == BACK: return step6_channel(cfg)
            if retry == 0: return step6_channel(cfg)
            return "next"
        chat = ask("chat_id (اختياري — Enter للتخطّي)", default="")
        cfg["interfaces"]["telegram"] = {"enabled": True, "token": token, "owner_chat_id": chat}
        save_env({"TELEGRAM_BOT_TOKEN": token})
        ok("Telegram مُعدّ")
        return "next"

    if cid == "discord":
        sub = select("Discord — طريقة الربط:", [
            ("إدخال Bot Token", "من Discord Developer Portal"),
            ("إرشادات الإعداد", "كيف تُنشئ بوت Discord"),
        ], allow_back=True)
        if sub == BACK:
            return step6_channel(cfg)
        if sub == 1:
            info("أنشئ تطبيقاً في discord.com/developers → Bot → Token")
        token = ask("Discord Bot Token", secret=True)
        if token:
            cfg["interfaces"]["discord"] = {"enabled": True, "token": token}
            save_env({"DISCORD_BOT_TOKEN": token})
            ok("Discord مُعدّ")
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "slack":
        token = ask("Slack Bot Token (xoxb-...)", secret=True)
        if token:
            app_token = ask("Slack App Token (xapp-...)", secret=True)
            cfg["interfaces"]["slack"] = {"enabled": True}
            save_env({"SLACK_BOT_TOKEN": token, "SLACK_APP_TOKEN": app_token})
            ok("Slack مُعدّ")
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "whatsapp":
        info("WhatsApp يحتاج حساب Business API (Meta)")
        token = ask("WhatsApp API Token", secret=True)
        phone = ask("Phone Number ID", default="")
        if token:
            cfg["interfaces"]["whatsapp"] = {"enabled": True, "phone_id": phone}
            save_env({"WHATSAPP_TOKEN": token})
            ok("WhatsApp مُعدّ")
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "signal":
        info("Signal يحتاج signal-cli مثبّتاً ورقماً مسجّلاً")
        number = ask("رقم Signal (+...)", default="")
        if number:
            cfg["interfaces"]["signal"] = {"enabled": True, "number": number}
            ok("Signal مُعدّ")
        else:
            return step6_channel(cfg)
        return "next"

    return "next"

def step7_search(cfg):
    diamond("٧/١٢ — Search provider · محرك البحث")
    sel = select("اختر محرك البحث/المتصفح للوكيل:", SEARCH_PROVIDERS, allow_back=True)
    if sel == BACK:
        return BACK
    name, sid, desc = SEARCH_PROVIDERS[sel]
    cfg.setdefault("browser", {})
    cfg["browser"]["provider"] = sid

    if sid == "internal":
        cfg["browser"]["enabled"] = True
        cfg["browser"]["mode"] = "both"
        ok("المتصفح الداخلي CoBWeaver Browser مُفعّل")
        info("يجلب الصفحات، يبحث، ويُلخّص. (لا يُشغّل JavaScript)")
    elif sid == "duckduckgo":
        cfg["browser"]["enabled"] = True
        ok("DuckDuckGo (بلا مفتاح)")
    elif sid == "brave":
        key = ask("مفتاح Brave Search API", secret=True)
        if key: save_env({"BRAVE_API_KEY": key})
        ok("Brave Search")
    elif sid == "tavily":
        key = ask("مفتاح Tavily API", secret=True)
        if key: save_env({"TAVILY_API_KEY": key})
        ok("Tavily")
    else:
        info("تخطّيت محرك البحث")
    return "next"

def step8_skills(cfg):
    diamond("٨/١٢ — Skills status · حالة المهارات")
    # فحص المهارات المتاحة فعلياً
    skills_dir = os.path.join(BASE_DIR, "skills")
    eligible = 0
    if os.path.isdir(skills_dir):
        import glob
        eligible = len([f for f in glob.glob(os.path.join(skills_dir,"*.py"))
                        if not os.path.basename(f).startswith("_")
                        and os.path.basename(f)[:-3] not in ("base","factory","evolver")])
    print(f"""
  {DIM}المهارات المتاحة:  {G}{eligible}{R}{DIM}
  متطلبات ناقصة:    0
  غير مدعومة هنا:   0{R}""")
    if ask_yn("تفعيل المهارات الآن؟", default=True):
        cfg.setdefault("skills", {})["enabled"] = True
        ok("المهارات مُفعّلة")
    else:
        cfg.setdefault("skills", {})["enabled"] = False
        info("يمكن تفعيلها لاحقاً")
    return "next"

def step9_hooks(cfg):
    diamond("٩/١٢ — Hooks · الأتمتة")
    print(f"  {DIM}الـ Hooks تُؤتمت إجراءات عند تنفيذ أوامر معيّنة.{R}")
    sel = multi_select("اختر الـ Hooks (Space للتحديد):", HOOKS, allow_back=True)
    if sel == BACK:
        return BACK
    if sel == CANCEL:
        sel = []
    enabled = [HOOKS[i][0] for i in sel]
    cfg.setdefault("hooks", {})["enabled"] = enabled
    if enabled:
        ok(f"فُعّلت: {', '.join(enabled)}")
    else:
        info("لم تُفعّل أي hooks")
    return "next"

def step10_run(cfg):
    diamond("١٠/١٢ — Run agent · تشغيل الوكيل")
    sel = select("كيف تريد تشغيل الوكيل؟", [
        ("في الطرفية (موصى به)", "يبدأ مباشرة بعد الإعداد"),
        ("عبر المتصفح",          "عبر بوابة التحكم"),
        ("لاحقاً",               "أشغّله بنفسي بأمر python main.py"),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    cfg["_run_mode"] = ["terminal","browser","later"][sel]
    return "next"

def step11_gateway(cfg):
    diamond("١١/١٢ — Control Gateway · بوابة التحكم")
    print(f"  {DIM}بوابة تحكم عبر المتصفح، محمية بتوكين عشوائي.{R}")
    if not ask_yn("تفعيل بوابة التحكم؟", default=True):
        cfg.setdefault("gateway", {})["enabled"] = False
        info("تخطّيت البوابة")
        return "next"

    scope = select("نطاق الوصول:", [
        ("localhost فقط", "أأمن — أنت فقط على هذا الجهاز"),
        ("الشبكة المحلية", "من أجهزة أخرى على شبكتك (التوكين إجباري)"),
    ], allow_back=True)
    if scope == BACK:
        return BACK

    cfg.setdefault("gateway", {})
    cfg["gateway"]["enabled"] = True
    cfg["gateway"]["host"] = "127.0.0.1" if scope == 0 else "0.0.0.0"
    cfg["gateway"]["port"] = GATEWAY_PORT

    try:
        from gateway_auth import GatewayAuth
        auth = GatewayAuth()
        token = auth.get_or_create_token()
        host = cfg["gateway"]["host"]
        disp = host if host != "0.0.0.0" else "<عنوان-جهازك>"
        print(f"\n  {G}✅ البوابة جاهزة{R}")
        print(f"  {B}رابط بوابة التحكم (خاص بنظامنا):{R}")
        print(f"  {C}http://{disp}:{GATEWAY_PORT}/#token={token}{R}")
        if host == "0.0.0.0":
            warn("مفتوحة على الشبكة — التوكين إجباري")
        else:
            ok("localhost فقط — آمن")
        print(f"\n  {DIM}لفتحها لاحقاً: {C}python main.py gateway{R}")
        print(f"  {DIM}لعرض الرابط:  {C}python main.py gateway --url{R}")
    except Exception as e:
        warn(f"تعذّر توليد التوكين: {e}")
    return "next"

def step12_finish(cfg):
    diamond("١٢/١٢ — اكتمل الإعداد! 🎉")
    # تنظيف المفاتيح المؤقتة
    run_mode_tmp = cfg.get("_run_mode","")
    for k in ["_chosen_provider","_setup_mode","_config_handling","_run_mode"]:
        cfg.pop(k, None)
    save_config(cfg)
    cfg["_run_mode_saved"] = run_mode_tmp

    # إعداد الحساب
    try:
        from account_manager import AccountManager
        am = AccountManager()
        acc = am.get_or_create_account()
        account_id = acc["account_id"]
    except Exception:
        account_id = "—"

    print(f"\n  {G}{B}✅ تم حفظ كل الإعدادات{R}\n")
    brain = cfg.get("brain", {})
    if brain.get("primary"): print(f"  🤖 أساسي:   {G}{brain['primary']}{R}")
    if brain.get("fast"):    print(f"  ⚡ سريع:    {G}{brain['fast']}{R}")
    if brain.get("local"):   print(f"  💻 محلي:    {G}{brain['local']}{R}")
    if cfg.get("browser", {}).get("provider"):
        print(f"  🌐 المتصفح: {G}{cfg['browser']['provider']}{R}")
    chans = [k for k,v in cfg.get("interfaces",{}).items() if v.get("enabled")]
    if chans: print(f"  📡 القنوات: {G}{', '.join(chans)}{R}")
    if cfg.get("gateway",{}).get("enabled"):
        print(f"  🔒 البوابة: {G}{cfg['gateway']['host']}:{GATEWAY_PORT}{R}")
    print(f"  🆔 الحساب:  {G}{account_id}{R}")

    # تشغيل تلقائي حسب اختيار المستخدم في خطوة 10
    run_mode = cfg.get("_run_mode_saved", "")
    if cfg.get("gateway",{}).get("enabled"):
        print(f"\n  {Y}━━━ لفتح بوابة التحكم ━━━{R}")
        print(f"  شغّل الأمر التالي في الطرفية:")
        print(f"  {G}{B}python main.py gateway{R}")
        print(f"  ثم افتح الرابط في المتصفح.")
        print(f"  {DIM}(البوابة تحتاج أن تبقى تعمل — لا تغلق الطرفية){R}")

    print(f"""
  {B}أوامر البدء:{R}
  {C}python main.py{R}              تشغيل CLI
  {C}python main.py gateway{R}      فتح بوابة التحكم
  {C}python main.py gateway --url{R} عرض رابط البوابة
  {C}python main.py account{R}      عرض/استعادة الحساب
  {C}python main.py backup{R}       نسخة احتياطية
  {C}python main.py restore <f>{R}  استعادة نسخة
  {C}python main.py restart{R}      إعادة التشغيل
  {C}python main.py doctor --fix{R} تشخيص وإصلاح

  {O}{B}🕷️  CoBWeaverClaw جاهز!{R}
""")

# ════════════════════════════════════════════════════════════
# المُشغّل — يدير التنقّل بين الخطوات مع دعم Back
# ════════════════════════════════════════════════════════════

STEPS = [
    step1_security,
    step2_mode,
    step3_config_handling,
    step4_provider,
    step5_model_def,
    step6_channel,
    step7_search,
    step8_skills,
    step9_hooks,
    step10_run,
    step11_gateway,
    step12_finish,
]

def run_wizard():
    cfg = load_config()
    step0_language(cfg)          # أول شاشة على الإطلاق — اختيار اللغة
    i = 0
    while i < len(STEPS):
        result = STEPS[i](cfg)
        if result == BACK:
            i = max(0, i - 1)  # رجوع خطوة
        else:
            i += 1
    return cfg

def main():
    # أوضاع جزئية
    if "--models" in sys.argv:
        cfg = load_config(); step4_provider(cfg); step5_model_def(cfg); save_config(cfg); return
    if "--channel" in sys.argv:
        cfg = load_config(); step6_channel(cfg); save_config(cfg); return
    if "--gateway" in sys.argv:
        cfg = load_config(); step11_gateway(cfg); save_config(cfg); return
    run_wizard()

if __name__ == "__main__":
    main()
