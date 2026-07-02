"""Compatibility shims for ported external memory providers (Phase 4).

The upstream providers imported a handful of helpers from the original
agent's CLI/runtime modules (config loader, curses setup prompts, async
scheduling, message flattening). Those modules don't exist in
CoBWeaverClaw, so this module provides lightweight, dependency-free
equivalents. Import paths in the ported plugins were rewritten to point
here; the provider logic itself is unchanged.

Most of these are only exercised by a provider's interactive `setup`/CLI
flow, which never runs unless the provider's pip package is installed and
the user opts in. They are implemented to behave sanely (or degrade to a
safe no-op) rather than to reproduce the original TUI.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ── config helpers (config loader shim) ───────────────────────────────
def _config_file() -> Path:
    return Path.home() / ".cobweaverclaw" / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load config.yaml if present, else empty dict."""
    p = _config_file()
    try:
        if p.exists():
            import yaml
            with open(p, encoding="utf-8-sig") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Persist config.yaml (best-effort)."""
    p = _config_file()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
    except Exception:
        pass


def cfg_get(config: Optional[Dict[str, Any]], *keys: str, default: Any = None) -> Any:
    """Nested lookup: cfg_get(cfg, 'memory', 'provider')."""
    node: Any = config or {}
    for k in keys:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return default
    return node


# ── misc utils (was the top-level `utils` module) ─────────────────────
def atomic_json_write(path: Any, data: Any, **_kw: Any) -> None:
    """Write JSON atomically via a temp file + os.replace."""
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise


def env_var_enabled(name: str, default: bool = False) -> bool:
    """True if env var is set to a truthy value (1/true/yes/on)."""
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ── message helpers (was agent.message_content) ───────────────────────
def flatten_message_text(content: Any) -> str:
    """Flatten OpenAI-style message content into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    if isinstance(content, dict):
        return str(content.get("text", ""))
    return str(content)


# ── async helpers (was agent.async_utils) ─────────────────────────────
def safe_schedule_threadsafe(loop: Any, coro: Any) -> Any:
    """Schedule a coroutine on a loop from another thread, best-effort."""
    try:
        import asyncio
        if loop is not None and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception:
        pass
    return None


# ── state helpers (SQLite WAL shim) ───────────────────────────────────
def apply_wal_with_fallback(conn: Any, *_a: Any, **_kw: Any) -> None:
    """Enable SQLite WAL mode, ignoring failures (e.g. on network FS)."""
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass


# ── secret / profile helpers ──────────────────────────────────────────
def masked_secret_prompt(prompt: str = "", **_kw: Any) -> str:
    """Prompt for a secret without echo; empty string if unavailable."""
    try:
        import getpass
        return getpass.getpass(prompt)
    except Exception:
        return ""


def _get_default_cobweaverclaw_home() -> Path:
    return Path.home() / ".cobweaverclaw"


def get_active_profile_name() -> str:
    return os.environ.get("COBWEAVERCLAW_PROFILE", "default")


def list_profiles() -> List[str]:
    return [get_active_profile_name()]


# ── curses / interactive setup helpers ────────────────────────────────
# These back the providers' optional interactive `setup` flows. In a
# headless/non-TUI context they degrade to no-ops or simple input().
_CANCELLED = object()


def curses_radiolist(*_a: Any, **_kw: Any) -> Any:
    return _CANCELLED


def _curses_select(*_a: Any, **_kw: Any) -> Any:
    return _CANCELLED


def _print_cancelled_setup(*_a: Any, **_kw: Any) -> None:
    print("Setup cancelled.")


def _prompt(message: str = "", default: str = "", **_kw: Any) -> str:
    try:
        val = input(f"{message} " if message else "").strip()
        return val or default
    except Exception:
        return default


def _write_env_vars(env: Dict[str, str], **_kw: Any) -> None:
    """Append env vars to ~/.cobweaverclaw/.env (best-effort)."""
    try:
        p = Path.home() / ".cobweaverclaw" / ".env"
        p.parent.mkdir(parents=True, exist_ok=True)
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        lines = [existing] if existing else []
        for k, v in (env or {}).items():
            lines.append(f"{k}={v}")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def cmd_setup_provider(*_a: Any, **_kw: Any) -> int:
    """Non-interactive fallback for a provider's setup command."""
    print("Interactive provider setup is not available in this build. "
          "Set the provider's API key via environment variables instead.")
    return 1
