"""Native background-review adapter for CoBWeaverClaw.

The ported ``background_review.py`` reviewer is wired to the original
upstream agent runtime (``run_agent.AIAgent``, terminal tools, plugin
whitelists) which CoBWeaverClaw does not implement. This module provides
a self-contained equivalent that runs on CoBWeaverClaw's own pieces:

- it replays the just-finished conversation to the agent's ``ModelRouter``
  (``brain.review_complete``) with a focused memory-extraction prompt,
- parses the model's structured decision, and
- persists durable user facts / preferences to the ``BuiltinMemoryProvider``
  files (USER.md / MEMORY.md).

It runs in the daemon thread spawned by ``CoBWeaverClaw._spawn_background_review``
and never touches the live conversation or its prompt cache. Every failure
is swallowed and logged — a broken review must never affect the user turn.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# System prompt for the extraction pass. Intent mirrors the ported
# _MEMORY_REVIEW_PROMPT, but asks for machine-parseable output so a
# tool-less model can still drive durable memory writes.
_REVIEW_SYSTEM = (
    "You are a memory-review assistant. You are given a transcript of a "
    "conversation between a user and their personal AI agent. Decide whether "
    "anything durable about the USER is worth remembering for future sessions.\n\n"
    "Capture ONLY:\n"
    "- user_facts: stable facts about who the user is (name, role, language, "
    "location, projects, tools they use, relationships).\n"
    "- memories: durable preferences and expectations about how the agent "
    "should behave (style, format, tone, workflow, standing instructions).\n\n"
    "Do NOT capture: one-off task details, transient/environment errors, "
    "negative claims about tools, or anything that only matters for today.\n\n"
    "Respond with ONLY a JSON object, no prose, in exactly this shape:\n"
    '{"user_facts": ["..."], "memories": ["..."]}\n'
    "Each item must be a short, self-contained English sentence. If there is "
    "nothing worth saving, return {\"user_facts\": [], \"memories\": []}."
)


def _run_coro_blocking(coro):
    """Run a coroutine to completion regardless of the caller's loop state.

    - No running loop in this thread (the daemon-review case): drive a fresh
      private loop directly.
    - A loop is already running (session-end review invoked from within the
      gateway/CLI event loop): run the coroutine on a dedicated worker thread
      so we never call ``run_until_complete`` against a live loop.
    """
    def _drive() -> Any:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _drive()

    import threading
    box: Dict[str, Any] = {}

    def _worker() -> None:
        box["v"] = _drive()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()
    return box.get("v")


def _format_transcript(messages: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    """Render the message snapshot into a compact role-tagged transcript."""
    lines: List[str] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        content = str(content or "").strip()
        if not content:
            continue
        tag = {"user": "USER", "assistant": "ASSISTANT"}.get(role, role.upper())
        lines.append(f"{tag}: {content}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        # keep the most recent tail — that's where fresh signal lives
        text = "…(earlier turns trimmed)…\n" + text[-max_chars:]
    return text


def _parse_review_json(reply: str) -> Optional[Dict[str, List[str]]]:
    """Extract the first JSON object from the model reply, defensively."""
    if not reply:
        return None
    # Strip code fences if present.
    reply = reply.strip()
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    def _clean(key: str) -> List[str]:
        vals = data.get(key, [])
        if not isinstance(vals, list):
            return []
        out = []
        for v in vals:
            s = str(v).strip()
            if s:
                out.append(s)
        return out

    return {"user_facts": _clean("user_facts"), "memories": _clean("memories")}


def run_review(agent: Any, messages: List[Dict[str, Any]]) -> List[str]:
    """Thread entry point: run one memory-review pass. Returns action list.

    Safe to call from a daemon thread; owns its own event loop for the async
    model call. Never raises — returns [] on any failure.
    """
    try:
        transcript = _format_transcript(messages)
        if not transcript.strip():
            return []
        user_content = (
            "Conversation transcript:\n\n" + transcript +
            "\n\nExtract durable user facts and preferences per your instructions."
        )
        brain = getattr(agent, "brain", None)
        if brain is None or not hasattr(brain, "review_complete"):
            return []

        reply = _run_coro_blocking(
            brain.review_complete(_REVIEW_SYSTEM, user_content)
        )
        parsed = _parse_review_json(reply or "")
        if not parsed:
            return []

        provider = _find_builtin_provider(agent)
        if provider is None:
            return []

        actions: List[str] = []
        n_facts = provider.add_user_facts(parsed["user_facts"]) if parsed["user_facts"] else 0
        n_mem = provider.add_memories(parsed["memories"]) if parsed["memories"] else 0
        if n_facts:
            actions.append(f"User profile: +{n_facts} fact(s)")
        if n_mem:
            actions.append(f"Memory: +{n_mem} preference(s)")
        if actions:
            logger.info("Background review saved: %s", " · ".join(actions))
        return actions
    except Exception as e:
        logger.debug("Background review adapter failed: %s", e)
        return []


def _find_builtin_provider(agent: Any) -> Any:
    """Locate the BuiltinMemoryProvider on the agent's memory manager."""
    mm = getattr(agent, "_memory_manager", None)
    if mm is None:
        return None
    for p in getattr(mm, "_providers", []) or []:
        if getattr(p, "name", "") == "builtin":
            return p
    return None
