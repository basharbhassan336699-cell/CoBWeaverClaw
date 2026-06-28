#!/usr/bin/env python3
"""
CoBWeaverClaw — Setup Wizard (full order 1→12).
Bilingual: language is chosen on the first screen and applied to ALL text.

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

GATEWAY_PORT = 7878

# لغة المعالج (تُحدَّد في أول شاشة). تؤثّر على كل النصوص اللاحقة.
LANG = "ar"
ORANGE = "\033[38;5;208m"

# ════════════════════════════════════════════════════════════
# Translation layer — كل نص للمستخدم يمرّ عبر t()
# ════════════════════════════════════════════════════════════
STRINGS = {
    "ar": {
        "cancelled": "تم الإلغاء.",
        "yes": "نعم", "no": "لا",
        # step1 security
        "security_title": "تنبيه أمني",
        "security_body": ("CoBWeaverClaw وكيل شخصي بحدّ ثقة واحد (أنت).\n"
                          "  • يقرأ الملفات وينفّذ أوامر إذا فُعّلت الأدوات.\n"
                          "  • prompt خبيث قد يخدعه — لا تُدخِل ما لا تثق به.\n"
                          "  • البوابة محمية بتوكين عشوائي، localhost افتراضياً.\n"
                          "  • أبقِ المفاتيح الحساسة بعيدة عن متناول الوكيل."),
        "security_confirm": "أفهم أن هذا وكيل شخصي. أتابع؟",
        "stopped": "تم الإيقاف.",
        # step2 mode
        "mode_title": "نمط الإعداد",
        "mode_prompt": "اختر نمط الإعداد:",
        "mode_quick": "QuickStart (موصى به)", "mode_quick_desc": "إعداد محلي سريع — يمكن تغييره لاحقاً",
        "mode_manual": "إعداد يدوي", "mode_manual_desc": "إعداد مفصّل لكل خيار",
        # step3 config handling
        "config_title": "معالجة الإعداد السابق",
        "config_detected": "تم اكتشاف إعداد سابق",
        "config_prompt": "ماذا تريد أن نفعل به؟",
        "config_keep": "الإبقاء على القيم الحالية", "config_keep_desc": "لا تغيّر شيئاً",
        "config_review": "مراجعة وتحديث", "config_review_desc": "أعد المرور على الخطوات",
        "config_reset": "إعادة الضبط قبل الإعداد", "config_reset_desc": "امسح القديم وابدأ نظيفاً",
        "config_reset_done": "تمت إعادة الضبط",
        # step4 provider
        "provider_title": "مزوّد الذكاء الاصطناعي",
        "provider_prompt": "اختر مزوّد النماذج:",
        "provider_hint": "يمكن إضافة أكثر من مزود — كرّر الخطوة لاحقاً",
        "badge_free": "مجاني", "badge_paid": "مدفوع",
        # step5 model
        "model_title": "تعريف النموذج",
        "ollama_installed_q": "هل Ollama مثبّت محلياً؟",
        "model_local_prompt": "اختر النموذج المحلي:",
        "model_manual": "✏️ كتابة يدوياً", "model_manual_desc": "أدخل اسم النموذج",
        "model_name_prompt": "اسم النموذج",
        "key_from": "المفتاح من:",
        "key_prompt": "مفتاح {name} API",
        "key_skipped": "تُخطّي {name}",
        "key_testing": "⟳ اختبار المفتاح...",
        "key_valid": "المفتاح صحيح ويعمل",
        "key_rejected": "المفتاح مرفوض (401)",
        "action_prompt": "ماذا تفعل؟",
        "action_retry": "إعادة الإدخال", "action_save_anyway": "حفظه رغم ذلك", "action_skip": "تخطّي",
        "verify_failed_saved": "تعذّر التحقق — سيُحفظ",
        "model_choose_prompt": "اختر نموذج {name} أو عرّفه يدوياً:",
        "model_manual_def": "✏️ كتابة التعريف يدوياً", "model_manual_def_desc": "أدخل اسم نموذج مخصّص",
        "role_prompt": "ما دور هذا النموذج؟",
        "role_primary": "primary — التحليل العميق", "role_fast": "fast — الردود السريعة",
        "role_coding": "coding — البرمجة", "role_arabic": "arabic — العربية",
        "role_fallback": "fallback — احتياطي",
        "add_another_q": "إضافة مزوّد آخر؟",
        "model_saved": "{name} → {model} ({role})",
        # step6 channels
        "channel_title": "قنوات التواصل",
        "channel_prompt": "كيف تريد التحكم بالوكيل؟",
        "ch_terminal": "Terminal (الطرفية)", "ch_terminal_desc": "تشغيل مباشر — موصى به للبداية",
        "ch_telegram": "Telegram", "ch_telegram_desc": "بوت Telegram للتحكم عن بُعد",
        "ch_discord": "Discord", "ch_discord_desc": "بوت Discord",
        "ch_slack": "Slack", "ch_slack_desc": "Slack Socket Mode",
        "ch_whatsapp": "WhatsApp", "ch_whatsapp_desc": "WhatsApp Business API",
        "ch_signal": "Signal", "ch_signal_desc": "Signal عبر signal-cli",
        "terminal_set": "Terminal — تشغيل مباشر في الطرفية",
        "tg_link_prompt": "Telegram — طريقة الربط:",
        "tg_enter_token": "إدخال توكين البوت", "tg_enter_token_desc": "من @BotFather (الأضمن)",
        "tg_show_link": "عرض رابط البوت", "tg_show_link_desc": "للوصول السريع بعد الإدخال",
        "tg_steps": "خطوات: افتح @BotFather → /newbot → انسخ التوكين",
        "telegram_token": "أدخل توكين بوت تيليجرام",
        "tg_skipped": "تُخطّي Telegram",
        "tg_testing": "⟳ اختبار البوت...",
        "tg_working": "البوت يعمل: @{username}",
        "tg_link": "رابط البوت: https://t.me/{username}",
        "tg_invalid": "توكين غير صحيح",
        "tg_chatid_prompt": "chat_id (اختياري — Enter للتخطّي)",
        "tg_configured": "Telegram مُعدّ",
        "discord_link_prompt": "Discord — طريقة الربط:",
        "discord_enter_token": "إدخال Bot Token", "discord_enter_token_desc": "من Discord Developer Portal",
        "discord_guide": "إرشادات الإعداد", "discord_guide_desc": "كيف تُنشئ بوت Discord",
        "discord_guide_text": "أنشئ تطبيقاً في discord.com/developers → Bot → Token",
        "discord_token_prompt": "Discord Bot Token",
        "discord_configured": "Discord مُعدّ",
        "slack_bot_prompt": "Slack Bot Token (xoxb-...)",
        "slack_app_prompt": "Slack App Token (xapp-...)",
        "slack_configured": "Slack مُعدّ",
        "whatsapp_note": "WhatsApp يحتاج حساب Business API (Meta)",
        "whatsapp_token_prompt": "WhatsApp API Token",
        "whatsapp_phone_prompt": "Phone Number ID",
        "whatsapp_configured": "WhatsApp مُعدّ",
        "signal_note": "Signal يحتاج signal-cli مثبّتاً ورقماً مسجّلاً",
        "signal_number_prompt": "رقم Signal (+...)",
        "signal_configured": "Signal مُعدّ",
        # step7 search
        "search_title": "محرك البحث",
        "search_prompt": "اختر محرك البحث/المتصفح للوكيل:",
        "sp_internal": "CoBWeaver Browser الداخلي", "sp_internal_desc": "متصفح الوكيل المدمج — جلب وبحث وتلخيص (موصى به)",
        "sp_ddg": "DuckDuckGo", "sp_ddg_desc": "بحث ويب مجاني بلا مفتاح",
        "sp_brave": "Brave Search", "sp_brave_desc": "يحتاج مفتاح API",
        "sp_tavily": "Tavily", "sp_tavily_desc": "بحث مخصص للذكاء الاصطناعي — يحتاج مفتاح",
        "sp_skip": "تخطّي الآن", "sp_skip_desc": "إعداده لاحقاً",
        "internal_enabled": "المتصفح الداخلي CoBWeaver Browser مُفعّل",
        "internal_note": "يجلب الصفحات، يبحث، ويُلخّص. (لا يُشغّل JavaScript)",
        "ddg_enabled": "DuckDuckGo (بلا مفتاح)",
        "brave_key_prompt": "مفتاح Brave Search API", "brave_enabled": "Brave Search",
        "tavily_key_prompt": "مفتاح Tavily API", "tavily_enabled": "Tavily",
        "search_skipped": "تخطّيت محرك البحث",
        # step8 skills
        "skills_title": "حالة المهارات",
        "skills_available": "المهارات المتاحة:",
        "skills_missing": "متطلبات ناقصة:",
        "skills_unsupported": "غير مدعومة هنا:",
        "skills_enable_q": "تفعيل المهارات الآن؟",
        "skills_enabled": "المهارات مُفعّلة",
        "skills_later": "يمكن تفعيلها لاحقاً",
        # step9 hooks
        "hooks_title": "الأتمتة (Hooks)",
        "hooks_intro": "الـ Hooks تُؤتمت إجراءات عند تنفيذ أوامر معيّنة.",
        "hooks_prompt": "اختر الـ Hooks (Space للتحديد):",
        "hook_session-memory": "حفظ سياق الجلسة في الذاكرة عند /new أو /reset",
        "hook_command-logger": "تسجيل كل الأوامر المنفّذة",
        "hook_boot-notify": "إشعار عند بدء تشغيل الوكيل",
        "hook_update-notify": "إشعار عند توفّر تحديث جديد",
        "hook_backup-reminder": "تذكير دوري بأخذ نسخة احتياطية",
        "hooks_enabled": "فُعّلت: {list}",
        "hooks_none": "لم تُفعّل أي hooks",
        # step10 run
        "run_title": "تشغيل الوكيل",
        "run_prompt": "كيف تريد تشغيل الوكيل؟",
        "run_terminal": "في الطرفية (موصى به)", "run_terminal_desc": "يبدأ مباشرة بعد الإعداد",
        "run_browser": "عبر المتصفح", "run_browser_desc": "عبر بوابة التحكم",
        "run_later": "لاحقاً", "run_later_desc": "أشغّله بنفسي بأمر python main.py",
        # step11 gateway
        "gateway_title": "بوابة التحكم",
        "gateway_intro": "بوابة تحكم عبر المتصفح، localhost افتراضياً.",
        "gateway_enable_q": "تفعيل بوابة التحكم؟",
        "gateway_skipped": "تخطّيت البوابة",
        "gateway_scope_prompt": "نطاق الوصول:",
        "scope_local": "localhost فقط", "scope_local_desc": "أأمن — أنت فقط على هذا الجهاز",
        "scope_network": "الشبكة المحلية", "scope_network_desc": "من أجهزة أخرى على شبكتك (التوكين إجباري)",
        "gateway_ready": "البوابة جاهزة",
        "gateway_url_label": "رابط بوابة التحكم:",
        "gateway_network_warn": "مفتوحة على الشبكة — التوكين إجباري",
        "gateway_local_ok": "localhost فقط — آمن",
        "gateway_open_later": "لفتحها لاحقاً: python main.py gateway",
        "gateway_show_url": "لعرض الرابط:  python main.py gateway --url",
        "gateway_token_failed": "تعذّر توليد التوكين: {err}",
        # step12 finish
        "finish_title": "اكتمل الإعداد! 🎉",
        "settings_saved": "تم حفظ كل الإعدادات",
        "label_primary": "🤖 أساسي:", "label_fast": "⚡ سريع:", "label_local": "💻 محلي:",
        "label_browser": "🌐 المتصفح:", "label_channels": "📡 القنوات:",
        "label_gateway": "🔒 البوابة:", "label_account": "🆔 الحساب:",
        "gateway_open_header": "━━━ لفتح بوابة التحكم ━━━",
        "gateway_run_cmd": "شغّل الأمر التالي في الطرفية:",
        "gateway_then_open": "ثم افتح الرابط في المتصفح.",
        "gateway_keep_running": "(البوابة تحتاج أن تبقى تعمل — لا تغلق الطرفية)",
        "start_commands": "أوامر البدء:",
        "cmd_cli": "تشغيل CLI", "cmd_gateway": "فتح بوابة التحكم",
        "cmd_gateway_url": "عرض رابط البوابة", "cmd_account": "عرض/استعادة الحساب",
        "cmd_backup": "نسخة احتياطية", "cmd_restore": "استعادة نسخة",
        "cmd_restart": "إعادة التشغيل", "cmd_doctor": "تشخيص وإصلاح",
        "ready": "🕷️  CoBWeaverClaw جاهز!",
        "done": "تم الإعداد بنجاح",
    },
    "en": {
        "cancelled": "Cancelled.",
        "yes": "Yes", "no": "No",
        # step1 security
        "security_title": "Security Disclaimer",
        "security_body": ("CoBWeaverClaw is a personal agent with a single trust level (you).\n"
                          "  • It reads files and runs commands when tools are enabled.\n"
                          "  • A malicious prompt can trick it — don't feed untrusted input.\n"
                          "  • The gateway is localhost-only by default.\n"
                          "  • Keep sensitive keys out of the agent's reach."),
        "security_confirm": "I understand this is a personal agent. Continue?",
        "stopped": "Stopped.",
        # step2 mode
        "mode_title": "Setup Mode",
        "mode_prompt": "Choose setup mode:",
        "mode_quick": "QuickStart (recommended)", "mode_quick_desc": "Fast local setup — can change later",
        "mode_manual": "Manual setup", "mode_manual_desc": "Detailed setup for every option",
        # step3 config handling
        "config_title": "Existing Configuration",
        "config_detected": "Existing configuration detected",
        "config_prompt": "What should we do with it?",
        "config_keep": "Keep current values", "config_keep_desc": "Change nothing",
        "config_review": "Review and update", "config_review_desc": "Go through the steps again",
        "config_reset": "Reset before setup", "config_reset_desc": "Wipe the old config and start clean",
        "config_reset_done": "Reset complete",
        # step4 provider
        "provider_title": "Choose AI Provider",
        "provider_prompt": "Choose your model provider:",
        "provider_hint": "You can add more than one provider — repeat this step later",
        "badge_free": "Free", "badge_paid": "Paid",
        # step5 model
        "model_title": "Choose Default Model",
        "ollama_installed_q": "Is Ollama installed locally?",
        "model_local_prompt": "Choose the local model:",
        "model_manual": "✏️ Type manually", "model_manual_desc": "Enter the model name",
        "model_name_prompt": "Model name",
        "key_from": "Get the key from:",
        "key_prompt": "{name} API key",
        "key_skipped": "Skipping {name}",
        "key_testing": "⟳ Testing the key...",
        "key_valid": "Key is valid and working",
        "key_rejected": "Key rejected (401)",
        "action_prompt": "What do you want to do?",
        "action_retry": "Re-enter", "action_save_anyway": "Save it anyway", "action_skip": "Skip",
        "verify_failed_saved": "Could not verify — will be saved",
        "model_choose_prompt": "Choose a {name} model or define it manually:",
        "model_manual_def": "✏️ Define manually", "model_manual_def_desc": "Enter a custom model name",
        "role_prompt": "What role does this model serve?",
        "role_primary": "primary — deep analysis", "role_fast": "fast — quick replies",
        "role_coding": "coding — programming", "role_arabic": "arabic — Arabic",
        "role_fallback": "fallback — backup",
        "add_another_q": "Add another provider?",
        "model_saved": "{name} → {model} ({role})",
        # step6 channels
        "channel_title": "Communication Channels",
        "channel_prompt": "How do you want to control the agent?",
        "ch_terminal": "Terminal", "ch_terminal_desc": "Run directly — recommended to start",
        "ch_telegram": "Telegram", "ch_telegram_desc": "Telegram bot for remote control",
        "ch_discord": "Discord", "ch_discord_desc": "Discord bot",
        "ch_slack": "Slack", "ch_slack_desc": "Slack Socket Mode",
        "ch_whatsapp": "WhatsApp", "ch_whatsapp_desc": "WhatsApp Business API",
        "ch_signal": "Signal", "ch_signal_desc": "Signal via signal-cli",
        "terminal_set": "Terminal — running directly in the shell",
        "tg_link_prompt": "Telegram — linking method:",
        "tg_enter_token": "Enter bot token", "tg_enter_token_desc": "From @BotFather (most reliable)",
        "tg_show_link": "Show bot link", "tg_show_link_desc": "Quick access after entering the token",
        "tg_steps": "Steps: open @BotFather → /newbot → copy the token",
        "telegram_token": "Enter Telegram bot token",
        "tg_skipped": "Skipping Telegram",
        "tg_testing": "⟳ Testing the bot...",
        "tg_working": "Bot is working: @{username}",
        "tg_link": "Bot link: https://t.me/{username}",
        "tg_invalid": "Invalid token",
        "tg_chatid_prompt": "chat_id (optional — Enter to skip)",
        "tg_configured": "Telegram configured",
        "discord_link_prompt": "Discord — linking method:",
        "discord_enter_token": "Enter Bot Token", "discord_enter_token_desc": "From the Discord Developer Portal",
        "discord_guide": "Setup guide", "discord_guide_desc": "How to create a Discord bot",
        "discord_guide_text": "Create an app at discord.com/developers → Bot → Token",
        "discord_token_prompt": "Discord Bot Token",
        "discord_configured": "Discord configured",
        "slack_bot_prompt": "Slack Bot Token (xoxb-...)",
        "slack_app_prompt": "Slack App Token (xapp-...)",
        "slack_configured": "Slack configured",
        "whatsapp_note": "WhatsApp requires a Business API account (Meta)",
        "whatsapp_token_prompt": "WhatsApp API Token",
        "whatsapp_phone_prompt": "Phone Number ID",
        "whatsapp_configured": "WhatsApp configured",
        "signal_note": "Signal requires signal-cli installed and a registered number",
        "signal_number_prompt": "Signal number (+...)",
        "signal_configured": "Signal configured",
        # step7 search
        "search_title": "Search Engine",
        "search_prompt": "Choose the agent's search engine / browser:",
        "sp_internal": "Internal CoBWeaver Browser", "sp_internal_desc": "Built-in browser — fetch, search, summarize (recommended)",
        "sp_ddg": "DuckDuckGo", "sp_ddg_desc": "Free web search, no key",
        "sp_brave": "Brave Search", "sp_brave_desc": "Requires an API key",
        "sp_tavily": "Tavily", "sp_tavily_desc": "AI-focused search — requires a key",
        "sp_skip": "Skip for now", "sp_skip_desc": "Set it up later",
        "internal_enabled": "Internal CoBWeaver Browser enabled",
        "internal_note": "Fetches pages, searches, and summarizes. (No JavaScript execution)",
        "ddg_enabled": "DuckDuckGo (no key)",
        "brave_key_prompt": "Brave Search API key", "brave_enabled": "Brave Search",
        "tavily_key_prompt": "Tavily API key", "tavily_enabled": "Tavily",
        "search_skipped": "Search engine skipped",
        # step8 skills
        "skills_title": "Skills Status",
        "skills_available": "Available skills:",
        "skills_missing": "Missing requirements:",
        "skills_unsupported": "Unsupported here:",
        "skills_enable_q": "Enable skills now?",
        "skills_enabled": "Skills enabled",
        "skills_later": "You can enable them later",
        # step9 hooks
        "hooks_title": "Automation (Hooks)",
        "hooks_intro": "Hooks automate actions when certain commands run.",
        "hooks_prompt": "Choose hooks (Space to select):",
        "hook_session-memory": "Save session context to memory on /new or /reset",
        "hook_command-logger": "Log every executed command",
        "hook_boot-notify": "Notify when the agent starts",
        "hook_update-notify": "Notify when an update is available",
        "hook_backup-reminder": "Periodic backup reminder",
        "hooks_enabled": "Enabled: {list}",
        "hooks_none": "No hooks enabled",
        # step10 run
        "run_title": "Run Agent",
        "run_prompt": "How do you want to run the agent?",
        "run_terminal": "In the terminal (recommended)", "run_terminal_desc": "Starts right after setup",
        "run_browser": "Via the browser", "run_browser_desc": "Through the control gateway",
        "run_later": "Later", "run_later_desc": "I'll run it myself with python main.py",
        # step11 gateway
        "gateway_title": "Control Gateway",
        "gateway_intro": "Browser-based control gateway, localhost by default.",
        "gateway_enable_q": "Enable the control gateway?",
        "gateway_skipped": "Gateway skipped",
        "gateway_scope_prompt": "Access scope:",
        "scope_local": "localhost only", "scope_local_desc": "Safest — only you on this device",
        "scope_network": "Local network", "scope_network_desc": "From other devices on your network (token required)",
        "gateway_ready": "Gateway ready",
        "gateway_url_label": "Control gateway URL:",
        "gateway_network_warn": "Exposed on the network — token required",
        "gateway_local_ok": "localhost only — secure",
        "gateway_open_later": "To open later: python main.py gateway",
        "gateway_show_url": "To show the URL: python main.py gateway --url",
        "gateway_token_failed": "Could not generate token: {err}",
        # step12 finish
        "finish_title": "Setup complete! 🎉",
        "settings_saved": "All settings saved",
        "label_primary": "🤖 Primary:", "label_fast": "⚡ Fast:", "label_local": "💻 Local:",
        "label_browser": "🌐 Browser:", "label_channels": "📡 Channels:",
        "label_gateway": "🔒 Gateway:", "label_account": "🆔 Account:",
        "gateway_open_header": "━━━ To open the control gateway ━━━",
        "gateway_run_cmd": "Run the following command in the terminal:",
        "gateway_then_open": "Then open the URL in your browser.",
        "gateway_keep_running": "(The gateway must stay running — don't close the terminal)",
        "start_commands": "Getting-started commands:",
        "cmd_cli": "Start the CLI", "cmd_gateway": "Open the control gateway",
        "cmd_gateway_url": "Show the gateway URL", "cmd_account": "Show/restore the account",
        "cmd_backup": "Create a backup", "cmd_restore": "Restore a backup",
        "cmd_restart": "Restart", "cmd_doctor": "Diagnose and fix",
        "ready": "🕷️  CoBWeaverClaw is ready!",
        "done": "Setup complete",
    },
}


def t(key, **kw):
    """يُعيد النص المترجَم حسب اللغة المختارة (مع تنسيق اختياري)."""
    s = STRINGS.get(LANG, STRINGS["ar"]).get(key)
    if s is None:
        s = STRINGS["ar"].get(key, key)
    return s.format(**kw) if kw else s


# ════════════════════════════════════════════════════════════
# UI helpers
# ════════════════════════════════════════════════════════════
def clear():
    os.system("clear" if os.name != "nt" else "cls")

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
    print(f"  {ORANGE}{B}Bashar Hassan{R}")
    print(f"  {DIM}Setup v0.1.0{R}\n")

def diamond(title):
    print(f"\n{G}◇{R}  {O}{B}{title}{R}")

def header(n, title_key):
    diamond(f"{n}/12 — {t(title_key)}")

def ask(prompt, default="", secret=False):
    disp = f"  {prompt}" + (f" [{C}{default}{R}]" if default else "") + ": "
    try:
        v = getpass.getpass(disp) if secret else input(disp).strip()
        return v or default
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Y}{t('cancelled')}{R}")
        sys.exit(0)

def ask_yn(prompt, default=True):
    sel = select(prompt, [(t("yes"), ""), (t("no"), "")], allow_back=False)
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
    _ensure_config_dir()
    try:
        import yaml
        path = os.path.join(CONFIG_DIR, "config.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        warn(f"config.yaml: {e}")

def save_env(env_vars):
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
# البيانات (brand names + ids؛ الأوصاف تُترجَم عبر t())
# ════════════════════════════════════════════════════════════
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
    ("Ollama",        "ollama",     "mistral",                  "",                   "ollama.ai", True,
        ["mistral","llama3.3","qwen2.5","gemma3","phi4"]),
]

# (id) فقط — الاسم والوصف يُترجمان
CHANNELS = ["terminal", "telegram", "discord", "slack", "whatsapp", "signal"]
SEARCH_IDS = ["internal", "duckduckgo", "brave", "tavily", "skip"]
HOOK_IDS = ["session-memory", "command-logger", "boot-notify", "update-notify", "backup-reminder"]

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
# الخطوات
# ════════════════════════════════════════════════════════════

def step0_language(cfg):
    """أول شاشة على الإطلاق — اختيار اللغة (تُعرض بالإنجليزية قبل أي اختيار)."""
    global LANG
    banner()
    print(f"  {O}{B}┌─────────────────────────────────────────┐{R}")
    print(f"  {O}{B}│  Choose your language / اختر لغتك       │{R}")
    print(f"  {O}{B}│  1. العربية                             │{R}")
    print(f"  {O}{B}│  2. English                             │{R}")
    print(f"  {O}{B}└─────────────────────────────────────────┘{R}")
    sel = select("Choose your language / اختر لغتك:",
                 [("العربية", "Arabic"), ("English", "الإنجليزية")], allow_back=False)
    LANG = "en" if sel == 1 else "ar"
    cfg.setdefault("agent", {})["language"] = LANG
    cfg.setdefault("interface", {})["language"] = LANG
    return "next"


def step1_security(cfg):
    header(1, "security_title")
    print(f"\n  {DIM}{t('security_body')}{R}")
    if not ask_yn(t("security_confirm"), default=True):
        print(f"  {Y}{t('stopped')}{R}")
        sys.exit(0)
    return "next"

def step2_mode(cfg):
    header(2, "mode_title")
    sel = select(t("mode_prompt"), [
        (t("mode_quick"), t("mode_quick_desc")),
        (t("mode_manual"), t("mode_manual_desc")),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    cfg["_setup_mode"] = "quick" if sel == 0 else "manual"
    return "next"

def step3_config_handling(cfg):
    existing = bool(cfg.get("brain", {}).get("primary")
                    or os.path.exists(os.path.join(CONFIG_DIR, ".env")))
    if not existing:
        return "next"
    header(3, "config_title")
    info(t("config_detected"))
    sel = select(t("config_prompt"), [
        (t("config_keep"), t("config_keep_desc")),
        (t("config_review"), t("config_review_desc")),
        (t("config_reset"), t("config_reset_desc")),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    if sel == 2:
        for f in [".env", "config.yaml"]:
            p = os.path.join(CONFIG_DIR, f)
            if os.path.exists(p):
                os.remove(p)
        cfg.clear()
        ok(t("config_reset_done"))
    cfg["_config_handling"] = ["keep","review","reset"][sel]
    return "next"

def step4_provider(cfg):
    header(4, "provider_title")
    opts = []
    for name, pid, model, env, url, free, models in PROVIDERS:
        badge = f"{G}{t('badge_free')}{R}" if free else f"{Y}{t('badge_paid')}{R}"
        opts.append((name, f"{badge} · {model}"))
    sel = select(t("provider_prompt"), opts, allow_back=True, hint=t("provider_hint"))
    if sel == BACK:
        return BACK
    cfg["_chosen_provider"] = sel
    return "next"

def step5_model_def(cfg):
    idx = cfg.get("_chosen_provider", 0)
    name, pid, default_model, env, url, free, models = PROVIDERS[idx]
    header(5, "model_title")

    if pid == "ollama":
        if ask_yn(t("ollama_installed_q"), default=False):
            opts = [(m, "") for m in models] + [(t("model_manual"), t("model_manual_desc"))]
            sel = select(t("model_local_prompt"), opts, allow_back=True)
            if sel == BACK: return BACK
            model = ask(t("model_name_prompt"), default=default_model) if sel == len(opts)-1 else models[sel]
            cfg.setdefault("brain", {})["local"] = f"ollama/{model}"
            ok(f"Ollama → {model}")
        return "next"

    print(f"  {DIM}{t('key_from')} {C}{url}{R}")
    key = ask(t("key_prompt", name=name), secret=True)
    if not key:
        warn(t("key_skipped", name=name))
        return "next"
    print(f"  {Y}{t('key_testing')}{R}")
    res = test_key(pid, key)
    if res is True:
        ok(t("key_valid"))
    elif res is False:
        err(t("key_rejected"))
        sel = select(t("action_prompt"), [
            (t("action_retry"), ""), (t("action_save_anyway"), ""), (t("action_skip"), ""),
        ], allow_back=True)
        if sel == BACK or sel == 3: return BACK
        if sel == 0: return step5_model_def(cfg)
        if sel == 2: return "next"
    else:
        warn(t("verify_failed_saved"))

    opts = [(m, "") for m in models] + [(t("model_manual_def"), t("model_manual_def_desc"))]
    sel = select(t("model_choose_prompt", name=name), opts, allow_back=True)
    if sel == BACK:
        return BACK
    model = ask(t("model_name_prompt"), default=default_model) if sel == len(opts)-1 else models[sel]

    role_opts = [
        (t("role_primary"), ""), (t("role_fast"), ""), (t("role_coding"), ""),
        (t("role_arabic"), ""), (t("role_fallback"), ""),
    ]
    rsel = select(t("role_prompt"), role_opts, allow_back=True)
    if rsel == BACK:
        return BACK
    role = ["primary","fast","coding","arabic","fallback"][rsel]

    cfg.setdefault("brain", {})[role] = f"{pid}/{model}"
    if env:
        save_env({env: key})
    ok(t("model_saved", name=name, model=model, role=role))

    if ask_yn(t("add_another_q"), default=False):
        r = step4_provider(cfg)
        if r == BACK:
            return "next"
        return step5_model_def(cfg)
    return "next"

def step6_channel(cfg):
    header(6, "channel_title")
    opts = [(t(f"ch_{cid}"), t(f"ch_{cid}_desc")) for cid in CHANNELS]
    sel = select(t("channel_prompt"), opts, allow_back=True)
    if sel == BACK:
        return BACK
    cid = CHANNELS[sel]

    cfg.setdefault("interfaces", {})

    if cid == "terminal":
        cfg["interfaces"]["cli"] = {"enabled": True}
        ok(t("terminal_set"))
        return "next"

    if cid == "telegram":
        sub = select(t("tg_link_prompt"), [
            (t("tg_enter_token"), t("tg_enter_token_desc")),
            (t("tg_show_link"), t("tg_show_link_desc")),
        ], allow_back=True)
        if sub == BACK:
            return step6_channel(cfg)
        print(f"\n  {DIM}{t('tg_steps')}{R}")
        token = ask(t("telegram_token"), secret=True)
        if not token:
            warn(t("tg_skipped"))
            return step6_channel(cfg)
        print(f"  {Y}{t('tg_testing')}{R}")
        bot = test_telegram(token)
        if bot:
            ok(t("tg_working", username=bot.get('username','')))
            if sub == 1:
                info(t("tg_link", username=bot.get('username','')))
        else:
            err(t("tg_invalid"))
            retry = select(t("action_prompt"), [
                (t("action_retry"), ""), (t("tg_skipped"), ""),
            ], allow_back=True)
            if retry == BACK: return step6_channel(cfg)
            if retry == 0: return step6_channel(cfg)
            return "next"
        chat = ask(t("tg_chatid_prompt"), default="")
        cfg["interfaces"]["telegram"] = {"enabled": True, "token": token, "owner_chat_id": chat}
        save_env({"TELEGRAM_BOT_TOKEN": token})
        ok(t("tg_configured"))
        return "next"

    if cid == "discord":
        sub = select(t("discord_link_prompt"), [
            (t("discord_enter_token"), t("discord_enter_token_desc")),
            (t("discord_guide"), t("discord_guide_desc")),
        ], allow_back=True)
        if sub == BACK:
            return step6_channel(cfg)
        if sub == 1:
            info(t("discord_guide_text"))
        token = ask(t("discord_token_prompt"), secret=True)
        if token:
            cfg["interfaces"]["discord"] = {"enabled": True, "token": token}
            save_env({"DISCORD_BOT_TOKEN": token})
            ok(t("discord_configured"))
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "slack":
        token = ask(t("slack_bot_prompt"), secret=True)
        if token:
            app_token = ask(t("slack_app_prompt"), secret=True)
            cfg["interfaces"]["slack"] = {"enabled": True}
            save_env({"SLACK_BOT_TOKEN": token, "SLACK_APP_TOKEN": app_token})
            ok(t("slack_configured"))
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "whatsapp":
        info(t("whatsapp_note"))
        token = ask(t("whatsapp_token_prompt"), secret=True)
        phone = ask(t("whatsapp_phone_prompt"), default="")
        if token:
            cfg["interfaces"]["whatsapp"] = {"enabled": True, "phone_id": phone}
            save_env({"WHATSAPP_TOKEN": token})
            ok(t("whatsapp_configured"))
        else:
            return step6_channel(cfg)
        return "next"

    if cid == "signal":
        info(t("signal_note"))
        number = ask(t("signal_number_prompt"), default="")
        if number:
            cfg["interfaces"]["signal"] = {"enabled": True, "number": number}
            ok(t("signal_configured"))
        else:
            return step6_channel(cfg)
        return "next"

    return "next"

def step7_search(cfg):
    header(7, "search_title")
    opts = [(t(f"sp_{sid if sid!='duckduckgo' else 'ddg'}"),
             t(f"sp_{sid if sid!='duckduckgo' else 'ddg'}_desc")) for sid in SEARCH_IDS]
    sel = select(t("search_prompt"), opts, allow_back=True)
    if sel == BACK:
        return BACK
    sid = SEARCH_IDS[sel]
    cfg.setdefault("browser", {})
    cfg["browser"]["provider"] = sid

    if sid == "internal":
        cfg["browser"]["enabled"] = True
        cfg["browser"]["mode"] = "both"
        ok(t("internal_enabled"))
        info(t("internal_note"))
    elif sid == "duckduckgo":
        cfg["browser"]["enabled"] = True
        ok(t("ddg_enabled"))
    elif sid == "brave":
        key = ask(t("brave_key_prompt"), secret=True)
        if key: save_env({"BRAVE_API_KEY": key})
        ok(t("brave_enabled"))
    elif sid == "tavily":
        key = ask(t("tavily_key_prompt"), secret=True)
        if key: save_env({"TAVILY_API_KEY": key})
        ok(t("tavily_enabled"))
    else:
        info(t("search_skipped"))
    return "next"

def step8_skills(cfg):
    header(8, "skills_title")
    skills_dir = os.path.join(BASE_DIR, "skills")
    eligible = 0
    if os.path.isdir(skills_dir):
        import glob
        eligible = len([f for f in glob.glob(os.path.join(skills_dir,"*.py"))
                        if not os.path.basename(f).startswith("_")
                        and os.path.basename(f)[:-3] not in ("base","factory","evolver")])
    print(f"""
  {DIM}{t('skills_available')}  {G}{eligible}{R}{DIM}
  {t('skills_missing')}    0
  {t('skills_unsupported')}   0{R}""")
    if ask_yn(t("skills_enable_q"), default=True):
        cfg.setdefault("skills", {})["enabled"] = True
        ok(t("skills_enabled"))
    else:
        cfg.setdefault("skills", {})["enabled"] = False
        info(t("skills_later"))
    return "next"

def step9_hooks(cfg):
    header(9, "hooks_title")
    print(f"  {DIM}{t('hooks_intro')}{R}")
    opts = [(hid, t(f"hook_{hid}")) for hid in HOOK_IDS]
    sel = multi_select(t("hooks_prompt"), opts, allow_back=True)
    if sel == BACK:
        return BACK
    if sel == CANCEL:
        sel = []
    enabled = [HOOK_IDS[i] for i in sel]
    cfg.setdefault("hooks", {})["enabled"] = enabled
    if enabled:
        ok(t("hooks_enabled", list=", ".join(enabled)))
    else:
        info(t("hooks_none"))
    return "next"

def step10_run(cfg):
    header(10, "run_title")
    sel = select(t("run_prompt"), [
        (t("run_terminal"), t("run_terminal_desc")),
        (t("run_browser"), t("run_browser_desc")),
        (t("run_later"), t("run_later_desc")),
    ], allow_back=True)
    if sel == BACK:
        return BACK
    cfg["_run_mode"] = ["terminal","browser","later"][sel]
    return "next"

def step11_gateway(cfg):
    header(11, "gateway_title")
    print(f"  {DIM}{t('gateway_intro')}{R}")
    if not ask_yn(t("gateway_enable_q"), default=True):
        cfg.setdefault("gateway", {})["enabled"] = False
        info(t("gateway_skipped"))
        return "next"

    scope = select(t("gateway_scope_prompt"), [
        (t("scope_local"), t("scope_local_desc")),
        (t("scope_network"), t("scope_network_desc")),
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
        disp = host if host != "0.0.0.0" else "<your-device-ip>"
        print(f"\n  {G}✅ {t('gateway_ready')}{R}")
        print(f"  {B}{t('gateway_url_label')}{R}")
        print(f"  {C}http://{disp}:{GATEWAY_PORT}/#token={token}{R}")
        if host == "0.0.0.0":
            warn(t("gateway_network_warn"))
        else:
            ok(t("gateway_local_ok"))
        print(f"\n  {DIM}{t('gateway_open_later')}{R}")
        print(f"  {DIM}{t('gateway_show_url')}{R}")
    except Exception as e:
        warn(t("gateway_token_failed", err=e))
    return "next"

def step12_finish(cfg):
    header(12, "finish_title")
    run_mode_tmp = cfg.get("_run_mode","")
    for k in ["_chosen_provider","_setup_mode","_config_handling","_run_mode"]:
        cfg.pop(k, None)
    save_config(cfg)
    cfg["_run_mode_saved"] = run_mode_tmp

    try:
        from account_manager import AccountManager
        am = AccountManager()
        account_id = am.get_or_create_account()["account_id"]
    except Exception:
        account_id = "—"

    print(f"\n  {G}{B}✅ {t('settings_saved')}{R}\n")
    brain = cfg.get("brain", {})
    if brain.get("primary"): print(f"  {t('label_primary')}   {G}{brain['primary']}{R}")
    if brain.get("fast"):    print(f"  {t('label_fast')}    {G}{brain['fast']}{R}")
    if brain.get("local"):   print(f"  {t('label_local')}    {G}{brain['local']}{R}")
    if cfg.get("browser", {}).get("provider"):
        print(f"  {t('label_browser')} {G}{cfg['browser']['provider']}{R}")
    chans = [k for k,v in cfg.get("interfaces",{}).items() if v.get("enabled")]
    if chans: print(f"  {t('label_channels')} {G}{', '.join(chans)}{R}")
    if cfg.get("gateway",{}).get("enabled"):
        print(f"  {t('label_gateway')} {G}{cfg['gateway']['host']}:{GATEWAY_PORT}{R}")
    print(f"  {t('label_account')}  {G}{account_id}{R}")

    if cfg.get("gateway",{}).get("enabled"):
        print(f"\n  {Y}{t('gateway_open_header')}{R}")
        print(f"  {t('gateway_run_cmd')}")
        print(f"  {G}{B}python main.py gateway{R}")
        print(f"  {t('gateway_then_open')}")
        print(f"  {DIM}{t('gateway_keep_running')}{R}")

    print(f"""
  {B}{t('start_commands')}{R}
  {C}python main.py{R}              {t('cmd_cli')}
  {C}python main.py gateway{R}      {t('cmd_gateway')}
  {C}python main.py gateway --url{R} {t('cmd_gateway_url')}
  {C}python main.py account{R}      {t('cmd_account')}
  {C}python main.py backup{R}       {t('cmd_backup')}
  {C}python main.py restore <f>{R}  {t('cmd_restore')}
  {C}python main.py restart{R}      {t('cmd_restart')}
  {C}python main.py doctor --fix{R} {t('cmd_doctor')}

  {O}{B}{t('ready')}{R}
""")

# ════════════════════════════════════════════════════════════
# المُشغّل
# ════════════════════════════════════════════════════════════
STEPS = [
    step1_security, step2_mode, step3_config_handling, step4_provider,
    step5_model_def, step6_channel, step7_search, step8_skills,
    step9_hooks, step10_run, step11_gateway, step12_finish,
]

def run_wizard():
    cfg = load_config()
    step0_language(cfg)
    i = 0
    while i < len(STEPS):
        result = STEPS[i](cfg)
        if result == BACK:
            i = max(0, i - 1)
        else:
            i += 1
    return cfg

def _apply_saved_lang(cfg):
    """يضبط لغة المعالج من config في الأوضاع الجزئية."""
    global LANG
    LANG = cfg.get("interface", {}).get("language") or cfg.get("agent", {}).get("language") or "ar"

def main():
    if "--models" in sys.argv:
        cfg = load_config(); _apply_saved_lang(cfg); step4_provider(cfg); step5_model_def(cfg); save_config(cfg); return
    if "--channel" in sys.argv:
        cfg = load_config(); _apply_saved_lang(cfg); step6_channel(cfg); save_config(cfg); return
    if "--gateway" in sys.argv:
        cfg = load_config(); _apply_saved_lang(cfg); step11_gateway(cfg); save_config(cfg); return
    run_wizard()

if __name__ == "__main__":
    main()
