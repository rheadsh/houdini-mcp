import types, pytest


# ---- Transform tests ----

def _make_obj_node(path="/obj/null1"):
    n = types.SimpleNamespace()
    n.path = lambda: path
    n.parmTuple = lambda name: types.SimpleNamespace(set=lambda v: None)
    n.setInput = lambda idx, src, out=0: None
    _mat = types.SimpleNamespace(
        asTuple=lambda: [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    )
    n.worldTransform = lambda: _mat
    n.localTransform = lambda: _mat
    n.setWorldTransform = lambda m: None
    return n


def test_obj_translate_calls_parmTuple(mock_hou):
    calls = []
    node = _make_obj_node()
    node.parmTuple = lambda name: types.SimpleNamespace(
        set=lambda v: calls.append((name, v))
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.transforms import _obj_translate
    result = _obj_translate("/obj/null1", 1.0, 2.0, 3.0)
    assert result["success"] is True
    assert any(c[0] == "t" for c in calls)


def test_obj_transform_get_world(mock_hou):
    node = _make_obj_node()
    mock_hou.node = lambda p: node
    from houdini_side.tools.transforms import _obj_transform_get
    result = _obj_transform_get("/obj/null1", "world")
    assert result["success"] is True
    assert "matrix" in result["data"]
    assert len(result["data"]["matrix"]) == 4


def test_obj_transform_get_invalid_space(mock_hou):
    node = _make_obj_node()
    mock_hou.node = lambda p: node
    from houdini_side.tools.transforms import _obj_transform_get
    result = _obj_transform_get("/obj/null1", "galactic")
    assert result["success"] is False
    assert "space" in result["error"].lower() or "invalid" in result["error"].lower()


def test_obj_rotate_calls_parmTuple(mock_hou):
    calls = []
    node = _make_obj_node()
    node.parmTuple = lambda name: types.SimpleNamespace(
        set=lambda v: calls.append((name, v))
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.transforms import _obj_rotate
    result = _obj_rotate("/obj/null1", 0.0, 90.0, 0.0)
    assert result["success"] is True
    assert any(c[0] == "r" for c in calls)


def test_obj_scale_success(mock_hou):
    node = _make_obj_node()
    mock_hou.node = lambda p: node
    from houdini_side.tools.transforms import _obj_scale
    result = _obj_scale("/obj/null1", 2.0, 2.0, 2.0)
    assert result["success"] is True
    assert result["data"]["s"] == [2.0, 2.0, 2.0]


def test_obj_translate_node_not_found(mock_hou):
    mock_hou.node = lambda p: None
    from houdini_side.tools.transforms import _obj_translate
    result = _obj_translate("/obj/missing", 1.0, 2.0, 3.0)
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_obj_parent_sets_input(mock_hou):
    calls = []
    child = _make_obj_node("/obj/child")
    child.setInput = lambda idx, src, out=0: calls.append((idx, src))
    parent_node = _make_obj_node("/obj/parent")

    def node_lookup(p):
        if p == "/obj/child":
            return child
        if p == "/obj/parent":
            return parent_node
        return None

    mock_hou.node = node_lookup
    from houdini_side.tools.transforms import _obj_parent
    result = _obj_parent("/obj/child", "/obj/parent")
    assert result["success"] is True
    assert result["data"]["parent"] == "/obj/parent"
    assert len(calls) == 1


def test_obj_parent_unparent(mock_hou):
    calls = []
    child = _make_obj_node("/obj/child")
    child.setInput = lambda idx, src, out=0: calls.append((idx, src))
    mock_hou.node = lambda p: child
    from houdini_side.tools.transforms import _obj_parent
    result = _obj_parent("/obj/child", None)
    assert result["success"] is True
    assert result["data"]["parent"] is None
    assert calls[0] == (0, None)


# ---- Rendering tests ----

def test_rop_list_returns_rops(mock_hou):
    import types as _t
    rop_cat = object()
    mock_hou.ropNodeTypeCategory = lambda: rop_cat
    rop_node = _t.SimpleNamespace(
        path=lambda: "/out/mantra1",
        type=lambda: _t.SimpleNamespace(
            name=lambda: "ifd",
            category=lambda: rop_cat,
        ),
    )
    parent = _t.SimpleNamespace(children=lambda: [rop_node])
    mock_hou.node = lambda p: parent
    from houdini_side.tools.rendering import _rop_list
    result = _rop_list("/out")
    assert result["success"] is True
    assert len(result["data"]["rops"]) == 1


def test_rop_get_output_tries_parm_names(mock_hou):
    import types as _t
    parm = _t.SimpleNamespace(eval=lambda: "/render/out.exr")
    node = _t.SimpleNamespace(
        parm=lambda name: parm if name == "vm_picture" else None,
        path=lambda: "/out/mantra1",
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.rendering import _rop_get_output
    result = _rop_get_output("/out/mantra1")
    assert result["success"] is True
    assert result["data"]["output"] == "/render/out.exr"
    assert result["data"]["parm"] == "vm_picture"


def test_rop_list_network_not_found(mock_hou):
    mock_hou.node = lambda p: None
    from houdini_side.tools.rendering import _rop_list
    result = _rop_list("/out")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_rop_render_status_not_cooking(mock_hou):
    import types as _t
    node = _t.SimpleNamespace(isCooking=lambda: False)
    mock_hou.node = lambda p: node
    from houdini_side.tools.rendering import _rop_render_status
    result = _rop_render_status("/out/mantra1")
    assert result["success"] is True
    assert result["data"]["is_cooking"] is False


def test_rop_get_output_no_parm(mock_hou):
    import types as _t
    node = _t.SimpleNamespace(
        parm=lambda name: None,
        path=lambda: "/out/custom",
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.rendering import _rop_get_output
    result = _rop_get_output("/out/custom")
    assert result["success"] is True
    assert result["data"]["output"] is None
    assert result["data"]["parm"] is None


def test_rop_frame_range_override(mock_hou):
    import types as _t
    set_calls = []
    trange_parm = _t.SimpleNamespace(set=lambda v: set_calls.append(("trange", v)))
    f_tuple = _t.SimpleNamespace(set=lambda v: set_calls.append(("f", v)))
    node = _t.SimpleNamespace(
        parm=lambda name: trange_parm if name == "trange" else None,
        parmTuple=lambda name: f_tuple if name == "f" else None,
    )
    mock_hou.node = lambda p: node
    from houdini_side.tools.rendering import _rop_frame_range_override
    result = _rop_frame_range_override("/out/mantra1", 1.0, 120.0)
    assert result["success"] is True
    assert result["data"]["start"] == 1.0
    assert result["data"]["end"] == 120.0
    assert any(c[0] == "trange" for c in set_calls)


# ---- Animation tests ----

def test_time_get_returns_frame(mock_hou):
    mock_hou.frame = lambda: 42.0
    mock_hou.time = lambda: 1.75
    mock_hou.fps = lambda: 24.0
    from houdini_side.tools.animation import _time_get
    result = _time_get()
    assert result["success"] is True
    assert result["data"]["frame"] == 42.0
    assert result["data"]["fps"] == 24.0


def test_fps_set_rejects_zero(mock_hou):
    from houdini_side.tools.animation import _fps_set
    result = _fps_set(0.0)
    assert result["success"] is False
    assert "positive" in result["error"].lower()


def test_frame_range_set_rejects_inverted(mock_hou):
    from houdini_side.tools.animation import _frame_range_set
    result = _frame_range_set(100.0, 1.0)
    assert result["success"] is False
    assert "end" in result["error"].lower() or ">=" in result["error"]


def test_fps_set_valid(mock_hou):
    set_calls = []
    mock_hou.setFps = lambda fps: set_calls.append(fps)
    mock_hou.fps = lambda: 30.0
    from houdini_side.tools.animation import _fps_set
    result = _fps_set(30.0)
    assert result["success"] is True
    assert result["data"]["fps"] == 30.0
    assert set_calls == [30.0]


def test_frame_range_get(mock_hou):
    mock_hou.playbar.frameRange = lambda: (1.0, 240.0)
    from houdini_side.tools.animation import _frame_range_get
    result = _frame_range_get()
    assert result["success"] is True
    assert result["data"]["start"] == 1.0
    assert result["data"]["end"] == 240.0


def test_time_set(mock_hou):
    set_calls = []
    mock_hou.setFrame = lambda f: set_calls.append(f)
    mock_hou.frame = lambda: 10.0
    from houdini_side.tools.animation import _time_set
    result = _time_set(10.0)
    assert result["success"] is True
    assert set_calls == [10.0]


def test_channel_list_no_keyframes(mock_hou):
    import types as _t
    parm_no_kf = _t.SimpleNamespace(name=lambda: "tx", keyframes=lambda: [])
    node = _t.SimpleNamespace(parms=lambda: [parm_no_kf])
    mock_hou.node = lambda p: node
    from houdini_side.tools.animation import _channel_list
    result = _channel_list("/obj/null1")
    assert result["success"] is True
    assert result["data"]["count"] == 0
    assert result["data"]["animated_parms"] == []


def test_keyframe_list_returns_keyframes(mock_hou):
    import types as _t
    kf = _t.SimpleNamespace(
        frame=lambda: 10.0,
        value=lambda: 5.0,
        expression=lambda: "",
        slope=lambda: 0.0,
    )
    parm = _t.SimpleNamespace(keyframes=lambda: [kf])
    node = _t.SimpleNamespace(parm=lambda name: parm if name == "tx" else None)
    mock_hou.node = lambda p: node
    from houdini_side.tools.animation import _keyframe_list
    result = _keyframe_list("/obj/null1", "tx")
    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["keyframes"][0]["frame"] == 10.0
    assert result["data"]["keyframes"][0]["value"] == 5.0
