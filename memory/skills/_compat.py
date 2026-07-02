"""Subprocess platform compat (renamed from external CLI helper)."""
import os
IS_WINDOWS = os.name == "nt"


def windows_hide_flags():
    return 0
