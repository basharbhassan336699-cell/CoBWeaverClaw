#!/usr/bin/env python3
"""
CoBWeaverClaw — Entry Point
Usage:
  python main.py              # Start CLI
  python main.py setup        # Setup wizard
  python main.py doctor       # Diagnose
  python main.py doctor --fix # Fix issues
  python main.py status       # Show status
  python main.py help         # Show help
"""
import asyncio
import sys
import yaml
import os


def load_config() -> dict:
    paths = ["config.yaml", os.path.expanduser("~/.cobweaverclaw/config.yaml")]
    for p in paths:
        if os.path.exists(p):
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}

def is_first_run() -> bool:
    """هل هذا أول تشغيل؟ — لا يوجد مفتاح API ولا إعدادات Telegram."""
    cfg   = load_config()
    brain = cfg.get("brain", {})
    tg    = cfg.get("interfaces", {}).get("telegram", {})
    has_key = any([
        os.environ.get("ANTHROPIC_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("GROQ_API_KEY"),
        brain.get("primary"),
    ])
    has_tg = bool(tg.get("token"))
    env_file = os.path.exists(".env")
    return not (has_key or has_tg or env_file)

def load_env():
    """تحميل متغيرات .env إن وُجد."""
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


async def main():
    load_env()
    config = load_config()
    args   = sys.argv[1:]

    # ── أول تشغيل → تشغيل Wizard تلقائياً ──────────────────
    if not args and is_first_run():
        print("\n🕷️  CoBWeaverClaw — أول تشغيل!")
        print("⟳  جاري تشغيل معالج الإعداد...\n")
        import subprocess
        subprocess.run([sys.executable, "setup_wizard.py"])
        return

    # ── Setup Wizard يدوي ────────────────────────────────────
    if args and args[0] in ("setup", "wizard", "configure", "config"):
        import subprocess
        extra = args[1:]
        subprocess.run([sys.executable, "setup_wizard.py"] + extra)
        return

    from core.agent import CoBWeaverClaw
    agent = CoBWeaverClaw(config)

    if not args:
        from interfaces.cli import CLI
        cli = CLI(agent)
        await cli.run()

    elif args[0] == "doctor":
        from commands.doctor import Doctor
        doc    = Doctor(config)
        result = await doc.run(
            fix     = "--fix"     in args,
            full    = "--full"    in args,
            dry_run = "--dry-run" in args
        )
        score = result["score"]
        print(f"\n🩺 Doctor Report — Score: {score:.0%}\n")
        for check, r in result["results"].items():
            icon = "✅" if r["ok"] else "❌"
            print(f"  {icon} {check:<14} {r['details']}")
        if result.get("fixed"):
            print(f"\n🔧 Fixed: {', '.join(result['fixed'])}")

    elif args[0] == "status":
        from core.platform import PlatformAdapter
        p = PlatformAdapter()
        print(f"\n🕷️  CoBWeaverClaw Status")
        print(f"  Platform:  {p.platform}")
        print(f"  Heartbeat: every {p.get_heartbeat_interval()}s")
        print(f"  Memory:    {p.get_memory_limit()}")
        print(f"  Storage:   {p.get_storage_path()}")
        print(f"  API Keys:  ", end="")
        keys = [k for k in ["ANTHROPIC_API_KEY","OPENAI_API_KEY","GROQ_API_KEY","GEMINI_API_KEY"]
                if os.environ.get(k)]
        print(", ".join(keys) if keys else "None configured")

    elif args[0] == "help":
        print("""
🕷️  CoBWeaverClaw — Commands

  python main.py                    Start CLI (auto-setup on first run)
  python main.py setup              Run setup wizard
  python main.py setup --models     Configure AI models only
  python main.py setup --telegram   Configure Telegram only
  python main.py doctor             Diagnose
  python main.py doctor --fix       Auto-fix issues
  python main.py doctor --fix --full Full repair cycle
  python main.py status             Show status
  python main.py help               This message
        """)

    else:
        response = await agent.process(" ".join(args), "cli_user")
        print(f"\n{response}")


if __name__ == "__main__":
    asyncio.run(main())
