"""Compatibility stubs for the ported memory system (no external deps)."""
from contextlib import contextmanager

# مجموعة أدوات النواة (كانت toolsets._*_CORE_TOOLS في المصدر)
_COBWEAVERCLAW_CORE_TOOLS = set()


@contextmanager
def thread_scoped_silence(*args, **kwargs):
    yield


def load_config(*args, **kwargs):
    return {}


# ── util stubs (renamed from external utils / cli helpers) ──
import json as _json, os as _os, tempfile as _tempfile, random as _random
from urllib.parse import urlparse as _urlparse


def atomic_json_write(path, data):
    d = _os.path.dirname(str(path)) or "."
    _os.makedirs(d, exist_ok=True)
    fd, tmp = _tempfile.mkstemp(dir=d)
    with _os.fdopen(fd, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)
    _os.replace(tmp, str(path))


def base_url_hostname(url):
    try:
        return (_urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def base_url_host_matches(a, b):
    return base_url_hostname(a) == base_url_hostname(b)


def jittered_backoff(attempt=0, base=1.0, cap=30.0):
    return min(cap, base * (2 ** max(0, attempt))) * (0.5 + _random.random() * 0.5)


def load_cobweaverclaw_dotenv(*args, **kwargs):
    env = _os.path.expanduser("~/.cobweaverclaw/.env")
    if _os.path.exists(env):
        for line in open(env, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                _os.environ.setdefault(k.strip(), v.strip())
    return None
