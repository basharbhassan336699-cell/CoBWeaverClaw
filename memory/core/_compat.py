"""Compatibility stubs for the ported memory system (no external deps)."""
from contextlib import contextmanager

# مجموعة أدوات النواة (كانت toolsets._*_CORE_TOOLS في المصدر)
_COBWEAVERCLAW_CORE_TOOLS = set()


@contextmanager
def thread_scoped_silence(*args, **kwargs):
    yield


def load_config(*args, **kwargs):
    return {}
