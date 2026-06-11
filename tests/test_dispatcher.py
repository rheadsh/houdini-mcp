"""
Tests for houdini_side.dispatcher.

dispatch() runs inline in these tests because houdini_side.dispatcher was
imported without a real hou module (_HOU_AVAILABLE is False). The ui_hou
fixture below patches the module to exercise the main-thread branch.
"""
import threading
import time
import types

import pytest
from houdini_side.dispatcher import dispatch, ok, err, _dispatch_timeout


# ---------------------------------------------------------------------------
# dispatch() tests
# ---------------------------------------------------------------------------

def test_dispatch_runs_callable():
    """dispatch() executes the callable and returns its return value."""
    result = dispatch(lambda: 42)
    assert result == 42


def test_dispatch_annotates_success_response():
    result = dispatch(lambda: ok({"value": 42}), label="unit_tool")
    assert result["success"] is True
    assert result["meta"]["tool"] == "unit_tool"
    assert isinstance(result["meta"]["duration_ms"], float)


def test_dispatch_propagates_exception():
    """dispatch() re-raises any exception raised inside the callable."""
    def boom():
        raise ValueError("something went wrong")

    with pytest.raises(ValueError, match="something went wrong"):
        dispatch(boom)


# ---------------------------------------------------------------------------
# ok() tests
# ---------------------------------------------------------------------------

def test_ok_basic():
    """ok() returns a success dict with an empty warnings list by default."""
    response = ok({"key": "value"})
    assert response == {"success": True, "data": {"key": "value"}, "warnings": []}


def test_ok_with_warnings():
    """ok() includes custom warnings when provided."""
    response = ok("some data", warnings=["w1", "w2"])
    assert response["success"] is True
    assert response["data"] == "some data"
    assert response["warnings"] == ["w1", "w2"]


# ---------------------------------------------------------------------------
# err() tests
# ---------------------------------------------------------------------------

def test_err_basic():
    """err() returns a failure dict with the exception message."""
    exc = RuntimeError("it broke")
    response = err(exc)
    assert response["success"] is False
    assert response["error"] == "it broke"


def test_err_type_name():
    """err() sets error_type to the exception class name."""
    exc = TypeError("bad type")
    response = err(exc)
    assert response["error_type"] == "TypeError"


# ---------------------------------------------------------------------------
# Main-thread branch (postEventCallback)
# ---------------------------------------------------------------------------

@pytest.fixture
def ui_hou(monkeypatch):
    """Patch the dispatcher so it believes a Houdini UI main loop exists.

    Returns the list of callbacks posted via hou.postEventCallback; the test
    plays the role of Houdini's main thread by invoking them.
    """
    import houdini_side.dispatcher as dispatcher
    callbacks = []
    hou_mock = types.SimpleNamespace(
        isUIAvailable=lambda: True,
        postEventCallback=callbacks.append,
    )
    monkeypatch.setattr(dispatcher, "hou", hou_mock)
    monkeypatch.setattr(dispatcher, "_HOU_AVAILABLE", True)
    return callbacks


def _drain_when_posted(callbacks, timeout=5.0):
    """Wait until dispatch() posts its callback, then run it."""
    deadline = time.monotonic() + timeout
    while not callbacks and time.monotonic() < deadline:
        time.sleep(0.005)
    assert callbacks, "dispatch() never posted a callback"
    callbacks[0]()


def test_dispatch_runs_fn_via_posted_callback(ui_hou):
    results = []
    worker = threading.Thread(
        target=lambda: results.append(dispatch(lambda: ok({"x": 1}), label="ui_tool"))
    )
    worker.start()
    _drain_when_posted(ui_hou)
    worker.join(timeout=5.0)
    assert not worker.is_alive()
    assert results[0]["success"] is True
    assert results[0]["meta"]["tool"] == "ui_tool"


def test_dispatch_propagates_exception_from_callback(ui_hou):
    def boom():
        raise ValueError("inside callback")

    raised = []

    def run():
        try:
            dispatch(boom, label="boom_tool")
        except Exception as e:
            raised.append(e)

    worker = threading.Thread(target=run)
    worker.start()
    _drain_when_posted(ui_hou)
    worker.join(timeout=5.0)
    assert isinstance(raised[0], ValueError)


def test_dispatch_times_out_when_callback_never_runs(ui_hou, monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "0.1")
    with pytest.raises(TimeoutError, match="slow_tool"):
        dispatch(lambda: 1, label="slow_tool")


def test_late_callback_after_timeout_skips_fn(ui_hou, monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "0.1")
    calls = []
    with pytest.raises(TimeoutError):
        dispatch(lambda: calls.append(1), label="late_tool")
    # Houdini drains its event queue after the MCP side already gave up:
    # the cancelled flag must prevent fn() from running with side effects.
    ui_hou[0]()
    assert calls == []


# ---------------------------------------------------------------------------
# _dispatch_timeout() env parsing
# ---------------------------------------------------------------------------

def test_dispatch_timeout_default(monkeypatch):
    monkeypatch.delenv("HOUDINI_MCP_DISPATCH_TIMEOUT", raising=False)
    assert _dispatch_timeout() == 30.0


def test_dispatch_timeout_global_env(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "2.5")
    assert _dispatch_timeout() == 2.5


def test_dispatch_timeout_per_tool_override(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "2.5")
    monkeypatch.setenv("HOUDINI_MCP_TIMEOUT_ROP_RENDER", "600")
    assert _dispatch_timeout("rop_render") == 600.0
    assert _dispatch_timeout("other_tool") == 2.5


def test_dispatch_timeout_invalid_value_falls_back(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "garbage")
    assert _dispatch_timeout() == 30.0


def test_dispatch_timeout_clamps_to_minimum(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_DISPATCH_TIMEOUT", "0")
    assert _dispatch_timeout() == 0.1
