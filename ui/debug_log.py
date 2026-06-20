"""
Small global switch for development-only CLI logs.
"""

_debug_enabled = False


def set_debug_enabled(enabled):
    global _debug_enabled
    _debug_enabled = bool(enabled)


def is_debug_enabled():
    return _debug_enabled


def debug_print(*args, **kwargs):
    if _debug_enabled:
        print(*args, **kwargs)
