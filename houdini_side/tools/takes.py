"""Take management tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _take_list():
    try:
        def work():
            takes_mod = getattr(hou, 'takes', None)
            if takes_mod is None:
                return ok({"takes": [], "note": "hou.takes not available"})
            root = takes_mod.rootTake()
            def _collect(take):
                result = [{"name": take.name(), "children": []}]
                for child in take.children():
                    result[0]["children"].extend(_collect(child))
                return result
            return ok({"takes": _collect(root)})
        return dispatch(work, label="take_list")
    except Exception as e:
        return err(e)


def _take_create(name: str, parent_name: "str | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: create take"):
                takes_mod = getattr(hou, 'takes', None)
                if takes_mod is None:
                    raise RuntimeError("hou.takes not available")
                if parent_name:
                    parent = takes_mod.findTake(parent_name)
                    if parent is None:
                        raise ValueError(f"Parent take not found: {parent_name!r}")
                else:
                    parent = takes_mod.rootTake()
                new_take = parent.addChildTake(name)
                return ok({"created": new_take.name()})
        return dispatch(work, label="take_create")
    except Exception as e:
        return err(e)


def _take_set_current(name: str):
    try:
        def work():
            takes_mod = getattr(hou, 'takes', None)
            if takes_mod is None:
                raise RuntimeError("hou.takes not available")
            take = takes_mod.findTake(name)
            if take is None:
                raise ValueError(f"Take not found: {name!r}")
            takes_mod.setCurrentTake(take)
            return ok({"current_take": name})
        return dispatch(work, label="take_set_current")
    except Exception as e:
        return err(e)


def _take_parm_include(node_path: str, parm_name: str):
    try:
        def work():
            with hou.undos.group("mcp: include parm in take"):
                takes_mod = getattr(hou, 'takes', None)
                if takes_mod is None:
                    raise RuntimeError("hou.takes not available")
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                pt = node.parmTuple(parm_name)
                if pt is None:
                    p = node.parm(parm_name)
                    if p is None:
                        raise ValueError(f"Parameter not found: {parm_name!r}")
                    pt = p.tuple()
                takes_mod.currentTake().addParmTuple(pt)
                return ok({"included": f"{node_path}/{parm_name}"})
        return dispatch(work, label="take_parm_include")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("take_list")
    async def take_list() -> list:
        """List all takes in the scene as a tree structure."""
        return [{"type": "text", "text": json.dumps(_take_list())}]

    @app.tool("take_create")
    async def take_create(name: str, parent_name: "str | None" = None) -> list:
        """Create a new take as a child of parent_name (or root if omitted)."""
        return [{"type": "text", "text": json.dumps(_take_create(name, parent_name))}]

    @app.tool("take_set_current")
    async def take_set_current(name: str) -> list:
        """Set the active take by name."""
        return [{"type": "text", "text": json.dumps(_take_set_current(name))}]

    @app.tool("take_parm_include")
    async def take_parm_include(node_path: str, parm_name: str) -> list:
        """Include a parameter in the current take."""
        return [{"type": "text", "text": json.dumps(_take_parm_include(node_path, parm_name))}]
