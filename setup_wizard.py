#!/usr/bin/env python3
"""
CoBWeaverClaw — Setup Wizard
معالج تثبيت تفاعلي بأسلوب احترافي (مستوحى من OpenClaw).
يعمل في Termux أو أي طرفية على أي نظام.

python setup_wizard.py
"""
import os
import sys
import json
import getpass
import secrets
from pathlib import Path

# ── ألوان ───────────────────────────────────────────────────
R, B = "\033[0m", "\033[1m"
G, Y, C = "\033[32m", "\033[33m", "\033[36m"
RD, W, O = "\033[31m", "\033[37m", "\033[38;5;208m"

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def banner():
    clear()
    print(f"{O}{B}")
    print("  ██████╗ ██████╗ ██╗    ██╗")
    print("  ██╔════╝██╔══██╗██║    ██║   CoBWeaverClaw")
    print("  ██║     ██████╔╝██║ █╗ ██║   🕷️  Setup")
    print("  ██║     ██╔══██╗██║███╗██║")
    print("  ╚██████╗██████╔╝╚███╔███╔╝   v0.1.0")
    print("   ╚═════╝╚═════╝  ╚══╝╚══╝")
    print(f"{R}")

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
    d = "Y/n" if default else "y/N"
    try:
        v = input(f"  {prompt} [{d}]: ").strip().lower()
        return default if not v else v in ("y", "yes", "نعم")
    except (KeyboardInterrupt, EOFError):
        return default

def menu(title, options, default=1):
    """قائمة اختيار مرقّمة بأسلوب OpenClaw."""
    print(f"\n  {B}{title}{R}")
    for i, (label, desc) in enumerate(options, 1):
        dot = f"{G}●{R}" if i == default else f"{W}○{R}"
        d   = f" {W}({desc}){R}" if desc else ""
        print(f"  {dot} {label}{d}")
    print(f"  {W}↑/↓ اكتب الرقم • Enter للتأكيد{R}")
    while True:
        try:
            v = input(f"  [{default}]: ").strip()
            if not v:
                return default
            n = int(v)
            if 1 <= n <= len(options):
                return n
        except (ValueError, KeyboardInterrupt):
            pass

def ok(m):   print(f"  {G}✅ {m}{R}")
def warn(m): print(f"  {Y}⚠️  {m}{R}")
def info(m): print(f"  {C}ℹ️  {m}{R}")

# ── المزودون ────────────────────────────────────────────────
PROVIDERS = [
    ("Anthropic",       "anthropic",  "claude-sonnet-4-6",            "ANTHROPIC_API_KEY",  "console.anthropic.com/settings/keys",      False),
    ("OpenAI",          "openai",     "gpt-4o-mini",                  "OPENAI_API_KEY",     "platform.openai.com/api-keys",             False),
    ("Groq",            "groq",       "llama-3.3-70b-versatile",      "GROQ_API_KEY",       "console.groq.com/keys",                    True),
    ("Google Gemini",   "gemini",     "gemini-2.0-flash",             "GEMINI_API_KEY",     "aistudio.google.com/app/apikey",           True),
    ("DeepSeek",        "deepseek",   "deepseek-chat",                "DEEPSEEK_API_KEY",   "platform.deepseek.com/api_keys",           False),
    ("OpenRouter",      "openrouter", "meta-llama/llama-3.3-70b",     "OPENROUTER_API_KEY", "openrouter.ai/keys",                       True),
    ("Mistral AI",      "mistral",    "mistral-small-latest",         "MISTRAL_API_KEY",    "console.mistral.ai/api-keys",              False),
    ("xAI (Grok)",      "xai",        "grok-2",                       "XAI_API_KEY",        "console.x.ai",                             False),
    ("Z.AI (GLM)",      "zai",        "glm-4.6",                      "ZAI_API_KEY",        "z.ai",                                     False),
    ("Ollama (محلي)",   "ollama",     "mistral",                      "",                   "ollama.ai",                                True),
]

CHANNELS = [
    ("Terminal فقط",        "terminal",  "تشغيل في الطرفية مباشرة (موصى به للبداية)"),
    ("Telegram",            "telegram",  "بوت Telegram للتحكم عن بعد"),
    ("Discord",             "discord",   "بوت Discord"),
    ("Slack",               "slack",     "Slack Socket Mode"),
    ("WhatsApp",            "whatsapp",  "WhatsApp عبر API"),
]

BROWSERS = [
    ("CoBWeaver Browser الداخلي", "internal", "متصفح الوكيل المدمج — جلب وبحث وتلخيص (موصى به)"),
    ("DuckDuckGo (بلا مفتاح)",    "duckduckgo","بحث ويب مجاني بدون مفتاح API"),
    ("Brave Search",             "brave",     "يحتاج مفتاح API"),
    ("تخطّي الآن",                "skip",      "إعداده لاحقاً"),
]

def load_config():
    for p in ["config.yaml", os.path.expanduser("~/.cobweaverclaw/config.yaml")]:
        if os.path.exists(p):
            try:
                import yaml
                with open(p) as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
    return {}

def save_config(cfg):
    try:
        import yaml
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        warn(f"تعذّر حفظ config.yaml: {e}")

def save_env(env_vars):
    env_path = Path(".env")
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

def test_key(provider, key):
    import urllib.request, urllib.error
    try:
        if provider == "anthropic":
            req = urllib.request.Request("https://api.anthropic.com/v1/models",
                  headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
        elif provider in ("openai", "groq", "deepseek", "openrouter", "mistral", "xai"):
            urls = {"openai":"https://api.openai.com/v1/models",
                    "groq":"https://api.groq.com/openai/v1/models",
                    "deepseek":"https://api.deepseek.com/models",
                    "openrouter":"https://openrouter.ai/api/v1/models",
                    "mistral":"https://api.mistral.ai/v1/models",
                    "xai":"https://api.x.ai/v1/models"}
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

# ════════════════════════════════════════════════════════════
# الخطوات
# ════════════════════════════════════════════════════════════

def step_security():
    diamond("Security disclaimer — تنبيه أمني")
    print(f"""
  {W}CoBWeaverClaw وكيل شخصي بحدّ ثقة واحد (أنت).
  • يستطيع قراءة الملفات وتنفيذ أوامر إذا فُعّلت الأدوات.
  • prompt خبيث قد يخدعه — لا تُعطِه مدخلات لا تثق بها.
  • البوابة محمية بتوكين عشوائي، و localhost افتراضياً.
  • أبقِ المفاتيح الحساسة بعيدة عن متناول الوكيل.{R}
""")
    if not ask_yn("أفهم أن هذا وكيل شخصي. أتابع؟", default=True):
        print(f"  {Y}تم الإيقاف.{R}")
        sys.exit(0)

def step_models(cfg):
    diamond("Model / auth provider — مزوّد النماذج")
    print(f"\n  {B}الشركات المتاحة:{R}\n")
    for i, (name, pid, model, env, url, free) in enumerate(PROVIDERS, 1):
        badge = f"{G}مجاني{R}" if free else f"{Y}مدفوع{R}"
        print(f"  {C}{i:2}{R}. {B}{name:<18}{R} {badge}  {W}{model}{R}")
    print(f"\n  {Y}اكتب أرقام ما تريد (مثل 1,3,4) أو all أو Enter للأساسي{R}")
    sel = ask("اختيارك", default="3").strip()

    if sel.lower() == "all":
        chosen = list(range(len(PROVIDERS)))
    else:
        chosen = []
        for x in sel.split(","):
            x = x.strip()
            if x.isdigit() and 1 <= int(x) <= len(PROVIDERS):
                chosen.append(int(x) - 1)
    if not chosen:
        chosen = [2]  # Groq افتراضياً (مجاني)

    cfg.setdefault("brain", {})
    env_vars = {}
    roles_assigned = []

    for idx in chosen:
        name, pid, model, env, url, free = PROVIDERS[idx]
        print(f"\n  {B}{C}━━━ {name} ━━━{R}")
        if pid == "ollama":
            if ask_yn("هل Ollama مثبّت لديك محلياً؟", default=False):
                m = ask("النموذج المحلي", default=model)
                cfg["brain"]["local"] = f"ollama/{m}"
                ok(f"Ollama → {m}")
            continue
        print(f"  {W}المفتاح من: {C}{url}{R}")
        key = ask(f"مفتاح {name}", secret=True)
        if not key:
            warn(f"تُخطّي {name}")
            continue
        print(f"  {Y}⟳ اختبار...{R}", end="", flush=True)
        res = test_key(pid, key)
        if res is True:
            print(f"\r  {G}✅ المفتاح صحيح ويعمل{R}            ")
        elif res is False:
            print(f"\r  {RD}❌ المفتاح مرفوض (401){R}          ")
            if not ask_yn("حفظه رغم ذلك؟", default=False):
                continue
        else:
            print(f"\r  {Y}⚠️  تعذّر التحقق — تم الحفظ{R}      ")

        m = ask("النموذج", default=model)
        if env:
            env_vars[env] = key

        # تعيين الدور تلقائياً
        if not cfg["brain"].get("primary"):
            cfg["brain"]["primary"] = f"{pid}/{m}"
            roles_assigned.append(f"{name} → primary (تحليل عميق)")
        elif not cfg["brain"].get("fast"):
            cfg["brain"]["fast"] = f"{pid}/{m}"
            roles_assigned.append(f"{name} → fast (ردود سريعة)")
        else:
            cfg["brain"][f"extra_{pid}"] = f"{pid}/{m}"
            roles_assigned.append(f"{name} → إضافي")
        ok(f"{name} — {m}")

    if env_vars:
        save_env(env_vars)
    if roles_assigned:
        print(f"\n  {B}الأدوار:{R}")
        for r in roles_assigned:
            print(f"    {G}•{R} {r}")
    return cfg

def step_browser(cfg):
    diamond("Browser / Search — المتصفح والبحث")
    choice = menu("اختر متصفح/محرك البحث للوكيل:", BROWSERS, default=1)
    name, bid, desc = BROWSERS[choice - 1]
    cfg.setdefault("browser", {})
    cfg["browser"]["provider"] = bid
    if bid == "internal":
        cfg["browser"]["enabled"] = True
        cfg["browser"]["mode"]    = "both"  # يدوي + تلقائي
        ok("المتصفح الداخلي CoBWeaver Browser مُفعّل (يدوي + تلقائي)")
        info("يجلب الصفحات، يبحث، ويُلخّص. (لا يُشغّل JavaScript)")
    elif bid == "brave":
        key = ask("مفتاح Brave Search API", secret=True)
        if key:
            save_env({"BRAVE_API_KEY": key})
        ok("Brave Search")
    elif bid == "duckduckgo":
        cfg["browser"]["enabled"] = True
        ok("DuckDuckGo (بلا مفتاح)")
    else:
        info("تخطّيت — يمكنك إعداده لاحقاً")
    return cfg

def step_channel(cfg):
    diamond("Channel — قناة التحكم")
    choice = menu("كيف تريد التحكم بالوكيل؟", CHANNELS, default=1)
    name, cid, desc = CHANNELS[choice - 1]
    cfg.setdefault("interfaces", {})
    if cid == "terminal":
        cfg["interfaces"]["cli"] = {"enabled": True}
        ok("Terminal — تشغيل مباشر في الطرفية")
    elif cid == "telegram":
        print(f"\n  {W}خطوات: افتح @BotFather → /newbot → انسخ التوكين{R}")
        token = ask("BOT_TOKEN", secret=True)
        if token:
            chat = ask("chat_id (اختياري)", default="")
            cfg["interfaces"]["telegram"] = {"enabled": True, "token": token, "owner_chat_id": chat}
            save_env({"TELEGRAM_BOT_TOKEN": token})
            ok("Telegram مُعدّ")
        else:
            warn("تُخطّي Telegram")
    else:
        cfg["interfaces"][cid] = {"enabled": True}
        info(f"{name} — أكمل إعداده لاحقاً من الإعدادات")
    return cfg

def step_gateway(cfg):
    diamond("Control Gateway — بوابة التحكم")
    print(f"""
  {W}بوابة تحكم عبر المتصفح، محمية بتوكين عشوائي.{R}
""")
    enable = ask_yn("تفعيل بوابة التحكم عبر المتصفح؟", default=True)
    cfg.setdefault("gateway", {})
    cfg["gateway"]["enabled"] = enable
    if not enable:
        info("تخطّيت البوابة")
        return cfg

    network = menu("نطاق الوصول للبوابة:", [
        ("localhost فقط", "أأمن — أنت فقط على هذا الجهاز"),
        ("الشبكة المحلية", "من أجهزة أخرى على شبكتك — يحتاج التوكين"),
    ], default=1)
    cfg["gateway"]["host"] = "127.0.0.1" if network == 1 else "0.0.0.0"
    cfg["gateway"]["port"] = 8787

    # توليد التوكين
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from gateway_auth import GatewayAuth
        auth  = GatewayAuth()
        token = auth.get_or_create_token()
        host  = cfg["gateway"]["host"]
        disp  = host if host != "0.0.0.0" else "<عنوان-جهازك>"
        print(f"\n  {G}✅ البوابة جاهزة{R}")
        print(f"  {B}الرابط (مع التوكين):{R}")
        print(f"  {C}http://{disp}:8787/#token={token}{R}")
        if host == "0.0.0.0":
            warn("مفتوحة على الشبكة — التوكين إجباري")
        else:
            ok("localhost فقط — آمن")
        print(f"\n  {W}لفتحها لاحقاً: {C}python main.py gateway{R}")
        print(f"  {W}لعرض الرابط:  {C}python main.py gateway --url{R}")
    except Exception as e:
        warn(f"تعذّر توليد التوكين: {e}")
    return cfg

def step_account(cfg):
    diamond("Account & Backup — الحساب والنسخ الاحتياطي")
    try:
        from account_manager import AccountManager
        am  = AccountManager()
        acc = am.get_or_create_account()
        ok(f"حسابك: {acc['account_id']}")
        info("هذا المعرّف ثابت ولا يُفقد. لاستعادته في أي وقت: python main.py account")
        if ask_yn("إنشاء نسخة احتياطية الآن؟", default=False):
            path = am.create_backup()
            ok(f"النسخة: {path}")
            info("انقلها لجهاز آخر واستعدها بـ: python main.py restore <file>")
    except Exception as e:
        warn(f"تعذّر إعداد الحساب: {e}")
    return cfg

def step_finish(cfg):
    diamond("اكتمل الإعداد! 🎉")
    save_config(cfg)
    print(f"\n  {G}{B}✅ تم حفظ كل الإعدادات{R}\n")
    brain = cfg.get("brain", {})
    if brain.get("primary"): print(f"  🤖 أساسي:  {G}{brain['primary']}{R}")
    if brain.get("fast"):    print(f"  ⚡ سريع:   {G}{brain['fast']}{R}")
    if brain.get("local"):   print(f"  💻 محلي:   {G}{brain['local']}{R}")
    if cfg.get("browser", {}).get("provider"):
        print(f"  🌐 المتصفح: {G}{cfg['browser']['provider']}{R}")
    if cfg.get("gateway", {}).get("enabled"):
        print(f"  🔒 البوابة: {G}مُفعّلة ({cfg['gateway']['host']}:8787){R}")
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

def main():
    banner()
    cfg = load_config()

    # وضع إعداد محدد
    if "--models" in sys.argv:
        save_config(step_models(cfg)); return
    if "--browser" in sys.argv:
        save_config(step_browser(cfg)); return
    if "--gateway" in sys.argv:
        save_config(step_gateway(cfg)); return

    step_security()
    cfg = step_models(cfg)
    cfg = step_browser(cfg)
    cfg = step_channel(cfg)
    cfg = step_gateway(cfg)
    cfg = step_account(cfg)
    step_finish(cfg)

if __name__ == "__main__":
    main()
