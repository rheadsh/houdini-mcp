"""
Tests for houdini_side.dispatcher.

The mock_hou autouse fixture (conftest.py) patches sys.modules["hou"] with a
mock that has isUIAvailable = lambda: False, so dispatch() always runs inline.
"""
import pytest
from houdini_side.dispatcher import dispatch, ok, err


# ---------------------------------------------------------------------------
# dispatch() tests
# ---------------------------------------------------------------------------

def test_dispatch_runs_callable():
    """dispatch() executes the callable and returns its return value."""
    result = dispatch(lambda: 42)
    assert result == 42


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
