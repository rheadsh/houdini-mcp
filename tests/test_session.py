# tests/test_session.py
import os
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


def test_hip_save_calls_hipfile_with_none(mock_hou):
    """hip_save(None) skips path validation and saves to current path."""
    saved = []
    mock_hou.hipFile.save = lambda path=None: saved.append(path)
    mock_hou.hipFile.path = lambda: "/projects/test.hip"
    from houdini_side.tools.session import _hip_save
    result = _hip_save(None)
    assert result["success"] is True
    assert saved == [None]


def test_hip_save_with_valid_path(mock_hou, monkeypatch):
    """hip_save with an explicit .hip path validates and saves."""
    saved = []
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    mock_hou.hipFile.save = lambda path=None: saved.append(path)
    mock_hou.hipFile.path = lambda: "/projects/test.hip"
    from houdini_side.tools.session import _hip_save
    result = _hip_save("/projects/test.hip")
    assert result["success"] is True
    assert len(saved) == 1
    assert saved[0].endswith(".hip")


def test_hip_save_rejects_non_hip_extension(mock_hou):
    """hip_save rejects paths that don't end in .hip/.hiplc/.hipnc."""
    from houdini_side.tools.session import _hip_save
    result = _hip_save("/projects/scene.py")
    assert result["success"] is False
    assert "extension" in result["error"].lower() or "invalid" in result["error"].lower()


def test_hip_load_calls_hipfile(mock_hou, monkeypatch):
    """hip_load validates the path and calls hou.hipFile.load."""
    loaded = []
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    mock_hou.hipFile.load = lambda path, suppress_save_prompt=True: loaded.append(path)
    mock_hou.hipFile.path = lambda: "/projects/scene.hip"
    from houdini_side.tools.session import _hip_load
    result = _hip_load("/projects/scene.hip")
    assert result["success"] is True
    assert len(loaded) == 1
    assert loaded[0].endswith(".hip")


def test_hip_load_rejects_missing_file(mock_hou):
    """hip_load returns error when file does not exist."""
    from houdini_side.tools.session import _hip_load
    result = _hip_load("/tmp/nonexistent.hip")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_hip_load_rejects_non_hip_extension(mock_hou, monkeypatch):
    """hip_load rejects files without .hip* extension."""
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    from houdini_side.tools.session import _hip_load
    result = _hip_load("/projects/scene.abc")
    assert result["success"] is False


def test_hip_new_clears_scene(mock_hou):
    cleared = []
    mock_hou.hipFile.clear = lambda suppress_save_prompt=True: cleared.append(True)
    mock_hou.hipFile.path = lambda: "/tmp/untitled.hip"
    from houdini_side.tools.session import _hip_new
    result = _hip_new()
    assert result["success"] is True
    assert cleared == [True]


def test_hip_merge_calls_hipfile(mock_hou, monkeypatch):
    """hip_merge validates and merges a .hip file."""
    merged = []
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    mock_hou.hipFile.merge = lambda path: merged.append(path)
    from houdini_side.tools.session import _hip_merge
    result = _hip_merge("/projects/other.hip")
    assert result["success"] is True
    assert len(merged) == 1
    assert merged[0].endswith(".hip")


def test_hip_merge_rejects_non_hip(mock_hou, monkeypatch):
    """hip_merge rejects non-.hip* files."""
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    from houdini_side.tools.session import _hip_merge
    result = _hip_merge("/projects/scene.obj")
    assert result["success"] is False


def test_session_info_error_returns_err(mock_hou):
    mock_hou.applicationVersionString = lambda: (_ for _ in ()).throw(RuntimeError("hou error"))
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is False
    assert "error" in result


def test_validate_hip_path_traversal_blocked(monkeypatch):
    """Path traversal outside project root is blocked."""
    import os
    monkeypatch.setenv("HOUDINI_MCP_PROJECT_ROOT", "/projects")
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    from houdini_side.tools.session import _validate_hip_path
    import pytest
    with pytest.raises(ValueError, match="outside HOUDINI_MCP_PROJECT_ROOT"):
        _validate_hip_path("/projects/../etc/passwd.hip")


def test_validate_hip_path_subdirectory_allowed(monkeypatch):
    """Paths inside project root are allowed."""
    import os
    monkeypatch.setenv("HOUDINI_MCP_PROJECT_ROOT", "/projects")
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    from houdini_side.tools.session import _validate_hip_path
    result = _validate_hip_path("/projects/shots/s001.hip")
    assert result.endswith(".hip")


def test_validate_hip_path_no_root_allows_any(monkeypatch):
    """When HOUDINI_MCP_PROJECT_ROOT not set, any .hip path is allowed."""
    import os
    monkeypatch.delenv("HOUDINI_MCP_PROJECT_ROOT", raising=False)
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    from houdini_side.tools.session import _validate_hip_path
    result = _validate_hip_path("/etc/test.hip")
    assert result.endswith(".hip")
