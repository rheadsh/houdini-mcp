import types, pytest


def _make_attrib(name, attrib_type="point", size=1, default=0.0):
    a = types.SimpleNamespace()
    a.name = lambda: name
    a.dataType = lambda: attrib_type
    a.size = lambda: size
    a.defaultValue = lambda: (default,) if size == 1 else (default,) * size
    return a


def _make_geo(npoints=100, nprims=50):
    g = types.SimpleNamespace()
    g.pointCount = lambda: npoints
    g.primCount = lambda: nprims
    g.vertexCount = lambda: nprims * 4
    g.pointAttribs = lambda: [_make_attrib("P", "point", 3, 0.0),
                               _make_attrib("N", "point", 3, 0.0)]
    g.primAttribs = lambda: [_make_attrib("Cd", "prim", 3, 1.0)]
    g.vertexAttribs = lambda: []
    g.globalAttribs = lambda: []
    g.pointGroups = lambda: []
    g.primGroups = lambda: []
    g.vertexGroups = lambda: []
    g.edgeGroups = lambda: []
    # Make 3 fake points
    _pts = [
        types.SimpleNamespace(
            position=lambda i=i: types.SimpleNamespace(
                __getitem__=lambda self, j: [float(i), 0.0, 0.0][j]
            ),
            attribValue=lambda n, i=i: float(i),
        )
        for i in range(3)
    ]
    g.points = lambda: _pts
    # Bounding box — use a real subscriptable class since SimpleNamespace
    # does not support special method lookup via __getitem__ as an attribute.
    class _Vec3:
        def __init__(self, vals): self._v = vals
        def __getitem__(self, i): return self._v[i]

    _bbox = types.SimpleNamespace(
        minvec=lambda: _Vec3([-1.0, -1.0, -1.0]),
        maxvec=lambda: _Vec3([1.0, 1.0, 1.0]),
        sizevec=lambda: _Vec3([2.0, 2.0, 2.0]),
        center=lambda: _Vec3([0.0, 0.0, 0.0]),
    )
    g.boundingBox = lambda: _bbox
    g.findPointAttrib = lambda name: _make_attrib(name) if name in ("P", "N") else None
    g.findPrimAttrib = lambda name: _make_attrib(name, "prim") if name == "Cd" else None
    g.findVertexAttrib = lambda name: None
    g.findGlobalAttrib = lambda name: None
    g.save = lambda path: None
    return g


def _make_sop(geo):
    s = types.SimpleNamespace()
    s.geometry = lambda: geo
    s.path = lambda: "/obj/geo1/box1"
    s.parent = lambda: types.SimpleNamespace(
        path=lambda: "/obj/geo1",
        createNode=lambda t, name=None: types.SimpleNamespace(
            path=lambda: f"/obj/geo1/{name or t}",
            parm=lambda n: types.SimpleNamespace(set=lambda v: None),
        ),
    )
    return s


def test_geo_info_returns_counts(mock_hou):
    sop = _make_sop(_make_geo(100, 50))
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_info
    result = _geo_info("/obj/geo1/box1")
    assert result["success"] is True
    assert result["data"]["point_count"] == 100
    assert result["data"]["prim_count"] == 50


def test_geo_info_missing_node(mock_hou):
    mock_hou.node = lambda p: None
    from houdini_side.tools.geometry import _geo_info
    result = _geo_info("/obj/nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_geo_attributes_lists_attribs(mock_hou):
    sop = _make_sop(_make_geo())
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_attributes
    result = _geo_attributes("/obj/geo1/box1")
    assert result["success"] is True
    point_names = [a["name"] for a in result["data"]["point"]]
    assert "P" in point_names
    assert "N" in point_names


def test_geo_bbox_returns_bounds(mock_hou):
    sop = _make_sop(_make_geo())
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_bbox
    result = _geo_bbox("/obj/geo1/box1")
    assert result["success"] is True
    assert result["data"]["min"] == [-1.0, -1.0, -1.0]
    assert result["data"]["max"] == [1.0, 1.0, 1.0]
    assert result["data"]["size"] == [2.0, 2.0, 2.0]


def test_geo_save_calls_geo_save(mock_hou):
    saved = []
    geo = _make_geo()
    geo.save = lambda path: saved.append(path)
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_save
    result = _geo_save("/obj/geo1/box1", "/tmp/out.bgeo")
    assert result["success"] is True
    assert saved == ["/tmp/out.bgeo"]


def test_geo_groups_returns_empty(mock_hou):
    sop = _make_sop(_make_geo())
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_groups
    result = _geo_groups("/obj/geo1/box1")
    assert result["success"] is True
    assert result["data"]["point_groups"] == []
    assert result["data"]["prim_groups"] == []


def test_geo_points_returns_positions(mock_hou):
    """geo_points serializes point positions as [x, y, z] lists."""
    import types

    class _Vec3:
        def __init__(self, x, y, z): self._v = [x, y, z]
        def __getitem__(self, i): return self._v[i]
        def __iter__(self): return iter(self._v)

    geo = _make_geo(3, 0)
    pts = [
        types.SimpleNamespace(position=lambda i=i: _Vec3(float(i), 0.0, 0.0))
        for i in range(3)
    ]
    geo.points = lambda: pts
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_points
    result = _geo_points("/obj/geo1/box1", max_count=10)
    assert result["success"] is True
    assert result["data"]["count"] == 3
    assert result["data"]["positions"][0] == [0.0, 0.0, 0.0]
    assert result["data"]["positions"][1] == [1.0, 0.0, 0.0]


def test_geo_points_respects_max_count(mock_hou):
    """geo_points truncates to max_count."""
    import types

    class _Vec3:
        def __init__(self): pass
        def __iter__(self): return iter([0.0, 0.0, 0.0])

    geo = _make_geo(100, 0)
    geo.points = lambda: [types.SimpleNamespace(position=lambda: _Vec3()) for _ in range(100)]
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_points
    result = _geo_points("/obj/geo1/box1", max_count=5)
    assert result["data"]["count"] == 5


def test_geo_attribute_values_vertex_attrib_returns_error(mock_hou):
    """geo_attribute_values returns actionable error for vertex attributes."""
    import types
    geo = _make_geo()
    vertex_attrib = types.SimpleNamespace(
        type=lambda: "vertex",
        dataType=lambda: "vertex",
        name=lambda: "uv",
        size=lambda: 3,
    )
    geo.findPointAttrib = lambda n: None
    geo.findPrimAttrib = lambda n: None
    geo.findVertexAttrib = lambda n: vertex_attrib if n == "uv" else None
    geo.findGlobalAttrib = lambda n: None
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_attribute_values
    result = _geo_attribute_values("/obj/geo1/box1", "uv")
    assert result["success"] is False
    assert "vertex" in result["error"].lower()
