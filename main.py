#!/usr/bin/env python3
"""
CoBWeaverClaw — Entry Point
Usage:
  python main.py              # Start agent
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
                return yaml.safe_load(f)
    return {}


async def main():
    config = load_config()
    args   = sys.argv[1:]

    from core.agent import CoBWeaverClaw
    agent = CoBWeaverClaw(config)

    if not args:
        # Start interactive CLI
        from interfaces.cli import CLI
        cli = CLI(agent)
        await cli.run()

    elif args[0] == "doctor":
        from commands.doctor import Doctor
        doc    = Doctor(config)
        result = await doc.run(
            fix     = "--fix"      in args,
            full    = "--full"     in args,
            dry_run = "--dry-run"  in args
        )
        score = result["score"]
        print(f"\n🩺 Doctor Report — Score: {score:.0%}\n")
        for check, r in result["results"].items():
            icon = "✅" if r["ok"] else "❌"
            print(f"  {icon} {check:<14} {r['details']}")
        if result["fixed"]:
            print(f"\n🔧 Fixed: {', '.join(result['fixed'])}")

    elif args[0] == "status":
        from core.platform import PlatformAdapter
        p = PlatformAdapter()
        print(f"\n🕷️  CoBWeaverClaw Status")
        print(f"  Platform:  {p.platform}")
        print(f"  Heartbeat: every {p.get_heartbeat_interval()}s")
        print(f"  Memory:    {p.get_memory_limit()}")
        print(f"  Storage:   {p.get_storage_path()}")

    elif args[0] == "help":
        print("""
🕷️  CoBWeaverClaw — Commands

  python main.py                    Start CLI
  python main.py doctor             Diagnose
  python main.py doctor --fix       Auto-fix issues
  python main.py doctor --fix --full Full repair cycle
  python main.py doctor --dry-run   Preview fixes
  python main.py status             Show status
  python main.py help               This message
        """)

    else:
        # Process as a direct message
        response = await agent.process(" ".join(args), "cli_user")
        print(f"\n{response}")


if __name__ == "__main__":
    asyncio.run(main())
