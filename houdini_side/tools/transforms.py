"""Object transform tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _obj_transform_get(obj_path: str, space: str = "world"):
    try:
        def work():
            node = hou.node(obj_path)
            if node is None:
                raise ValueError(f"Node not found: {obj_path!r}")
            if space == "world":
                m = node.worldTransform()
            elif space == "local":
                m = node.localTransform()
            else:
                raise ValueError(f"Invalid space {space!r}. Use 'world' or 'local'.")
            return ok({"matrix": [list(row) for row in m.asTuple()], "space": space})
        return dispatch(work, label="obj_transform_get")
    except Exception as e:
        return err(e)


def _obj_transform_set(obj_path: str, matrix4x4: list):
    try:
        def work():
            with hou.undos.group("mcp: set transform"):
                node = hou.node(obj_path)
                if node is None:
                    raise ValueError(f"Node not found: {obj_path!r}")
                m = hou.Matrix4(matrix4x4)
                node.setWorldTransform(m)
                return ok({"path": obj_path})
        return dispatch(work, label="obj_transform_set")
    except Exception as e:
        return err(e)


def _obj_translate(obj_path: str, tx: float, ty: float, tz: float):
    try:
        def work():
            with hou.undos.group("mcp: set translation"):
                node = hou.node(obj_path)
                if node is None:
                    raise ValueError(f"Node not found: {obj_path!r}")
                node.parmTuple("t").set((tx, ty, tz))
                return ok({"path": obj_path, "t": [tx, ty, tz]})
        return dispatch(work, label="obj_translate")
    except Exception as e:
        return err(e)


def _obj_rotate(obj_path: str, rx: float, ry: float, rz: float):
    try:
        def work():
            with hou.undos.group("mcp: set rotation"):
                node = hou.node(obj_path)
                if node is None:
                    raise ValueError(f"Node not found: {obj_path!r}")
                node.parmTuple("r").set((rx, ry, rz))
                return ok({"path": obj_path, "r": [rx, ry, rz]})
        return dispatch(work, label="obj_rotate")
    except Exception as e:
        return err(e)


def _obj_scale(obj_path: str, sx: float, sy: float, sz: float):
    try:
        def work():
            with hou.undos.group("mcp: set scale"):
                node = hou.node(obj_path)
                if node is None:
                    raise ValueError(f"Node not found: {obj_path!r}")
                node.parmTuple("s").set((sx, sy, sz))
                return ok({"path": obj_path, "s": [sx, sy, sz]})
        return dispatch(work, label="obj_scale")
    except Exception as e:
        return err(e)


def _obj_parent(child_path: str, parent_path: "str | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: parent object"):
                child = hou.node(child_path)
                if child is None:
                    raise ValueError(f"Child node not found: {child_path!r}")
                if parent_path is not None:
                    parent = hou.node(parent_path)
                    if parent is None:
                        raise ValueError(f"Parent node not found: {parent_path!r}")
                    child.setInput(0, parent)
                    return ok({"child": child_path, "parent": parent_path})
                else:
                    child.setInput(0, None)
                    return ok({"child": child_path, "parent": None})
        return dispatch(work, label="obj_parent")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("obj_transform_get")
    async def obj_transform_get(obj_path: str, space: str = "world") -> list:
        """Get a 4x4 transform matrix. space: 'world' (default) or 'local'."""
        return [{"type": "text", "text": json.dumps(_obj_transform_get(obj_path, space))}]

    @app.tool("obj_transform_set")
    async def obj_transform_set(obj_path: str, matrix4x4: list) -> list:
        """Set an object's world transform from a 4x4 matrix (list of 4 rows of 4 floats)."""
        return [{"type": "text", "text": json.dumps(_obj_transform_set(obj_path, matrix4x4))}]

    @app.tool("obj_translate")
    async def obj_translate(obj_path: str, tx: float, ty: float, tz: float) -> list:
        """Set object translation parameters tx, ty, tz."""
        return [{"type": "text", "text": json.dumps(_obj_translate(obj_path, tx, ty, tz))}]

    @app.tool("obj_rotate")
    async def obj_rotate(obj_path: str, rx: float, ry: float, rz: float) -> list:
        """Set object rotation parameters rx, ry, rz (degrees)."""
        return [{"type": "text", "text": json.dumps(_obj_rotate(obj_path, rx, ry, rz))}]

    @app.tool("obj_scale")
    async def obj_scale(obj_path: str, sx: float, sy: float, sz: float) -> list:
        """Set object uniform or per-axis scale sx, sy, sz."""
        return [{"type": "text", "text": json.dumps(_obj_scale(obj_path, sx, sy, sz))}]

    @app.tool("obj_parent")
    async def obj_parent(child_path: str, parent_path: "str | None" = None) -> list:
        """Parent child to parent (input 0). Pass parent_path=null to unparent."""
        return [{"type": "text", "text": json.dumps(_obj_parent(child_path, parent_path))}]
