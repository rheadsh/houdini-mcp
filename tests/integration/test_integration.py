"""
Integration tests requiring a real Houdini installation.

Run with:
    hython -m pytest tests/integration -v

These tests are automatically skipped when run under standard Python.
They verify that the tool implementations work against the real hou.* API,
not just the mock.
"""
from typing import Any, cast

import pytest

# The real hou module is only importable inside Houdini/hython.
try:
    import hou as _hou
    _HOU_AVAILABLE = True
except ImportError:
    _hou = None
    _HOU_AVAILABLE = False

hou = cast(Any, _hou)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _HOU_AVAILABLE,
        reason="hou module not available — run with hython"
    ),
]


@pytest.fixture(autouse=True)
def fresh_scene():
    """Start each integration test with an empty hip scene."""
    if _HOU_AVAILABLE:
        hou.hipFile.clear(suppress_save_prompt=True)
    yield
    if _HOU_AVAILABLE:
        hou.hipFile.clear(suppress_save_prompt=True)


# ---- Session tools ----

def test_integration_session_info():
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is True
    assert "version" in result["data"]
    assert result["data"]["version"]  # non-empty string
    assert "user" in result["data"]


def test_integration_hip_info():
    from houdini_side.tools.session import _hip_info
    result = _hip_info()
    assert result["success"] is True
    assert "path" in result["data"]
    assert "has_unsaved_changes" in result["data"]


# ---- Node tools ----

def test_integration_node_create_and_delete():
    from houdini_side.tools.nodes import _node_create, _node_delete, _node_get
    # Create a geo node under /obj
    result = _node_create("/obj", "geo", "mcp_test_geo")
    assert result["success"] is True
    node_path = result["data"]["path"]
    assert node_path == "/obj/mcp_test_geo"

    # Verify it exists
    get_result = _node_get("/obj/mcp_test_geo")
    assert get_result["success"] is True
    assert get_result["data"]["type"] == "geo"

    # Delete it
    del_result = _node_delete("/obj/mcp_test_geo")
    assert del_result["success"] is True
    assert hou.node("/obj/mcp_test_geo") is None


def test_integration_node_connect():
    from houdini_side.tools.nodes import _node_create, _node_connect, _node_get
    geo = hou.node("/obj").createNode("geo", "test_net")
    box = geo.createNode("box", "box1")
    copy = geo.createNode("copytopoints", "copy1")

    result = _node_connect(box.path(), 0, copy.path(), 0)
    assert result["success"] is True

    # Verify connection
    get = _node_get(copy.path())
    assert get["data"]["inputs"][0]["node"] == box.path()
    geo.destroy()


# ---- Parameter tools ----

def test_integration_parm_get_and_set():
    from houdini_side.tools.parameters import _parm_get, _parm_set
    geo = hou.node("/obj").createNode("geo", "parm_test")
    box = geo.createNode("box", "box1")

    # Set sizex to 5.0
    set_result = _parm_set(box.path(), "sizex", 5.0)
    assert set_result["success"] is True

    # Read it back
    get_result = _parm_get(box.path(), "sizex")
    assert get_result["success"] is True
    assert abs(get_result["data"]["value"] - 5.0) < 0.001
    geo.destroy()


def test_integration_parm_get_all():
    from houdini_side.tools.parameters import _parm_get_all
    geo = hou.node("/obj").createNode("geo", "pall_test")
    box = geo.createNode("box", "box1")
    result = _parm_get_all(box.path())
    assert result["success"] is True
    assert "sizex" in result["data"]["parameters"]
    geo.destroy()


# ---- Geometry tools ----

def test_integration_geo_info():
    from houdini_side.tools.geometry import _geo_info
    geo = hou.node("/obj").createNode("geo", "geo_test")
    box = geo.createNode("box", "box1")
    # Force cook
    box.cook(force=True)
    result = _geo_info(box.path())
    assert result["success"] is True
    assert result["data"]["point_count"] > 0
    assert result["data"]["prim_count"] > 0
    geo.destroy()


def test_integration_geo_bbox():
    from houdini_side.tools.geometry import _geo_bbox
    geo = hou.node("/obj").createNode("geo", "bbox_test")
    box = geo.createNode("box", "box1")
    box.cook(force=True)
    result = _geo_bbox(box.path())
    assert result["success"] is True
    # Default box is 1x1x1 centered at origin
    bbox = result["data"]
    assert len(bbox["min"]) == 3
    assert len(bbox["max"]) == 3
    assert bbox["size"][0] > 0
    geo.destroy()


# ---- Animation tools ----

def test_integration_time_get_and_set():
    from houdini_side.tools.animation import _time_get, _time_set
    original = hou.frame()
    _time_set(42.0)
    result = _time_get()
    assert result["success"] is True
    assert abs(result["data"]["frame"] - 42.0) < 0.001
    hou.setFrame(original)  # restore


def test_integration_frame_range():
    from houdini_side.tools.animation import _frame_range_get, _frame_range_set
    _frame_range_set(1.0, 120.0)
    result = _frame_range_get()
    assert result["success"] is True
    assert result["data"]["start"] == 1.0
    assert result["data"]["end"] == 120.0
