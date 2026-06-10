"""SOP geometry inspection and export tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import resolve_output_path, validate_read_path


_GEO_SUFFIXES = (".bgeo", ".bgeo.sc", ".obj", ".fbx", ".usd", ".usda", ".usdc")


def _geo_info(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            return ok({
                "point_count": geo.pointCount(),
                "prim_count": geo.primCount(),
                "vertex_count": geo.vertexCount(),
                "point_attribs": [a.name() for a in geo.pointAttribs()],
                "prim_attribs": [a.name() for a in geo.primAttribs()],
                "vertex_attribs": [a.name() for a in geo.vertexAttribs()],
                "global_attribs": [a.name() for a in geo.globalAttribs()],
            })
        return dispatch(work, label="geo_info")
    except Exception as e:
        return err(e)


def _attrib_info(a):
    try:
        default = a.defaultValue()
        default_val = list(default) if hasattr(default, '__iter__') else default
    except Exception:
        default_val = None
    return {
        "name": a.name(),
        "type": str(a.dataType()),
        "size": a.size(),
        "default": default_val,
    }


def _geo_attributes(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            return ok({
                "point": [_attrib_info(a) for a in geo.pointAttribs()],
                "prim": [_attrib_info(a) for a in geo.primAttribs()],
                "vertex": [_attrib_info(a) for a in geo.vertexAttribs()],
                "global": [_attrib_info(a) for a in geo.globalAttribs()],
            })
        return dispatch(work, label="geo_attributes")
    except Exception as e:
        return err(e)


def _geo_attribute_values(sop_path: str, attrib_name: str, max_count: int = 100):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            # Try all attribute classes in priority order
            attrib = (geo.findPointAttrib(attrib_name)
                      or geo.findPrimAttrib(attrib_name)
                      or geo.findVertexAttrib(attrib_name)
                      or geo.findGlobalAttrib(attrib_name))
            if attrib is None:
                raise ValueError(
                    f"Attribute {attrib_name!r} not found on {sop_path!r}. "
                    f"Use geo_attributes to list available attributes."
                )
            attrib_class = str(attrib.type()) if hasattr(attrib, 'type') else str(attrib.dataType())
            if "point" in attrib_class.lower():
                items = list(geo.points())[:max_count]
                vals = [p.attribValue(attrib_name) for p in items]
            elif "prim" in attrib_class.lower():
                items = list(geo.prims())[:max_count]
                vals = [p.attribValue(attrib_name) for p in items]
            elif "vertex" in attrib_class.lower():
                raise ValueError(
                    f"Vertex attribute {attrib_name!r} iteration is not directly supported. "
                    "Iterate via geo.prims() then prim.vertices() in a Python SOP or script."
                )
            elif "global" in attrib_class.lower():
                # Detail (global) attrib — single value
                vals = [geo.attribValue(attrib_name)]
            else:
                vals = []
            vals = [list(v) if hasattr(v, '__iter__') and not isinstance(v, str)
                    else v for v in vals]
            return ok({"attrib": attrib_name, "count": len(vals), "values": vals})
        return dispatch(work, label="geo_attribute_values")
    except Exception as e:
        return err(e)


def _geo_groups(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            return ok({
                "point_groups": [
                    {"name": g.name(), "size": len(g.points())}
                    for g in geo.pointGroups()
                ],
                "prim_groups": [
                    {"name": g.name(), "size": len(g.prims())}
                    for g in geo.primGroups()
                ],
                "vertex_groups": [{"name": g.name()} for g in geo.vertexGroups()],
                "edge_groups": [{"name": g.name()} for g in geo.edgeGroups()],
            })
        return dispatch(work, label="geo_groups")
    except Exception as e:
        return err(e)


def _geo_points(sop_path: str, max_count: int = 100):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            pts = list(geo.points())[:max_count]
            positions = [list(p.position()) for p in pts]
            return ok({"count": len(positions), "positions": positions})
        return dispatch(work, label="geo_points")
    except Exception as e:
        return err(e)


def _geo_bbox(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            bbox = geo.boundingBox()
            mn = bbox.minvec()
            mx = bbox.maxvec()
            sz = bbox.sizevec()
            ct = bbox.center()
            return ok({
                "min": [mn[0], mn[1], mn[2]],
                "max": [mx[0], mx[1], mx[2]],
                "size": [sz[0], sz[1], sz[2]],
                "center": [ct[0], ct[1], ct[2]],
            })
        return dispatch(work, label="geo_bbox")
    except Exception as e:
        return err(e)


def _geo_save(sop_path: str, file_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path!r}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No cooked geometry on node: {sop_path!r}")
            safe_path = resolve_output_path(hou, file_path, _GEO_SUFFIXES)
            geo.save(safe_path)
            return ok({"saved_to": safe_path})
        return dispatch(work, label="geo_save")
    except Exception as e:
        return err(e)


def _geo_load(parent_path: str, file_path: str):
    try:
        def work():
            with hou.undos.group("mcp: load geometry"):
                parent = hou.node(parent_path)
                if parent is None:
                    raise ValueError(f"Parent not found: {parent_path!r}")
                safe_path = validate_read_path(hou, file_path)
                file_sop = parent.createNode("file")
                file_sop.parm("file").set(safe_path)
                return ok({"node": file_sop.path(), "file": safe_path})
        return dispatch(work, label="geo_load")
    except Exception as e:
        return err(e)


def register(app):
    """Register all 8 geometry tools."""
    import json

    @app.tool("geo_info")
    async def geo_info(sop_path: str) -> list:
        """Get geometry stats: point/prim/vertex counts and all attribute names."""
        return [{"type": "text", "text": json.dumps(_geo_info(sop_path))}]

    @app.tool("geo_attributes")
    async def geo_attributes(sop_path: str) -> list:
        """List all attributes with their type, size, and default value."""
        return [{"type": "text", "text": json.dumps(_geo_attributes(sop_path))}]

    @app.tool("geo_attribute_values")
    async def geo_attribute_values(sop_path: str, attrib_name: str,
                                    max_count: int = 100) -> list:
        """Get the first max_count values of a point or prim attribute."""
        return [{"type": "text", "text": json.dumps(
            _geo_attribute_values(sop_path, attrib_name, max_count)
        )}]

    @app.tool("geo_groups")
    async def geo_groups(sop_path: str) -> list:
        """List all point/prim/vertex/edge groups with their sizes."""
        return [{"type": "text", "text": json.dumps(_geo_groups(sop_path))}]

    @app.tool("geo_points")
    async def geo_points(sop_path: str, max_count: int = 100) -> list:
        """Get point positions as [x, y, z] lists (first max_count points)."""
        return [{"type": "text", "text": json.dumps(_geo_points(sop_path, max_count))}]

    @app.tool("geo_bbox")
    async def geo_bbox(sop_path: str) -> list:
        """Get the bounding box: min, max, size, center (all as [x,y,z] lists)."""
        return [{"type": "text", "text": json.dumps(_geo_bbox(sop_path))}]

    @app.tool("geo_save")
    async def geo_save(sop_path: str, file_path: str) -> list:
        """Export geometry to file. Supports .bgeo, .bgeo.sc, .obj, .fbx, .usd."""
        return [{"type": "text", "text": json.dumps(_geo_save(sop_path, file_path))}]

    @app.tool("geo_load")
    async def geo_load(parent_path: str, file_path: str) -> list:
        """Create a File SOP inside parent_path that loads geometry from file_path."""
        return [{"type": "text", "text": json.dumps(_geo_load(parent_path, file_path))}]
