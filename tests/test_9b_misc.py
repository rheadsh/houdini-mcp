import types, pytest


# --- Utils tests ---

def test_run_hscript_returns_output(mock_hou):
    mock_hou.hscript = lambda cmd: ("hello world\n", "")
    from houdini_side.tools.utils import _run_hscript
    result = _run_hscript("echo hello")
    assert result["success"] is True
    assert "hello" in result["data"]["stdout"]


def test_eval_expression_returns_result(mock_hou):
    mock_hou.hscriptExpression = lambda e: 42.0
    from houdini_side.tools.utils import _eval_expression
    result = _eval_expression("$F")
    assert result["success"] is True
    assert result["data"]["result"] == 42.0


def test_expand_string(mock_hou):
    mock_hou.expandString = lambda s: "/projects/myshow"
    from houdini_side.tools.utils import _expand_string
    result = _expand_string("$HIP")
    assert result["success"] is True
    assert result["data"]["expanded"] == "/projects/myshow"


def test_env_get(mock_hou):
    mock_hou.getenv = lambda k, default=None: "24" if k == "FPS" else default
    from houdini_side.tools.utils import _env_get
    result = _env_get("FPS")
    assert result["success"] is True
    assert result["data"]["value"] == "24"


def test_env_set_calls_putenv(mock_hou):
    calls = []
    mock_hou.putenv = lambda k, v: calls.append((k, v))
    from houdini_side.tools.utils import _env_set
    result = _env_set("MY_VAR", "hello")
    assert result["success"] is True
    assert calls == [("MY_VAR", "hello")]


def test_update_mode_set_invalid(mock_hou):
    from houdini_side.tools.utils import _update_mode_set
    result = _update_mode_set("turbo")
    assert result["success"] is False
    assert "unknown" in result["error"].lower() or "valid" in result["error"].lower()


def test_path_list(mock_hou):
    mock_hou.houdiniPath = lambda: ["/hfs", "/home/user/houdini20"]
    from houdini_side.tools.utils import _path_list
    result = _path_list()
    assert result["success"] is True
    assert "/hfs" in result["data"]["paths"]


def test_houdini_env_diagnostics(mock_hou):
    mock_hou.houdiniPath = lambda: ["/hfs"]
    mock_hou.getenv = lambda k, default=None: "9876" if k == "HOUDINI_MCP_PORT" else default
    from houdini_side.tools.utils import _houdini_env_diagnostics
    result = _houdini_env_diagnostics()
    assert result["success"] is True
    assert result["data"]["houdini"]["version"] == "20.5.000"
    assert result["data"]["env"]["HOUDINI_MCP_PORT"] == "9876"


# --- HDA tests ---

def test_hda_list_returns_empty_when_unavailable(mock_hou):
    # Remove hda attr to simulate unavailability
    if hasattr(mock_hou, 'hda'):
        delattr(mock_hou, 'hda')
    from houdini_side.tools.hda import _hda_list
    result = _hda_list()
    assert result["success"] is True
    assert result["data"]["hdas"] == []
