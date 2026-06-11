"""Integration tests run against the real hou module — no mocking here."""
import sys
import pytest


@pytest.fixture(autouse=True)
def mock_hou():
    """Override the parent autouse hou mock with a no-op.

    Without this, tests/conftest.py would replace sys.modules["hou"] with
    the unit-test mock even under hython and the integration tests would
    silently validate the mock instead of the real API.
    """
    yield None


@pytest.fixture(autouse=True)
def fresh_tool_modules(monkeypatch):
    """Evict tool modules so each test imports them against the real hou."""
    prefix = "houdini_side.tools"
    for key in list(sys.modules):
        if key == prefix or key.startswith(prefix + "."):
            monkeypatch.delitem(sys.modules, key, raising=False)
