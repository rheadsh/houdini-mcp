"""Tests for the shared helpers in houdini_side.tools.common."""
import json
import os
import types

import pytest


# ---------------------------------------------------------------------------
# resolve_output_path
# ---------------------------------------------------------------------------

def test_resolve_output_path_creates_parent_dirs(tmp_path, mock_hou):
    from houdini_side.tools.common import resolve_output_path
    target = tmp_path / "renders" / "out.bgeo"
    result = resolve_output_path(mock_hou, str(target), (".bgeo",))
    assert result.endswith("out.bgeo")
    assert (tmp_path / "renders").is_dir()


def test_resolve_output_path_rejects_bad_extension(tmp_path, mock_hou):
    from houdini_side.tools.common import resolve_output_path
    with pytest.raises(ValueError, match="extension"):
        resolve_output_path(mock_hou, str(tmp_path / "out.exe"), (".bgeo",))


def test_resolve_output_path_rejects_empty(mock_hou):
    from houdini_side.tools.common import resolve_output_path
    with pytest.raises(ValueError):
        resolve_output_path(mock_hou, "")
    with pytest.raises(ValueError):
        resolve_output_path(mock_hou, "   ")


def test_resolve_output_path_expands_hou_variables(tmp_path, mock_hou):
    from houdini_side.tools.common import resolve_output_path
    mock_hou.expandString = lambda s: s.replace("$HIP", str(tmp_path))
    result = resolve_output_path(mock_hou, "$HIP/geo/out.bgeo", (".bgeo",))
    assert result == os.path.realpath(str(tmp_path / "geo" / "out.bgeo"))


def test_resolve_output_path_confines_to_project_root(tmp_path, monkeypatch, mock_hou):
    from houdini_side.tools.common import resolve_output_path
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setenv("HOUDINI_MCP_PROJECT_ROOT", str(root))

    inside = resolve_output_path(mock_hou, str(root / "out.bgeo"), (".bgeo",))
    assert inside.startswith(os.path.realpath(str(root)))

    with pytest.raises(ValueError, match="outside HOUDINI_MCP_PROJECT_ROOT"):
        resolve_output_path(mock_hou, str(tmp_path / "escape.bgeo"), (".bgeo",))


# ---------------------------------------------------------------------------
# validate_read_path / enforce_project_root
# ---------------------------------------------------------------------------

def test_validate_read_path_returns_original_string(mock_hou):
    from houdini_side.tools.common import validate_read_path
    # $F-style sequence paths must survive untouched on file parms.
    assert validate_read_path(mock_hou, "/tmp/geo.$F.bgeo") == "/tmp/geo.$F.bgeo"


def test_validate_read_path_confines_to_project_root(tmp_path, monkeypatch, mock_hou):
    from houdini_side.tools.common import validate_read_path
    monkeypatch.setenv("HOUDINI_MCP_PROJECT_ROOT", str(tmp_path))
    with pytest.raises(ValueError, match="outside HOUDINI_MCP_PROJECT_ROOT"):
        validate_read_path(mock_hou, "/etc/passwd")


def test_enforce_project_root_noop_when_unset(monkeypatch):
    from houdini_side.tools.common import enforce_project_root
    monkeypatch.delenv("HOUDINI_MCP_PROJECT_ROOT", raising=False)
    enforce_project_root("/anywhere/at/all")  # must not raise


# ---------------------------------------------------------------------------
# as_text / to_jsonable / as_list / set_node_parm
# ---------------------------------------------------------------------------

def test_as_text_wraps_payload_in_mcp_envelope():
    from houdini_side.tools.common import as_text
    envelope = as_text({"success": True, "data": 1})
    assert envelope[0]["type"] == "text"
    assert json.loads(envelope[0]["text"]) == {"success": True, "data": 1}


def test_to_jsonable_passes_scalars_through():
    from houdini_side.tools.common import to_jsonable
    for value in (None, True, 3, 2.5, "txt"):
        assert to_jsonable(value) == value


def test_to_jsonable_converts_vector_like_to_list():
    from houdini_side.tools.common import to_jsonable

    class FakeVector:
        def __iter__(self):
            return iter((1.0, 2.0, 3.0))

    assert to_jsonable(FakeVector()) == [1.0, 2.0, 3.0]
    assert to_jsonable({"v": FakeVector()}) == {"v": [1.0, 2.0, 3.0]}


def test_to_jsonable_stringifies_opaque_objects():
    from houdini_side.tools.common import to_jsonable

    class FakeRamp:
        def __repr__(self):
            return "<hou.Ramp>"

    result = to_jsonable(FakeRamp())
    assert isinstance(result, str)
    json.dumps(result)  # must be serializable


def test_as_list_variants():
    from houdini_side.tools.common import as_list
    assert as_list(None) == []
    assert as_list((1, 2)) == [1, 2]
    assert as_list(iter([3])) == [3]
    assert as_list(7) == [7]


def test_set_node_parm_prefers_parm():
    from houdini_side.tools.common import set_node_parm
    calls = []
    node = types.SimpleNamespace(
        parm=lambda name: types.SimpleNamespace(set=lambda v: calls.append(v)),
        parmTuple=lambda name: None,
    )
    set_node_parm(node, "sizex", 5.0)
    assert calls == [5.0]


def test_set_node_parm_passes_explicit_reference_behavior():
    from houdini_side.tools.common import set_node_parm
    calls = []

    class Parm:
        def set(self, value, *, follow_parm_reference):
            calls.append((value, follow_parm_reference))

    node = types.SimpleNamespace(parm=lambda name: Parm(), parmTuple=lambda name: None)
    set_node_parm(node, "sizex", 5.0, follow_parm_reference=False)
    assert calls == [(5.0, False)]


def test_set_node_parm_falls_back_to_tuple_and_wraps_scalar():
    from houdini_side.tools.common import set_node_parm
    calls = []
    node = types.SimpleNamespace(
        parm=lambda name: None,
        parmTuple=lambda name: types.SimpleNamespace(set=lambda v: calls.append(v)),
    )
    set_node_parm(node, "t", 1.0)
    set_node_parm(node, "t", [1.0, 2.0, 3.0])
    assert calls == [[1.0], [1.0, 2.0, 3.0]]


def test_set_node_parm_raises_when_missing():
    from houdini_side.tools.common import set_node_parm
    node = types.SimpleNamespace(parm=lambda name: None, parmTuple=lambda name: None)
    with pytest.raises(ValueError, match="not found"):
        set_node_parm(node, "nope", 1)
