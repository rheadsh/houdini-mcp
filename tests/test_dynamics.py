import types


def _make_dop_object(name, data=()):
    return types.SimpleNamespace(
        name=lambda: name,
        allData=lambda: [types.SimpleNamespace(name=lambda d=d: d) for d in data],
        findData=lambda dname: f"<SIM_Data {dname}>" if dname in data else None,
    )


def _make_dop_node(objects=(), parms=None):
    _parms = parms or {}
    sim = types.SimpleNamespace(
        objects=lambda: list(objects),
        findObject=lambda name: next(
            (o for o in objects if o.name() == name), None
        ),
    )
    return types.SimpleNamespace(
        parm=lambda name: _parms.get(name),
        simulation=lambda: sim,
    )


def test_dop_object_list(mock_hou):
    node = _make_dop_node(objects=[_make_dop_object("pyro1"), _make_dop_object("smoke")])
    mock_hou.node = lambda path: node
    from houdini_side.tools.dynamics import _dop_object_list
    result = _dop_object_list("/obj/dopnet1")
    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert {"name": "pyro1"} in result["data"]["objects"]


def test_dop_object_info_lists_data(mock_hou):
    node = _make_dop_node(objects=[_make_dop_object("pyro1", data=("Forces", "Solver"))])
    mock_hou.node = lambda path: node
    from houdini_side.tools.dynamics import _dop_object_info
    result = _dop_object_info("/obj/dopnet1", "pyro1")
    assert result["success"] is True
    assert result["data"]["data"] == ["Forces", "Solver"]


def test_dop_object_info_not_found(mock_hou):
    mock_hou.node = lambda path: _make_dop_node()
    from houdini_side.tools.dynamics import _dop_object_info
    result = _dop_object_info("/obj/dopnet1", "ghost")
    assert result["success"] is False
    assert "ghost" in result["error"]


def test_dop_data_get(mock_hou):
    node = _make_dop_node(objects=[_make_dop_object("pyro1", data=("Forces",))])
    mock_hou.node = lambda path: node
    from houdini_side.tools.dynamics import _dop_data_get
    result = _dop_data_get("/obj/dopnet1", "pyro1", "Forces")
    assert result["success"] is True
    assert "Forces" in result["data"]["value"]


def test_dop_data_get_missing_data(mock_hou):
    node = _make_dop_node(objects=[_make_dop_object("pyro1", data=("Forces",))])
    mock_hou.node = lambda path: node
    from houdini_side.tools.dynamics import _dop_data_get
    result = _dop_data_get("/obj/dopnet1", "pyro1", "Gravity")
    assert result["success"] is False


def test_dop_sim_enable_uses_enabled_parm(mock_hou):
    calls = []
    parm = types.SimpleNamespace(set=lambda v: calls.append(v))
    mock_hou.node = lambda path: _make_dop_node(parms={"enabled": parm})
    from houdini_side.tools.dynamics import _dop_sim_enable
    assert _dop_sim_enable("/obj/dopnet1", False)["success"] is True
    assert _dop_sim_enable("/obj/dopnet1", True)["success"] is True
    assert calls == [0, 1]


def test_dop_sim_enable_falls_back_to_global_toggle(mock_hou):
    calls = []
    mock_hou.setSimulationEnabled = lambda on: calls.append(on)
    mock_hou.node = lambda path: _make_dop_node()
    from houdini_side.tools.dynamics import _dop_sim_enable
    result = _dop_sim_enable("/obj/dopnet1", True)
    assert result["success"] is True
    assert calls == [True]


def test_dop_sim_reset_presses_button(mock_hou):
    pressed = []
    parm = types.SimpleNamespace(pressButton=lambda: pressed.append(True))
    mock_hou.node = lambda path: _make_dop_node(parms={"resimulate": parm})
    from houdini_side.tools.dynamics import _dop_sim_reset
    result = _dop_sim_reset("/obj/dopnet1")
    assert result["success"] is True
    assert pressed == [True]


def test_dop_network_not_found(mock_hou):
    from houdini_side.tools.dynamics import _dop_object_list
    result = _dop_object_list("/obj/missing")
    assert result["success"] is False
    assert "not found" in result["error"].lower()
