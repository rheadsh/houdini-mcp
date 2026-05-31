"""
Thread-safe dispatcher for hou.* calls.

Houdini requires all hou.* calls on the main thread.
When the MCP server thread needs to call hou.*, it posts a callback
via hou.postEventCallback() and waits on a threading.Event.

In headless/test contexts (hou.isUIAvailable() is False),
the callable is executed inline on the calling thread.
"""
import threading
import traceback

try:
    import hou
    _HOU_AVAILABLE = True
except ImportError:
    _HOU_AVAILABLE = False


def dispatch(fn):
    """
    Execute fn() on Houdini's main thread and return its result.
    Raises any exception fn() raises.
    """
    if not _HOU_AVAILABLE or not hou.isUIAvailable():
        return fn()

    result_holder = [None]
    exc_holder = [None]
    done = threading.Event()

    def _callback():
        try:
            result_holder[0] = fn()
        except Exception as e:
            exc_holder[0] = e
        finally:
            done.set()

    hou.postEventCallback(_callback)
    done.wait(timeout=30.0)

    if not done.is_set():
        raise TimeoutError("Houdini main thread dispatch timed out after 30s")
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
