import types, pytest

# ---- Mock helpers ----

def _make_node(path="/obj/geo1", node_type="geo", children=None, inputs=None):
    """Build a minimal hou.Node-like SimpleNamespace."""
    n = types.SimpleNamespace()
    n.path = lambda: path
    n.name = lambda: path.split("/")[-1]
    n.type = lambda: types.SimpleNamespace(name=lambda: node_type)
    parent_path = "/".join(path.split("/")[:-1]) or "/"
    n.parent = lambda: types.SimpleNamespace(path=lambda: parent_path)
    n.children = lambda: (children or [])
    _inputs = inputs or []
    n.inputs = lambda: _inputs
    n.outputs = lambda: []
    n.isBypassed = lambda: False
    n.isDisplayFlagSet = lambda: True
    n.isRenderFlagSet = lambda: False
    n.color = lambda: types.SimpleNamespace(rgb=lambda: (0.6, 0.6, 0.6))
    n.position = lambda: types.SimpleNamespace(__getitem__=lambda self, i: [0.0, 0.0][i])
    n.comment = lambda: ""
    n.setName = lambda name: None
    n.destroy = lambda: None
    n.bypass = lambda on: None
    n.setDisplayFlag = lambda on: None
    n.setRenderFlag = lambda on: None
    n.setTemplateFlag = lambda on: None
    n.setHighlightFlag = lambda on: None
    n.setPosition = lambda pos: None
    n.setColor = lambda c: None
    n.setComment = lambda s: None
    n.layoutChildren = lambda: None
    n.cook = lambda force=False: None
    n.createNode = lambda t, name=None: _make_node(f"{path}/{name or t}", t)
    n.setInput = lambda idx, src, out=0: None
    n.createNetworkBox = lambda: types.SimpleNamespace(
        setComment=lambda s: None,
        setColor=lambda c: None,
    )
    n.createStickyNote = lambda: types.SimpleNamespace(
        setText=lambda s: None,
        setPosition=lambda p: None,
    )
    return n


# ---- Tests ----

def test_node_get_returns_info(mock_hou):
    node = _make_node("/obj/geo1", "geo")
    mock_hou.node = lambda path: node
    from houdini_side.tools.nodes import _node_get
    result = _node_get("/obj/geo1")
    assert result["success"] is True
    assert result["data"]["path"] == "/obj/geo1"
    assert result["data"]["type"] == "geo"


def test_node_get_missing_returns_err(mock_hou):
    mock_hou.node = lambda path: None
    from houdini_side.tools.nodes import _node_get
    result = _node_get("/obj/nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_node_list_returns_children(mock_hou):
    children = [_make_node("/obj/geo1"), _make_node("/obj/cam1")]
    parent = _make_node("/obj", children=children)
    mock_hou.node = lambda path: parent
    from houdini_side.tools.nodes import _node_list
    result = _node_list("/obj")
    assert result["success"] is True
    assert len(result["data"]["nodes"]) == 2


def test_node_create_calls_createNode(mock_hou):
    created = []
    def create_node(node_type, name=None):
        child = _make_node(f"/obj/{name or node_type}", node_type)
        created.append(child)
        return child
    parent = _make_node("/obj")
    parent.createNode = create_node
    mock_hou.node = lambda path: parent if path == "/obj" else None
    from houdini_side.tools.nodes import _node_create
    result = _node_create("/obj", "geo", "mygeo")
    assert result["success"] is True
    assert len(created) == 1


def test_node_delete_calls_destroy(mock_hou):
    destroyed = []
    node = _make_node("/obj/geo1")
    node.destroy = lambda: destroyed.append(True)
    mock_hou.node = lambda path: node
    from houdini_side.tools.nodes import _node_delete
    result = _node_delete("/obj/geo1")
    assert result["success"] is True
    assert destroyed == [True]


def test_node_connect_calls_setInput(mock_hou):
    calls = []
    src = _make_node("/obj/geo1")
    dst = _make_node("/obj/geo2")
    dst.setInput = lambda idx, node, out=0: calls.append((idx, node, out))
    mock_hou.node = lambda p: src if p == "/obj/geo1" else dst
    from houdini_side.tools.nodes import _node_connect
    result = _node_connect("/obj/geo1", 0, "/obj/geo2", 0)
    assert result["success"] is True
    assert calls[0] == (0, src, 0)


def test_node_bypass_calls_bypass(mock_hou):
    calls = []
    node = _make_node()
    node.bypass = lambda on: calls.append(on)
    mock_hou.node = lambda p: node
    from houdini_side.tools.nodes import _node_bypass
    result = _node_bypass("/obj/geo1", True)
    assert result["success"] is True
    assert calls == [True]


def test_node_set_flag_display(mock_hou):
    calls = []
    node = _make_node()
    node.setDisplayFlag = lambda on: calls.append(on)
    mock_hou.node = lambda p: node
    from houdini_side.tools.nodes import _node_set_flag
    result = _node_set_flag("/obj/geo1", "display", True)
    assert result["success"] is True
    assert calls == [True]


def test_node_type_list_unknown_context(mock_hou):
    from houdini_side.tools.nodes import _node_type_list
    result = _node_type_list("badcontext")
    assert result["success"] is False
    assert "unknown" in result["error"].lower()
