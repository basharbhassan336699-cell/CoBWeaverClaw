"""
Telegram Interface — Primary user interface.
agent channels add telegram
"""
import os
import json
import asyncio
import urllib.request


class TelegramBot:
    """
    Telegram bot interface for CoBWeaverClaw.
    Supports commands, buttons, and Thought Stream display.
    """

    def __init__(self, agent, token: str):
        self.agent  = agent
        self.token  = token
        self.offset = 0
        self.base   = f"https://api.telegram.org/bot{token}"

    async def start(self):
        """Start polling for messages."""
        print(f"🕷️  CoBWeaverClaw Telegram Bot started")
        while True:
            updates = await self._get_updates()
            for update in updates:
                await self._handle(update)
            await asyncio.sleep(1)

    async def _get_updates(self) -> list:
        try:
            url = f"{self.base}/getUpdates?offset={self.offset}&timeout=30"
            with urllib.request.urlopen(url, timeout=35) as r:
                data = json.loads(r.read())
            updates = data.get("result", [])
            if updates:
                self.offset = updates[-1]["update_id"] + 1
            return updates
        except Exception:
            return []

    async def _handle(self, update: dict):
        msg = update.get("message", {})
        if not msg:
            return
        text    = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])

        if not text:
            return

        # Show "thinking" indicator
        await self._send(chat_id, "🕷️ ...")

        try:
            response = await self.agent.process(text, user_id)
            await self._send(chat_id, response)
        except Exception as e:
            await self._send(chat_id, f"❌ Error: {str(e)}")

    async def _send(self, chat_id: int, text: str):
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"{self.base}/sendMessage", data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req)
        except Exception:
            pass
