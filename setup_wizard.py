#!/usr/bin/env python3
"""
CoBWeaverClaw — Setup Wizard
واجهة إعداد تفاعلية شاملة عند أول تشغيل أو عند الطلب.

python setup_wizard.py
"""
import os
import sys
import json
import yaml
import urllib.request
import urllib.error
import getpass
import shutil
from pathlib import Path

# ── ألوان الطرفية ──────────────────────────────────────────
R  = "\033[0m"       # Reset
B  = "\033[1m"       # Bold
G  = "\033[32m"      # Green
Y  = "\033[33m"      # Yellow
C  = "\033[36m"      # Cyan
P  = "\033[35m"      # Purple
RD = "\033[31m"      # Red
W  = "\033[37m"      # White
BG = "\033[44m"      # Blue BG

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def header(title: str, step: int = 0, total: int = 0):
    clear()
    print(f"{B}{C}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   🕷️  CoBWeaverClaw — Setup Wizard           ║")
    if step and total:
        bar = "█" * step + "░" * (total - step)
        print(f"  ║   [{bar}] {step}/{total}                    ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"  {B}{W}{title}{R}")
    print()

def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    if default:
        display = f"{prompt} [{C}{default}{R}]: "
    else:
        display = f"{prompt}: "
    try:
        if secret:
            val = getpass.getpass(display)
        else:
            val = input(display).strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Y}تم الإلغاء{R}")
        sys.exit(0)

def ask_choice(prompt: str, choices: list, default: int = 1) -> int:
    print(f"  {B}{prompt}{R}")
    for i, (label, desc) in enumerate(choices, 1):
        marker = f"{G}►{R}" if i == default else " "
        print(f"  {marker} {B}{i}{R}. {label:<25} {W}{desc}{R}")
    print()
    while True:
        try:
            val = input(f"  اختر [{default}]: ").strip()
            if not val:
                return default
            n = int(val)
            if 1 <= n <= len(choices):
                return n
        except (ValueError, KeyboardInterrupt):
            pass

def ask_yn(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    try:
        val = input(f"  {prompt} [{d}]: ").strip().lower()
        if not val:
            return default
        return val in ("y", "yes", "نعم", "1")
    except (KeyboardInterrupt, EOFError):
        return default

def ok(msg: str):
    print(f"  {G}✅ {msg}{R}")

def warn(msg: str):
    print(f"  {Y}⚠️  {msg}{R}")

def err(msg: str):
    print(f"  {RD}❌ {msg}{R}")

def info(msg: str):
    print(f"  {C}ℹ️  {msg}{R}")

def test_api_key(provider: str, key: str) -> bool:
    """اختبار مفتاح API قبل الحفظ."""
    try:
        if provider == "anthropic":
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"}
            )
            urllib.request.urlopen(req, timeout=8)
            return True
        elif provider == "openai":
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            urllib.request.urlopen(req, timeout=8)
            return True
        elif provider == "groq":
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            urllib.request.urlopen(req, timeout=8)
            return True
        elif provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            urllib.request.urlopen(url, timeout=8)
            return True
        elif provider == "cohere":
            req = urllib.request.Request(
                "https://api.cohere.ai/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            urllib.request.urlopen(req, timeout=8)
            return True
    except urllib.error.HTTPError as e:
        return e.code != 401
    except Exception:
        return False
    return False

def test_telegram_bot(token: str) -> dict | None:
    """اختبار بوت Telegram."""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        if data.get("ok"):
            return data["result"]
    except Exception:
        pass
    return None

def get_telegram_chat_id(token: str) -> str | None:
    """جلب chat_id من آخر رسالة."""
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        if data.get("ok") and data["result"]:
            last = data["result"][-1]
            return str(last.get("message", {}).get("chat", {}).get("id", ""))
    except Exception:
        pass
    return None

def save_env(env_vars: dict):
    """حفظ المتغيرات في ملف .env."""
    env_path = Path(".env")
    lines = []
    if env_path.exists():
        with open(env_path) as f:
            existing = {l.split("=")[0]: l for l in f.readlines() if "=" in l}
    else:
        existing = {}
    existing.update({k: f"{k}={v}\n" for k, v in env_vars.items()})
    with open(env_path, "w") as f:
        f.writelines(existing.values())

def load_config() -> dict:
    for p in ["config.yaml", os.path.expanduser("~/.cobweaverclaw/config.yaml")]:
        if os.path.exists(p):
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}

def save_config(cfg: dict):
    path = "config.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# ============================================================
# الخطوات
# ============================================================

TOTAL_STEPS = 6

def step_welcome() -> str:
    """شاشة الترحيب واختيار اللغة."""
    header("مرحباً | Welcome", 0, TOTAL_STEPS)
    print(f"  {B}CoBWeaverClaw{R} — وكيل ذكاء اصطناعي مفتوح المصدر")
    print(f"  Open-Source AI Agent\n")
    print(f"  {Y}هذا المعالج سيساعدك على إعداد الوكيل خطوة بخطوة.{R}")
    print(f"  This wizard will help you configure the agent step by step.\n")

    choice = ask_choice("اختر لغة الواجهة | Choose interface language:", [
        ("العربية",  "Arabic"),
        ("English",  "English"),
    ], default=1)
    return "ar" if choice == 1 else "en"

AI_PROVIDERS = [
    {
        "id":       "anthropic",
        "name":     "Anthropic",
        "models":   ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"],
        "default":  "claude-sonnet-4-6",
        "role":     "التحليل العميق والمعقد",
        "url":      "https://console.anthropic.com/settings/keys",
        "format":   "sk-ant-api03-...",
        "desc":     "الأقوى في التحليل العميق — يُستخدم للمهام الصعبة",
        "free":     False,
        "priority": 1,
    },
    {
        "id":       "openai",
        "name":     "OpenAI",
        "models":   ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"],
        "default":  "gpt-4o-mini",
        "role":     "الكتابة والإبداع",
        "url":      "https://platform.openai.com/api-keys",
        "format":   "sk-proj-...",
        "desc":     "ممتاز للكتابة الإبداعية والبرمجة",
        "free":     False,
        "priority": 2,
    },
    {
        "id":       "groq",
        "name":     "Groq",
        "models":   ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "default":  "llama-3.3-70b-versatile",
        "role":     "الردود السريعة (150ms)",
        "url":      "https://console.groq.com/keys",
        "format":   "gsk_...",
        "desc":     "الأسرع في السوق — للردود اليومية السريعة",
        "free":     True,
        "priority": 3,
    },
    {
        "id":       "gemini",
        "name":     "Google Gemini",
        "models":   ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default":  "gemini-2.0-flash",
        "role":     "البحث ومعالجة الملفات",
        "url":      "https://aistudio.google.com/app/apikey",
        "format":   "AIza...",
        "desc":     "ممتاز للبحث وتحليل المستندات الكبيرة",
        "free":     True,
        "priority": 4,
    },
    {
        "id":       "cohere",
        "name":     "Cohere",
        "models":   ["command-r-plus", "command-r", "command"],
        "default":  "command-r-plus",
        "role":     "البحث والاسترجاع (RAG)",
        "url":      "https://dashboard.cohere.com/api-keys",
        "format":   "...",
        "desc":     "متخصص في RAG والبحث الدلالي",
        "free":     True,
        "priority": 5,
    },
    {
        "id":       "openrouter",
        "name":     "OpenRouter",
        "models":   ["meta-llama/llama-3.3-70b", "mistralai/mistral-7b", "qwen/qwen-2.5-72b"],
        "default":  "meta-llama/llama-3.3-70b",
        "role":     "بوابة موحدة لكل النماذج",
        "url":      "https://openrouter.ai/keys",
        "format":   "sk-or-...",
        "desc":     "بوابة واحدة لأكثر من 200 نموذج",
        "free":     True,
        "priority": 6,
    },
    {
        "id":       "mistral",
        "name":     "Mistral AI",
        "models":   ["mistral-large-latest", "mistral-small-latest", "open-mistral-7b"],
        "default":  "mistral-small-latest",
        "role":     "النماذج الأوروبية",
        "url":      "https://console.mistral.ai/api-keys",
        "format":   "...",
        "desc":     "نماذج أوروبية سريعة وخصوصية أفضل",
        "free":     False,
        "priority": 7,
    },
    {
        "id":       "ollama",
        "name":     "Ollama (محلي)",
        "models":   ["mistral", "llama3.3", "qwen2.5", "gemma3", "phi4"],
        "default":  "mistral",
        "role":     "يعمل بدون إنترنت",
        "url":      "https://ollama.ai",
        "format":   "لا يحتاج مفتاح",
        "desc":     "تشغيل محلي كامل بدون إنترنت أو تكلفة",
        "free":     True,
        "priority": 8,
    },
]

def step_ai_models(lang: str, cfg: dict) -> dict:
    """إعداد نماذج الذكاء الاصطناعي."""
    header("🤖 نماذج الذكاء الاصطناعي | AI Models", 2, TOTAL_STEPS)

    print(f"  {B}الشركات المتاحة:{R}\n")
    print(f"  {'#':<3} {'الشركة':<18} {'الدور':<25} {'مجاني':<8} {'النموذج الافتراضي'}")
    print(f"  {'─'*80}")
    for i, p in enumerate(AI_PROVIDERS, 1):
        free_badge = f"{G}✓ مجاني{R}" if p["free"] else f"{Y}مدفوع{R}"
        print(f"  {C}{i:<3}{R} {B}{p['name']:<18}{R} {p['role']:<25} {free_badge:<16} {W}{p['default']}{R}")

    print(f"\n  {Y}اختر الشركات التي تريد إضافة مفاتيحها (مثال: 1,3,4 أو all):{R}")
    print(f"  {W}اضغط Enter بدون إدخال لاختيار Anthropic + Groq فقط{R}\n")

    sel_input = ask("اختيارك", default="1,3").strip()

    if sel_input.lower() == "all":
        selected = list(range(len(AI_PROVIDERS)))
    else:
        try:
            selected = [int(x.strip())-1 for x in sel_input.split(",") if x.strip().isdigit()]
            selected = [i for i in selected if 0 <= i < len(AI_PROVIDERS)]
        except:
            selected = [0, 2]

    if not selected:
        selected = [0, 2]

    keys    = {}
    models  = {}
    roles   = {}

    for idx in selected:
        p = AI_PROVIDERS[idx]
        print(f"\n  {B}{C}━━━ {p['name']} ━━━{R}")
        print(f"  {W}{p['desc']}{R}")

        if p["id"] == "ollama":
            print(f"  {G}لا يحتاج مفتاح — يعمل محلياً{R}")
            print(f"  تثبيت: curl -sSL https://ollama.ai/install.sh | sh")
            use_ollama = ask_yn(f"هل Ollama مثبّت لديك؟", default=False)
            if use_ollama:
                print(f"  {W}النماذج المتاحة: {', '.join(p['models'])}{R}")
                model = ask(f"  النموذج", default=p["default"])
                models[p["id"]] = model
                keys[p["id"]]   = "local"
            continue

        print(f"  {W}احصل على مفتاحك من: {C}{p['url']}{R}")
        print(f"  {W}الصيغة: {p['format']}{R}")
        print(f"  {W}النماذج: {', '.join(p['models'][:3])}{R}\n")

        key = ask(f"  مفتاح {p['name']} API", secret=True)

        if not key:
            warn(f"تم تخطي {p['name']}")
            continue

        # اختبار المفتاح
        print(f"  {Y}⟳ جاري اختبار المفتاح...{R}", end="", flush=True)
        valid = test_api_key(p["id"], key)
        if valid:
            print(f"\r  {G}✅ المفتاح صحيح ويعمل!{R}         ")
        else:
            print(f"\r  {Y}⚠️  لم يتحقق (قد يعمل) — تم الحفظ{R}")

        # اختيار النموذج
        print(f"\n  {W}النماذج المتاحة:{R}")
        for mi, m in enumerate(p["models"], 1):
            mark = f"{G}★{R}" if m == p["default"] else " "
            print(f"  {mark} {mi}. {m}")

        m_choice = ask(f"  اختر النموذج", default=p["default"])
        if m_choice.isdigit() and 1 <= int(m_choice) <= len(p["models"]):
            m_choice = p["models"][int(m_choice)-1]

        # اختيار الدور
        print(f"\n  {W}الأدوار المتاحة:{R}")
        role_choices = [
            ("primary",  "للمهام العميقة والمعقدة"),
            ("fast",     "للردود السريعة اليومية"),
            ("coding",   "للبرمجة والكود"),
            ("arabic",   "للغة العربية تحديداً"),
            ("research", "للبحث والتحليل"),
            ("fallback", "احتياطي عند فشل الآخرين"),
        ]
        for ri, (role, rdesc) in enumerate(role_choices, 1):
            print(f"  {ri}. {role:<12} {W}{rdesc}{R}")

        r_choice = ask(f"  دور هذا النموذج", default="1")
        if r_choice.isdigit() and 1 <= int(r_choice) <= len(role_choices):
            role_name = role_choices[int(r_choice)-1][0]
        else:
            role_name = r_choice or "primary"

        keys[p["id"]]   = key
        models[p["id"]] = m_choice
        roles[p["id"]]  = role_name
        ok(f"{p['name']} — {m_choice} ({role_name})")

    # حفظ في config
    cfg.setdefault("brain", {})

    env_vars = {}
    for pid, key in keys.items():
        if key != "local":
            env_key = {
                "anthropic":  "ANTHROPIC_API_KEY",
                "openai":     "OPENAI_API_KEY",
                "groq":       "GROQ_API_KEY",
                "gemini":     "GEMINI_API_KEY",
                "cohere":     "COHERE_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "mistral":    "MISTRAL_API_KEY",
            }.get(pid)
            if env_key:
                env_vars[env_key] = key

    save_env(env_vars)

    # ربط الأدوار
    for pid, role in roles.items():
        cfg["brain"][role] = f"{pid}/{models.get(pid, '')}"

    # تعيين primary تلقائياً
    if "anthropic" in keys and "primary" not in roles.values():
        cfg["brain"]["primary"] = f"anthropic/{models.get('anthropic','claude-sonnet-4-6')}"
    if "groq" in keys and "fast" not in roles.values():
        cfg["brain"]["fast"] = f"groq/{models.get('groq','llama-3.3-70b-versatile')}"
    if "ollama" in keys:
        cfg["brain"]["local"] = f"ollama/{models.get('ollama','mistral')}"

    return cfg

def step_telegram(lang: str, cfg: dict) -> dict:
    """إعداد Telegram."""
    header("📱 قناة Telegram", 3, TOTAL_STEPS)

    print(f"  {B}إعداد بوت Telegram للتحكم بالوكيل{R}\n")
    print(f"  {W}خطوات الحصول على BOT_TOKEN:{R}")
    print(f"  {C}1.{R} افتح Telegram وابحث عن {B}@BotFather{R}")
    print(f"  {C}2.{R} أرسل {B}/newbot{R}")
    print(f"  {C}3.{R} اختر اسماً للبوت")
    print(f"  {C}4.{R} انسخ الـ Token المُعطى{R}\n")

    skip = ask_yn("هل تريد إعداد Telegram الآن؟", default=True)
    if not skip:
        warn("تم تخطي Telegram — يمكن إعداده لاحقاً بـ: python setup_wizard.py --telegram")
        return cfg

    bot_token = ask("  BOT_TOKEN", secret=True)
    if not bot_token:
        warn("تم تخطي Telegram")
        return cfg

    print(f"  {Y}⟳ اختبار البوت...{R}", end="", flush=True)
    bot_info = test_telegram_bot(bot_token)

    if bot_info:
        print(f"\r  {G}✅ البوت يعمل: @{bot_info.get('username','')}{R}       ")
    else:
        print(f"\r  {RD}❌ توكين غير صحيح{R}")
        retry = ask_yn("حاول مرة أخرى؟")
        if retry:
            return step_telegram(lang, cfg)
        return cfg

    # جلب chat_id
    print(f"\n  {Y}الآن أرسل أي رسالة للبوت @{bot_info.get('username','')} في Telegram{R}")
    input("  ثم اضغط Enter هنا للمتابعة...")

    chat_id = get_telegram_chat_id(bot_token)
    if chat_id:
        ok(f"chat_id: {chat_id}")
    else:
        chat_id = ask("  أدخل chat_id يدوياً (اختياري)", default="")

    # إشعارات المالك
    owner_notifications = ask_yn("تلقي إشعارات الأجهزة الجديدة والتحديثات؟", default=True)

    cfg.setdefault("interfaces", {})
    cfg["interfaces"]["telegram"] = {
        "enabled":         True,
        "token":           bot_token,
        "owner_chat_id":   chat_id,
        "notifications":   owner_notifications,
    }

    save_env({
        "TELEGRAM_BOT_TOKEN":  bot_token,
        "TELEGRAM_CHAT_ID":    chat_id or "",
    })

    ok("Telegram مُعدّ بنجاح!")
    return cfg

def step_specialization(lang: str, cfg: dict) -> dict:
    """اختيار تخصص الوكيل."""
    header("🎯 تخصص الوكيل | Specialization", 4, TOTAL_STEPS)

    print(f"  {B}اختر تخصص الوكيل الرئيسي:{R}\n")

    specs = [
        ("general",     "عام",        "يتعامل مع أي مهمة بدون قيود"),
        ("trading",     "تداول 📈",   "متخصص في تحليل السوق وإشارات التداول"),
        ("medicine",    "طب 🏥",      "متخصص في الطب والصحة والأدوية"),
        ("engineering", "هندسة 🏗️",   "متخصص في الهندسة والتصميم"),
        ("law",         "قانون ⚖️",   "متخصص في القانون والتشريعات"),
        ("education",   "تعليم 🎓",   "متخصص في التعليم والبحث العلمي"),
        ("programming", "برمجة 💻",   "متخصص في البرمجة والتطوير"),
        ("finance",     "مالية 💰",   "متخصص في المحاسبة والمالية"),
    ]

    for i, (sid, sname, sdesc) in enumerate(specs, 1):
        print(f"  {C}{i}{R}. {B}{sname:<20}{R} {W}{sdesc}{R}")

    print()
    choice = ask("  اختيارك", default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(specs):
        spec_id = specs[int(choice)-1][0]
        spec_name = specs[int(choice)-1][1]
    else:
        spec_id, spec_name = "general", "عام"

    cfg.setdefault("agent", {})
    cfg["agent"]["specialization"] = spec_id

    # إعدادات التخصص
    if spec_id == "trading":
        print(f"\n  {B}إعدادات التداول:{R}")
        exchange = ask_choice("منصة التداول:", [
            ("Binance",    "العملات الرقمية"),
            ("Bybit",      "العملات الرقمية"),
            ("MT5",        "فوركس وأسهم"),
            ("أخرى",       "منصة مخصصة"),
        ], default=1)
        exchanges = ["binance", "bybit", "mt5", "custom"]
        cfg.setdefault("trading", {})
        cfg["trading"]["exchange"] = exchanges[exchange-1]

        swarm = ask_yn("تفعيل محرك محاكاة السوق (Swarm Engine)؟", default=True)
        cfg.setdefault("swarm", {})
        cfg["swarm"]["enabled"] = swarm

    ok(f"التخصص: {spec_name}")
    return cfg

def step_advanced(lang: str, cfg: dict) -> dict:
    """إعدادات متقدمة."""
    header("⚙️ الإعدادات المتقدمة", 5, TOTAL_STEPS)

    adv = ask_yn("هل تريد تخصيص الإعدادات المتقدمة؟", default=False)
    if not adv:
        info("سيتم استخدام الإعدادات الافتراضية")
        return cfg

    # لغة الوكيل
    print(f"\n  {B}لغة الوكيل الافتراضية:{R}")
    lang_choice = ask_choice("", [
        ("auto",    "كشف تلقائي من رسالة المستخدم"),
        ("ar",      "العربية دائماً"),
        ("en",      "الإنجليزية دائماً"),
    ], default=1)
    cfg["agent"]["language"] = ["auto","ar","en"][lang_choice-1]

    # Heartbeat
    print(f"\n  {B}دورة المراقبة (Heartbeat):{R}")
    hb = ask_choice("كل كم يفحص الوكيل الحالة؟", [
        ("60s",    "كل دقيقة (جهاز قوي)"),
        ("300s",   "كل 5 دقائق (افتراضي)"),
        ("900s",   "كل 15 دقيقة (موفر للبطارية)"),
    ], default=2)
    cfg.setdefault("heartbeat", {})
    cfg["heartbeat"]["interval_seconds"] = [60, 300, 900][hb-1]

    # التحديثات
    notify_updates = ask_yn("\n  إشعار عند صدور تحديث جديد؟", default=True)
    cfg.setdefault("updates", {})
    cfg["updates"]["notify_on_update"] = notify_updates
    cfg["updates"]["auto_check"]       = True

    # التعلم الذاتي
    auto_learn = ask_yn("\n  تفعيل التعلم الذاتي الأسبوعي؟", default=True)
    cfg.setdefault("learning", {})
    cfg["learning"]["enabled"] = auto_learn

    return cfg

def step_finish(cfg: dict, lang: str):
    """الشاشة النهائية."""
    header("🎉 اكتمل الإعداد!", 6, TOTAL_STEPS)

    save_config(cfg)

    print(f"  {G}{B}✅ تم حفظ الإعدادات بنجاح!{R}\n")

    # ملخص
    print(f"  {B}ملخص الإعداد:{R}")
    brain = cfg.get("brain", {})
    if brain.get("primary"):
        print(f"  🤖 النموذج الرئيسي:  {G}{brain['primary']}{R}")
    if brain.get("fast"):
        print(f"  ⚡ النموذج السريع:   {G}{brain['fast']}{R}")
    if brain.get("local"):
        print(f"  💻 النموذج المحلي:   {G}{brain['local']}{R}")

    tg = cfg.get("interfaces", {}).get("telegram", {})
    if tg.get("enabled"):
        print(f"  📱 Telegram:         {G}مُعدّ ✅{R}")
    else:
        print(f"  📱 Telegram:         {Y}غير مُعدّ{R}")

    spec = cfg.get("agent", {}).get("specialization", "general")
    print(f"  🎯 التخصص:           {G}{spec}{R}")
    print()

    print(f"  {B}أوامر البدء:{R}")
    print(f"  {C}python main.py{R}              ← تشغيل CLI")
    print(f"  {C}python main.py doctor{R}       ← تشخيص")
    print(f"  {C}python main.py status{R}       ← الحالة")
    print()
    print(f"  {B}لإعادة الإعداد في أي وقت:{R}")
    print(f"  {C}python setup_wizard.py{R}")
    print()
    print(f"  {P}{'═'*50}{R}")
    print(f"  {B}{C}🕷️  CoBWeaverClaw — جاهز للعمل!{R}")
    print(f"  {P}{'═'*50}{R}\n")


# ============================================================
# Main
# ============================================================
def main():
    # فحص إذا كان هناك إعداد سابق
    cfg = load_config()
    existing = bool(cfg.get("brain") or cfg.get("interfaces",{}).get("telegram",{}).get("token"))

    if existing and "--force" not in sys.argv and "--reconfigure" not in sys.argv:
        clear()
        print(f"\n  {B}{C}🕷️  CoBWeaverClaw{R}\n")
        print(f"  {G}يوجد إعداد سابق.{R}")
        print(f"  لإعادة الإعداد الكامل: {C}python setup_wizard.py --force{R}")
        print(f"  لإعداد نموذج جديد:     {C}python setup_wizard.py --models{R}")
        print(f"  لإعداد Telegram:       {C}python setup_wizard.py --telegram{R}")
        print()
        redo = ask_yn("هل تريد إعادة الإعداد الآن؟", default=False)
        if not redo:
            sys.exit(0)

    # وضع إعداد محدد
    if "--models" in sys.argv:
        lang = "ar"
        cfg  = step_ai_models(lang, cfg)
        save_config(cfg)
        ok("تم تحديث النماذج")
        return

    if "--telegram" in sys.argv:
        lang = "ar"
        cfg  = step_telegram(lang, cfg)
        save_config(cfg)
        ok("تم تحديث Telegram")
        return

    # إعداد كامل
    lang = step_welcome()
    input(f"\n  {Y}اضغط Enter للبدء...{R}")

    cfg = step_ai_models(lang, cfg)
    input(f"\n  {G}✅ تم إعداد النماذج. اضغط Enter للمتابعة...{R}")

    cfg = step_telegram(lang, cfg)
    input(f"\n  اضغط Enter للمتابعة...{R}")

    cfg = step_specialization(lang, cfg)
    input(f"\n  اضغط Enter للمتابعة...{R}")

    cfg = step_advanced(lang, cfg)
    input(f"\n  اضغط Enter لإنهاء الإعداد...{R}")

    step_finish(cfg, lang)

if __name__ == "__main__":
    main()
