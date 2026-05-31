# tests/test_session.py
import pytest


def test_session_info_returns_version(mock_hou):
    mock_hou.applicationVersionString = lambda: "20.5.000"
    mock_hou.userName = lambda: "artist"
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is True
    assert "20.5" in result["data"]["version"]
    assert result["data"]["user"] == "artist"


def test_hip_info_no_unsaved(mock_hou):
    mock_hou.hipFile.path = lambda: "/projects/test.hip"
    mock_hou.hipFile.hasUnsavedChanges = lambda: False
    from houdini_side.tools.session import _hip_info
    result = _hip_info()
    assert result["success"] is True
    assert result["data"]["path"] == "/projects/test.hip"
    assert result["data"]["has_unsaved_changes"] is False


def test_hip_save_calls_hipfile(mock_hou):
    saved = []
    mock_hou.hipFile.save = lambda path=None: saved.append(path)
    mock_hou.hipFile.path = lambda: "/projects/test.hip"
    from houdini_side.tools.session import _hip_save
    result = _hip_save(None)
    assert result["success"] is True
    assert saved == [None]


def test_hip_load_calls_hipfile(mock_hou):
    loaded = []
    mock_hou.hipFile.load = lambda path, suppress_save_prompt=True: loaded.append(path)
    mock_hou.hipFile.path = lambda: "/projects/scene.hip"
    from houdini_side.tools.session import _hip_load
    result = _hip_load("/projects/scene.hip")
    assert result["success"] is True
    assert loaded == ["/projects/scene.hip"]


def test_hip_new_clears_scene(mock_hou):
    cleared = []
    mock_hou.hipFile.clear = lambda suppress_save_prompt=True: cleared.append(True)
    mock_hou.hipFile.path = lambda: "/tmp/untitled.hip"
    from houdini_side.tools.session import _hip_new
    result = _hip_new()
    assert result["success"] is True
    assert cleared == [True]


def test_hip_merge_calls_hipfile(mock_hou):
    merged = []
    mock_hou.hipFile.merge = lambda path: merged.append(path)
    from houdini_side.tools.session import _hip_merge
    result = _hip_merge("/projects/other.hip")
    assert result["success"] is True
    assert merged == ["/projects/other.hip"]


def test_session_info_error_returns_err(mock_hou):
    mock_hou.applicationVersionString = lambda: (_ for _ in ()).throw(RuntimeError("hou error"))
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is False
    assert "error" in result
