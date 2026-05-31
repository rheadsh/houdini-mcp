"""
Thread-safe dispatcher for hou.* calls.

Houdini requires all hou.* calls on the main thread.
When the MCP server thread needs to call hou.*, it posts a callback
via hou.postEventCallback() and waits on a threading.Event.

In headless/test contexts (hou.isUIAvailable() is False),
the callable is executed inline on the calling thread.
"""
import threading
import time
import os
from typing import Optional, Any

try:
    import hou as hou  # type: ignore[import-untyped]  # noqa: PLC0414
    _HOU_AVAILABLE = True
except ImportError:
    hou = None  # type: ignore[assignment]
    _HOU_AVAILABLE = False


def _dispatch_timeout(label: str = "") -> float:
    specific_name = f"HOUDINI_MCP_TIMEOUT_{label.upper()}" if label else ""
    raw = os.environ.get(specific_name) if specific_name else None
    raw = raw or os.environ.get("HOUDINI_MCP_DISPATCH_TIMEOUT", "30")
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = 30.0
    return max(timeout, 0.1)


def _annotate_response(response, label: str, elapsed_ms: float):
    if isinstance(response, dict) and response.get("success") is True:
        response.setdefault("meta", {})
        response["meta"].update({
            "tool": label or None,
            "duration_ms": round(elapsed_ms, 3),
        })
    return response


def dispatch(fn, label: str = ""):
    """
    Execute fn() on Houdini's main thread and return its result.
    Raises any exception fn() raises.

    label: optional description used in TimeoutError messages for diagnostics.
    """
    started = time.perf_counter()
    _has_post_callback = _HOU_AVAILABLE and hou is not None and hasattr(hou, 'postEventCallback')
    if not _HOU_AVAILABLE or hou is None or not hou.isUIAvailable() or not _has_post_callback:
        response = fn()
        return _annotate_response(
            response, label, (time.perf_counter() - started) * 1000.0
        )

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
    timeout = _dispatch_timeout(label)
    timed_out = not done.wait(timeout=timeout)

    if timed_out:
        cancelled.set()
        tool_name = label or getattr(fn, "__name__", repr(fn))
        raise TimeoutError(
            f"Houdini main thread dispatch timed out after {timeout:g}s (tool: {tool_name})"
        )
    if exc_holder[0] is not None:
        raise exc_holder[0]
    return _annotate_response(
        result_holder[0], label, (time.perf_counter() - started) * 1000.0
    )


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
