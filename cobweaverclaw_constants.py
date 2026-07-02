"""Constants/paths for CoBWeaverClaw memory system (renamed from external source)."""
from pathlib import Path


def get_config_path() -> Path:
    return Path.home() / ".cobweaverclaw"


def get_skills_dir() -> Path:
    return Path.home() / ".cobweaverclaw" / "skills"


def is_termux() -> bool:
    return Path("/data/data/com.termux").exists()


def get_cobweaverclaw_home() -> Path:
    return Path.home() / ".cobweaverclaw"


def display_cobweaverclaw_home() -> str:
    return "~/.cobweaverclaw"
