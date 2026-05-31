"""
Thread-safe dispatcher for hou.* calls.

Houdini requires all hou.* calls on the main thread.
When the MCP server thread needs to call hou.*, it posts a callback
via hou.postEventCallback() and waits on a threading.Event.

In headless/test contexts (hou.isUIAvailable() is False),
the callable is executed inline on the calling thread.
"""
import threading
from typing import Optional, Any

try:
    import hou as hou  # type: ignore[import-untyped]  # noqa: PLC0414
    _HOU_AVAILABLE = True
except ImportError:
    hou = None  # type: ignore[assignment]
    _HOU_AVAILABLE = False


def dispatch(fn, label: str = ""):
    """
    Execute fn() on Houdini's main thread and return its result.
    Raises any exception fn() raises.

    label: optional description used in TimeoutError messages for diagnostics.
    """
    if not _HOU_AVAILABLE or hou is None or not hou.isUIAvailable():
        return fn()

    result_holder: list[Any] = [None]
    exc_holder: list[Optional[Exception]] = [None]
    done = threading.Event()
    cancelled = threading.Event()  # set on timeout so late callbacks skip fn()

    def _callback():
        if cancelled.is_set():
            return  # timed out — discard; do NOT call fn() to avoid side effects
        try:
            result_holder[0] = fn()
        except Exception as e:
            exc_holder[0] = e
        finally:
            done.set()

    hou.postEventCallback(_callback)
    timed_out = not done.wait(timeout=30.0)

    if timed_out:
        cancelled.set()
        tool_name = label or getattr(fn, "__name__", repr(fn))
        raise TimeoutError(
            f"Houdini main thread dispatch timed out after 30s (tool: {tool_name})"
        )
    if exc_holder[0] is not None:
        raise exc_holder[0]
    return result_holder[0]


def ok(data, warnings=None):
    """Convenience: build a success response dict."""
    return {"success": True, "data": data, "warnings": warnings or []}


def err(e):
    """Convenience: build an error response dict from an exception."""
    return {
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__,
    }
