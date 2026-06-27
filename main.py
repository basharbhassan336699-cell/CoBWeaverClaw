#!/usr/bin/env python3
"""
CoBWeaverClaw — Entry Point
الأوامر:
  python main.py                    تشغيل CLI (أو معالج الإعداد أول مرة)
  python main.py setup              معالج الإعداد
  python main.py gateway            فتح بوابة التحكم عبر المتصفح
  python main.py gateway --url      عرض رابط البوابة فقط
  python main.py gateway --network  فتح البوابة للشبكة المحلية
  python main.py gateway --new-token توليد توكين جديد للبوابة
  python main.py account            عرض/استعادة بيانات الحساب
  python main.py backup [path]      إنشاء نسخة احتياطية
  python main.py restore <file>     استعادة نسخة احتياطية
  python main.py restart            إعادة تشغيل الوكيل
  python main.py doctor [--fix]     تشخيص وإصلاح
  python main.py status             الحالة
  python main.py help               المساعدة
"""
import os
import sys
import asyncio

# إتاحة استيراد الوحدات من المجلدات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))
sys.path.insert(0, os.path.join(BASE_DIR, "browser"))


def load_env():
    """تحميل .env إن وُجد."""
    env = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_config():
    import yaml
    for p in ["config.yaml", os.path.expanduser("~/.cobweaverclaw/config.yaml")]:
        if os.path.exists(p):
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def is_first_run():
    cfg = load_config()
    has_brain = bool(cfg.get("brain", {}).get("primary") or cfg.get("brain", {}).get("fast"))
    has_env   = os.path.exists(os.path.join(BASE_DIR, ".env"))
    return not (has_brain or has_env)


# ── الأوامر ─────────────────────────────────────────────────

def cmd_gateway(args):
    """فتح بوابة التحكم."""
    from gateway_auth import GatewayAuth
    auth = GatewayAuth()

    if "--new-token" in args:
        token = auth.regenerate_token()
        print(f"\n🔑 توكين جديد للبوابة:\n   {token}\n")
        print("   التوكين القديم أُلغي. استخدم الرابط الجديد.")
        return

    if "--url" in args:
        cfg  = load_config()
        host = cfg.get("gateway", {}).get("host", "127.0.0.1")
        port = cfg.get("gateway", {}).get("port", 7878)
        disp = host if host != "0.0.0.0" else "<عنوان-جهازك>"
        token = auth.get_or_create_token()
        print(f"\n🔗 رابط بوابة التحكم:\n   http://{disp}:{port}/#token={token}\n")
        return

    # تشغيل البوابة
    from gateway_server import run_gateway
    cfg  = load_config()
    host = "0.0.0.0" if "--network" in args else cfg.get("gateway", {}).get("host", "127.0.0.1")
    port = cfg.get("gateway", {}).get("port", 7878)

    # تحميل HTML لوحة التحكم
    html_path = os.path.join(BASE_DIR, "interfaces", "dashboard", "gateway.html")
    dashboard_html = open(html_path).read() if os.path.exists(html_path) else "<html><body><h1>CoBWeaverClaw Gateway</h1></body></html>"

    run_gateway(host=host, port=port, dashboard_html=dashboard_html)


def cmd_account(args):
    """عرض/استعادة الحساب."""
    from account_manager import AccountManager
    am  = AccountManager()
    acc = am.get_or_create_account()
    print(f"\n🕷️  حساب CoBWeaverClaw")
    print(f"   المعرّف:    {acc['account_id']}")
    print(f"   أُنشئ في:   {acc.get('created_at', '?')[:19]}")
    print(f"   الجهاز:     {acc.get('device_name', '?')}")
    print(f"\n   هذا المعرّف ثابت ولا يُفقد.")
    print(f"   لنسخة احتياطية: python main.py backup\n")


def cmd_backup(args):
    """إنشاء نسخة احتياطية."""
    from account_manager import AccountManager
    am   = AccountManager()
    path = args[0] if args and not args[0].startswith("-") else None
    out  = am.create_backup(path)
    print(f"\n✅ نسخة احتياطية كاملة:")
    print(f"   {out}")
    print(f"\n   تحوي: الحساب + التوكين + الذاكرة + الإعدادات + المفاتيح")
    print(f"   للنقل لجهاز آخر: انسخ الملف ثم: python main.py restore {os.path.basename(out)}\n")


def cmd_restore(args):
    """استعادة نسخة احتياطية."""
    if not args:
        print("\n❌ حدّد ملف النسخة: python main.py restore <file.tar.gz>\n")
        return
    from account_manager import AccountManager
    am = AccountManager()
    try:
        result = am.restore_backup(args[0])
        print(f"\n✅ تمت الاستعادة على هذا الجهاز")
        print(f"   الحساب:    {result['account_id']}")
        print(f"   المُستعاد:  {', '.join(result['restored'])}\n")
    except Exception as e:
        print(f"\n❌ فشلت الاستعادة: {e}\n")


def cmd_restart(args):
    """إعادة تشغيل الوكيل."""
    print("\n🔄 إعادة تشغيل CoBWeaverClaw...")
    python = sys.executable
    os.execv(python, [python, os.path.join(BASE_DIR, "main.py")])


async def cmd_doctor(args):
    """تشخيص."""
    from commands.doctor import Doctor
    cfg = load_config()
    doc = Doctor(cfg)
    result = await doc.run(fix="--fix" in args, full="--full" in args, dry_run="--dry-run" in args)
    print(f"\n🩺 تقرير التشخيص — النتيجة: {result['score']:.0%}\n")
    for check, r in result["results"].items():
        icon = "✅" if r["ok"] else "❌"
        print(f"  {icon} {check:<14} {r['details']}")
    if result.get("fixed"):
        print(f"\n🔧 أُصلح: {', '.join(result['fixed'])}")


def cmd_status(args):
    from gateway_auth import GatewayAuth
    from account_manager import AccountManager
    import platform
    cfg = load_config()
    am  = AccountManager()
    print(f"\n🕷️  CoBWeaverClaw")
    print(f"   الحساب:    {am.get_account_id()}")
    print(f"   المنصة:    {platform.system()}")
    keys = [k for k in os.environ if k.endswith("_API_KEY")]
    print(f"   المفاتيح:  {len(keys)} مُعدّ")
    gw = cfg.get("gateway", {})
    if gw.get("enabled"):
        print(f"   البوابة:   مُفعّلة ({gw.get('host')}:{gw.get('port')})")
    print()


def cmd_help():
    print("""
🕷️  CoBWeaverClaw — الأوامر

  python main.py                    تشغيل CLI
  python main.py setup              معالج الإعداد الكامل
  python main.py setup --models     إعداد النماذج فقط
  python main.py setup --browser    إعداد المتصفح فقط
  python main.py setup --gateway    إعداد البوابة فقط

  python main.py gateway            فتح بوابة التحكم
  python main.py gateway --url      عرض الرابط فقط
  python main.py gateway --network  فتحها للشبكة المحلية
  python main.py gateway --new-token توليد توكين جديد

  python main.py account            عرض الحساب
  python main.py backup [path]      نسخة احتياطية
  python main.py restore <file>     استعادة نسخة
  python main.py restart            إعادة التشغيل

  python main.py doctor [--fix]     تشخيص وإصلاح
  python main.py status             الحالة
""")


def main():
    load_env()
    args = sys.argv[1:]

    if not args and is_first_run():
        print("\n🕷️  أول تشغيل — معالج الإعداد...\n")
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "setup_wizard.py")])
        return

    if not args:
        from core.agent import CoBWeaverClaw
        from interfaces.cli import CLI
        agent = CoBWeaverClaw(load_config())
        asyncio.run(CLI(agent).run())
        return

    cmd = args[0]
    rest = args[1:]

    if cmd in ("setup", "wizard", "configure"):
        import subprocess
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "setup_wizard.py")] + rest)
    elif cmd == "gateway":
        cmd_gateway(rest)
    elif cmd == "account":
        cmd_account(rest)
    elif cmd == "backup":
        cmd_backup(rest)
    elif cmd == "restore":
        cmd_restore(rest)
    elif cmd == "restart":
        cmd_restart(rest)
    elif cmd == "doctor":
        asyncio.run(cmd_doctor(rest))
    elif cmd == "status":
        cmd_status(rest)
    elif cmd == "help":
        cmd_help()
    else:
        # رسالة عادية للوكيل
        from core.agent import CoBWeaverClaw
        agent = CoBWeaverClaw(load_config())
        resp = asyncio.run(agent.process(" ".join(args), "cli_user"))
        print(f"\n{resp}")


if __name__ == "__main__":
    main()
