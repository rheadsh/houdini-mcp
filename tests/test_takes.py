import types


def _make_take(name, children=None):
    t = types.SimpleNamespace()
    t.name = lambda: name
    t.children = lambda: children or []
    t.addChildTake = lambda n: _make_take(n)
    t.addParmTuple = lambda pt: None
    return t


def test_take_list_returns_tree(mock_hou):
    grandchild = _make_take("fx_v2")
    child = _make_take("fx_v1", children=[grandchild])
    mock_hou.takes.rootTake = lambda: _make_take("Main", children=[child])
    from houdini_side.tools.takes import _take_list
    result = _take_list()
    assert result["success"] is True
    tree = result["data"]["takes"]
    assert tree[0]["name"] == "Main"
    assert tree[0]["children"][0]["name"] == "fx_v1"
    assert tree[0]["children"][0]["children"][0]["name"] == "fx_v2"


def test_take_list_when_takes_unavailable(mock_hou):
    delattr(mock_hou, "takes")
    from houdini_side.tools.takes import _take_list
    result = _take_list()
    assert result["success"] is True
    assert result["data"]["takes"] == []


def test_take_create_under_root(mock_hou):
    created = []
    root = _make_take("Main")
    root.addChildTake = lambda n: created.append(n) or _make_take(n)
    mock_hou.takes.rootTake = lambda: root
    from houdini_side.tools.takes import _take_create
    result = _take_create("lighting_v1")
    assert result["success"] is True
    assert result["data"]["created"] == "lighting_v1"
    assert created == ["lighting_v1"]


def test_take_create_missing_parent(mock_hou):
    mock_hou.takes.findTake = lambda name: None
    from houdini_side.tools.takes import _take_create
    result = _take_create("child", parent_name="ghost")
    assert result["success"] is False
    assert "ghost" in result["error"]


def test_take_set_current(mock_hou):
    selected = []
    take = _make_take("fx_v1")
    mock_hou.takes.findTake = lambda name: take if name == "fx_v1" else None
    mock_hou.takes.setCurrentTake = lambda t: selected.append(t.name())
    from houdini_side.tools.takes import _take_set_current
    result = _take_set_current("fx_v1")
    assert result["success"] is True
    assert selected == ["fx_v1"]


def test_take_set_current_not_found(mock_hou):
    mock_hou.takes.findTake = lambda name: None
    from houdini_side.tools.takes import _take_set_current
    result = _take_set_current("ghost")
    assert result["success"] is False
