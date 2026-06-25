"""
Platform Adapter — Detects device and adapts behavior accordingly.
"""
import os
import sys
import platform


class PlatformAdapter:
    """
    Detects the current platform and provides
    platform-specific configurations.
    """

    PLATFORMS = {
        "android": {"heartbeat": 300, "memory_limit": "512MB", "model": "fast"},
        "ios":     {"heartbeat": 300, "memory_limit": "512MB", "model": "fast"},
        "raspi":   {"heartbeat": 900, "memory_limit": "256MB", "model": "local"},
        "linux":   {"heartbeat": 60,  "memory_limit": "2GB",   "model": "primary"},
        "macos":   {"heartbeat": 60,  "memory_limit": "2GB",   "model": "primary"},
        "windows": {"heartbeat": 60,  "memory_limit": "2GB",   "model": "primary"},
    }

    def __init__(self):
        self.platform = self._detect()

    def _detect(self) -> str:
        if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
            return "android"
        if sys.platform == "darwin":
            return "macos"
        if sys.platform == "win32":
            return "windows"
        try:
            with open("/proc/cpuinfo") as f:
                if "Raspberry" in f.read():
                    return "raspi"
        except Exception:
            pass
        if os.path.exists("/system/xbin/bash"):
            return "ios"
        return "linux"

    def get_heartbeat_interval(self) -> int:
        return self.PLATFORMS[self.platform]["heartbeat"]

    def get_memory_limit(self) -> str:
        return self.PLATFORMS[self.platform]["memory_limit"]

    def get_preferred_model(self) -> str:
        return self.PLATFORMS[self.platform]["model"]

    def get_storage_path(self) -> str:
        paths = {
            "android": os.path.expanduser("~/.cobweaverclaw"),
            "ios":     os.path.expanduser("~/.cobweaverclaw"),
            "linux":   os.path.expanduser("~/.cobweaverclaw"),
            "macos":   os.path.expanduser("~/.cobweaverclaw"),
            "raspi":   os.path.expanduser("~/.cobweaverclaw"),
            "windows": os.path.join(os.environ.get("APPDATA","~"), "CoBWeaverClaw"),
        }
        return paths[self.platform]
