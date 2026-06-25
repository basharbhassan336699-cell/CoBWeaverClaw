"""
Monitor Command — Live monitoring of agent status.
agent monitor / agent status --live
"""
import asyncio


class Monitor:
    """Real-time agent monitoring with TUI display."""

    def __init__(self, agent):
        self.agent    = agent
        self.running  = False

    async def start(self, interval: int = 5):
        """Start live monitoring loop."""
        self.running = True
        while self.running:
            status = await self._get_status()
            self._display(status)
            await asyncio.sleep(interval)

    async def _get_status(self) -> dict:
        return {
            "agent":   "running" if self.agent.running else "stopped",
            "platform": self.agent.platform.platform,
            "memory":  "ok",
            "skills":  len(self.agent.router.skills),
        }

    def _display(self, status: dict):
        print(f"\r🕷️  CoBWeaverClaw | {status['agent']} | "
              f"Platform: {status['platform']} | "
              f"Skills: {status['skills']}", end="", flush=True)

    def stop(self):
        self.running = False
