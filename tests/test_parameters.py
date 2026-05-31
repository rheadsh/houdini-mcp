# tests/test_parameters.py
import types, pytest


def _make_parm(name="tx", value=5.0):
    p = types.SimpleNamespace()
    p.name = lambda: name
    p.eval = lambda: value
    p._val = value
    p.set = lambda v: setattr(p, "_val", v)
    p.revertToDefaults = lambda: None
    p.lock = lambda on: None
    p.setExpression = lambda expr, lang=None: None
    p.keyframes = lambda: []
    p.setKeyframe = lambda kf: None
    p.deleteKeyframeAtFrame = lambda f: None
    p.isLocked = lambda: False
    return p


def _make_node_with_parm(parm_name="tx", parm_value=5.0):
    node = types.SimpleNamespace()
    parm = _make_parm(parm_name, parm_value)
    node.path = lambda: "/obj/geo1/box1"
    node.parm = lambda name: parm if name == parm_name else None
    node.parmTuple = lambda name: None
    node.parms = lambda: [parm]
    return node


def test_parm_get_returns_value(mock_hou):
    node = _make_node_with_parm("tx", 5.0)
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_get
    result = _parm_get("/obj/geo1/box1", "tx")
    assert result["success"] is True
    assert result["data"]["value"] == 5.0


def test_parm_get_missing_node(mock_hou):
    mock_hou.node = lambda p: None
    from houdini_side.tools.parameters import _parm_get
    result = _parm_get("/obj/nonexistent", "tx")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_parm_get_missing_parm(mock_hou):
    node = _make_node_with_parm("tx")
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_get
    result = _parm_get("/obj/geo1/box1", "BADPARM")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_parm_set_calls_set(mock_hou):
    set_vals = []
    node = _make_node_with_parm("tx")
    node.parm("tx").set = lambda v: set_vals.append(v)
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_set
    result = _parm_set("/obj/geo1/box1", "tx", 3.14)
    assert result["success"] is True
    assert set_vals == [3.14]


def test_parm_set_many_sets_all_items(mock_hou):
    set_vals = []
    node1 = _make_node_with_parm("tx")
    node2 = _make_node_with_parm("ty")
    node1.parm("tx").set = lambda v: set_vals.append(("/obj/geo1/box1", "tx", v))
    node2.parm("ty").set = lambda v: set_vals.append(("/obj/geo1/box2", "ty", v))
    mock_hou.node = lambda p: {
        "/obj/geo1/box1": node1,
        "/obj/geo1/box2": node2,
    }.get(p)

    from houdini_side.tools.parameters import _parm_set_many
    result = _parm_set_many([
        {"node_path": "/obj/geo1/box1", "parm_name": "tx", "value": 1.0},
        {"node_path": "/obj/geo1/box2", "parm_name": "ty", "value": 2.0},
    ])

    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert set_vals == [
        ("/obj/geo1/box1", "tx", 1.0),
        ("/obj/geo1/box2", "ty", 2.0),
    ]


def test_parm_revert(mock_hou):
    reverted = []
    node = _make_node_with_parm("tx")
    node.parm("tx").revertToDefaults = lambda: reverted.append(True)
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_revert
    result = _parm_revert("/obj/geo1/box1", "tx")
    assert result["success"] is True
    assert reverted == [True]


def test_parm_set_expression(mock_hou):
    exprs = []
    node = _make_node_with_parm("tx")
    node.parm("tx").setExpression = lambda e, lang=None: exprs.append((e, lang))
    # mock exprLanguage
    import types as _types
    mock_hou.exprLanguage = _types.SimpleNamespace(
        Python="python", Hscript="hscript"
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_set_expression
    result = _parm_set_expression("/obj/geo1/box1", "tx", "sin($F)", "python")
    assert result["success"] is True
    assert exprs[0][0] == "sin($F)"


def test_parm_get_all(mock_hou):
    node = _make_node_with_parm("tx", 7.0)
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_get_all
    result = _parm_get_all("/obj/geo1/box1")
    assert result["success"] is True
    assert "tx" in result["data"]["parameters"]
    assert result["data"]["parameters"]["tx"] == 7.0


def test_parm_keyframe_set(mock_hou):
    kf_set = []
    node = _make_node_with_parm("tx", 3.0)
    node.parm("tx").setKeyframe = lambda kf: kf_set.append(kf)
    mock_hou.node = lambda p: node
    mock_hou.frame = lambda: 10.0
    # Keyframe mock already in conftest
    from houdini_side.tools.parameters import _parm_keyframe_set
    result = _parm_keyframe_set("/obj/geo1/box1", "tx", frame=10.0, value=3.0)
    assert result["success"] is True
    assert len(kf_set) == 1


def test_parm_link_sets_expression(mock_hou):
    exprs = []
    node = _make_node_with_parm("tx")
    node.parm("tx").setExpression = lambda e, lang=None: exprs.append(e)
    import types as _types
    mock_hou.exprLanguage = _types.SimpleNamespace(Python="python", Hscript="hscript")
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_link
    result = _parm_link("/obj/src", "tx", "/obj/geo1/box1", "tx")
    assert result["success"] is True
    assert 'ch("' in exprs[0]
