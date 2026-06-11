import types


def test_vex_run_with_modern_api(mock_hou):
    mock_hou.runVex = lambda code, inputs, ctx: {"P": (0, 1, 0)}
    from houdini_side.tools.vex import _vex_run
    result = _vex_run("@P.y += 1;", "sop")
    assert result["success"] is True
    assert result["data"]["context"] == "sop"


def test_vex_run_falls_back_to_legacy_signature(mock_hou):
    # Older API only accepts (code, context); the 3-arg call raises TypeError.
    mock_hou.runVex = lambda code, ctx: "legacy-ok"
    from houdini_side.tools.vex import _vex_run
    result = _vex_run("@P.y += 1;")
    assert result["success"] is True
    assert "legacy-ok" in result["data"]["result"]


def test_vex_run_unavailable(mock_hou):
    delattr(mock_hou, "runVex")
    from houdini_side.tools.vex import _vex_run
    result = _vex_run("@P.y += 1;")
    assert result["success"] is False
    assert "vop_snippet_set" in result["error"]


def test_vex_context_list(mock_hou):
    mock_hou.vexContexts = lambda: [types.SimpleNamespace(name=lambda: "sop")]
    from houdini_side.tools.vex import _vex_context_list
    result = _vex_context_list()
    assert result["success"] is True
    assert result["data"]["contexts"][0]["name"] == "sop"


def _make_snippet_node(parm_names):
    parms = {name: types.SimpleNamespace(
        set=lambda c, n=name: setattr(_make_snippet_node, "last", (n, c)),
        name=lambda n=name: n,
    ) for name in parm_names}
    return types.SimpleNamespace(parm=lambda name: parms.get(name))


def test_vop_snippet_set_uses_snippet_parm(mock_hou):
    mock_hou.node = lambda path: _make_snippet_node(["snippet"])
    from houdini_side.tools.vex import _vop_snippet_set
    result = _vop_snippet_set("/obj/geo/wrangle1", "@P.y += 1;")
    assert result["success"] is True
    assert result["data"]["parm"] == "snippet"


def test_vop_snippet_set_falls_back_to_code_parm(mock_hou):
    mock_hou.node = lambda path: _make_snippet_node(["code"])
    from houdini_side.tools.vex import _vop_snippet_set
    result = _vop_snippet_set("/obj/geo/vopsop1", "@P.y += 1;")
    assert result["success"] is True
    assert result["data"]["parm"] == "code"


def test_vop_snippet_set_no_code_parm(mock_hou):
    mock_hou.node = lambda path: _make_snippet_node([])
    from houdini_side.tools.vex import _vop_snippet_set
    result = _vop_snippet_set("/obj/geo/box1", "@P.y += 1;")
    assert result["success"] is False
    assert "snippet" in result["error"]


def test_vop_network_list_finds_vop_children(mock_hou):
    vop_cat = mock_hou.vopNodeTypeCategory()
    other_cat = types.SimpleNamespace(name=lambda: "Sop")

    def _node(path, cat, children=()):
        return types.SimpleNamespace(
            path=lambda: path,
            type=lambda: types.SimpleNamespace(category=lambda: cat),
            children=lambda: list(children),
        )

    vop = _node("/mat/principled1", vop_cat)
    sop = _node("/obj/geo1", other_cat)
    root = _node("/", other_cat, children=[vop, sop])
    mock_hou.node = lambda path: root if path == "/" else None

    from houdini_side.tools.vex import _vop_network_list
    result = _vop_network_list("/")
    assert result["success"] is True
    assert result["data"]["vop_networks"] == ["/mat/principled1"]


def test_vop_node_connect_uses_named_input(mock_hou):
    connections = []
    src = types.SimpleNamespace(path=lambda: "/mat/tex1")
    dst = types.SimpleNamespace(
        path=lambda: "/mat/principled1",
        setNamedInput=lambda port, node, out: connections.append((port, node.path(), out)),
    )
    nodes = {"/mat/tex1": src, "/mat/principled1": dst}
    mock_hou.node = lambda path: nodes.get(path)

    from houdini_side.tools.vex import _vop_node_connect
    result = _vop_node_connect("/mat/tex1", "color", "/mat/principled1", "basecolor")
    assert result["success"] is True
    assert connections == [("basecolor", "/mat/tex1", "color")]
