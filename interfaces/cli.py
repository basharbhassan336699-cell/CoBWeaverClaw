"""
CLI Interface — Command-line interface for developers.
"""
import asyncio
import sys


class CLI:
    """Terminal interface with full command support."""

    COMMANDS = {
        "scan":     "Discover platform and environment",
        "doctor":   "Diagnose and fix issues",
        "status":   "Show agent status",
        "memory":   "Memory management",
        "models":   "Model management",
        "skills":   "Skill management",
        "learn":    "Trigger self-learning",
        "backup":   "Backup agent data",
        "migrate":  "Migrate from OpenClaw/Hermes",
        "help":     "Show this help",
    }

    def __init__(self, agent):
        self.agent = agent

    async def run(self):
        """Start interactive CLI session."""
        print("🕷️  CoBWeaverClaw CLI | type 'help' for commands")
        while True:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("Goodbye! 🕷️")
                    break
                await self._handle(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye! 🕷️")
                break

    async def _handle(self, command: str):
        parts = command.split()
        cmd   = parts[0].lower()

        if cmd == "help":
            for c, desc in self.COMMANDS.items():
                print(f"  agent {c:<12} {desc}")
        elif cmd == "doctor":
            from commands.doctor import Doctor
            doc    = Doctor(self.agent.config)
            fix    = "--fix" in parts
            full   = "--full" in parts
            dry    = "--dry-run" in parts
            result = await doc.run(fix=fix, full=full, dry_run=dry)
            score  = result["score"]
            print(f"\n🩺 Doctor Report — Score: {score:.0%}")
            for check, r in result["results"].items():
                icon = "✅" if r["ok"] else "❌"
                print(f"  {icon} {check:<12} {r['details']}")
            if result["fixed"]:
                print(f"\n🔧 Fixed: {', '.join(result['fixed'])}")
        else:
            response = await self.agent.process(command, "cli_user")
            print(f"\n{response}")
