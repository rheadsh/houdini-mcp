"""Parameter read/write, expressions, keyframes, linking."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _set_node_parm(node, parm_name: str, value):
    parm = node.parm(parm_name)
    if parm is None:
        pt = node.parmTuple(parm_name)
        if pt is None:
            raise ValueError(f"Parameter not found: {parm_name!r}")
        pt.set(value if isinstance(value, (list, tuple)) else [value])
    else:
        parm.set(value)


def _parm_get(node_path: str, parm_name: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path!r}")
            parm = node.parm(parm_name)
            if parm is None:
                pt = node.parmTuple(parm_name)
                if pt is None:
                    raise ValueError(f"Parameter not found: {parm_name!r} on {node_path!r}")
                return ok({"name": parm_name, "value": list(pt.eval())})
            return ok({"name": parm_name, "value": parm.eval()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_set(node_path: str, parm_name: str, value):
    try:
        def work():
            with hou.undos.group("mcp: set parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                _set_node_parm(node, parm_name, value)
            return ok({"node": node_path, "parm": parm_name, "value": value})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_set_many(items: list):
    try:
        def work():
            with hou.undos.group("mcp: set many parms"):
                changed = []
                for index, item in enumerate(items):
                    node_path = item.get("node_path")
                    parm_name = item.get("parm_name")
                    if not node_path:
                        raise ValueError(f"Missing node_path in item {index}")
                    if not parm_name:
                        raise ValueError(f"Missing parm_name in item {index}")
                    node = hou.node(node_path)
                    if node is None:
                        raise ValueError(f"Node not found: {node_path!r}")
                    value = item.get("value")
                    _set_node_parm(node, parm_name, value)
                    changed.append({"node": node_path, "parm": parm_name, "value": value})
                return ok({"count": len(changed), "items": changed})
        return dispatch(work, label="parm_set_many")
    except Exception as e:
        return err(e)


def _parm_set_expression(node_path: str, parm_name: str,
                          expr: str, language: str = "python"):
    try:
        def work():
            with hou.undos.group("mcp: set expression"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name!r}")
                lang = (hou.exprLanguage.Python if language == "python"
                        else hou.exprLanguage.Hscript)
                parm.setExpression(expr, lang)
            return ok({"node": node_path, "parm": parm_name, "expression": expr,
                       "language": language})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_get_all(node_path: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path!r}")
            params = {}
            for p in node.parms():
                try:
                    params[p.name()] = p.eval()
                except Exception:
                    params[p.name()] = None
            return ok({"node": node_path, "parameters": params})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_revert(node_path: str, parm_name: str):
    try:
        def work():
            with hou.undos.group("mcp: revert parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name!r}")
                parm.revertToDefaults()
            return ok({"reverted": parm_name})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_lock(node_path: str, parm_name: str, on: bool):
    try:
        def work():
            with hou.undos.group("mcp: lock parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name!r}")
                parm.lock(on)
            return ok({"parm": parm_name, "locked": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframe_set(node_path: str, parm_name: str,
                        frame: "float | None" = None,
                        value: "float | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: set keyframe"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name!r}")
                kf = hou.Keyframe()
                kf.setFrame(frame if frame is not None else hou.frame())
                kf.setValue(value if value is not None else parm.eval())
                parm.setKeyframe(kf)
                return ok({"parm": parm_name, "frame": kf.frame(),
                           "value": kf.value()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframe_delete(node_path: str, parm_name: str, frame: float):
    try:
        def work():
            with hou.undos.group("mcp: delete keyframe"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name!r}")
                parm.deleteKeyframeAtFrame(frame)
            return ok({"parm": parm_name, "deleted_frame": frame})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframes_list(node_path: str, parm_name: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path!r}")
            parm = node.parm(parm_name)
            if parm is None:
                raise ValueError(f"Parameter not found: {parm_name!r}")
            kfs = []
            for kf in parm.keyframes():
                entry: dict = {"frame": kf.frame()}
                try:
                    entry["value"] = kf.value()
                except Exception:
                    pass
                try:
                    entry["expression"] = kf.expression()
                except Exception:
                    pass
                kfs.append(entry)
            return ok({"parm": parm_name, "keyframes": kfs})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_link(src_node: str, src_parm: str,
               dst_node: str, dst_parm: str):
    try:
        def work():
            with hou.undos.group("mcp: link parm"):
                dst = hou.node(dst_node)
                if dst is None:
                    raise ValueError(f"Dest node not found: {dst_node!r}")
                p = dst.parm(dst_parm)
                if p is None:
                    raise ValueError(f"Dest parm not found: {dst_parm!r}")
                expr = f'ch("{src_node}/{src_parm}")'
                p.setExpression(expr, hou.exprLanguage.Hscript)
            return ok({"linked": f"{dst_node}/{dst_parm} -> {src_node}/{src_parm}"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    """Register all 11 parameter tools."""
    import json

    @app.tool("parm_get")
    async def parm_get(node_path: str, parm_name: str) -> list:
        """Get the evaluated value of a parameter or parameter tuple."""
        return [{"type": "text", "text": json.dumps(_parm_get(node_path, parm_name))}]

    @app.tool("parm_set")
    async def parm_set(node_path: str, parm_name: str, value) -> list:
        """Set a parameter value. Use a list for vector/tuple params like 't' or 's'."""
        return [{"type": "text", "text": json.dumps(_parm_set(node_path, parm_name, value))}]

    @app.tool("parm_set_many")
    async def parm_set_many(items: list) -> list:
        """Set many parameter values in one undo group. items: [{node_path, parm_name, value}]."""
        return [{"type": "text", "text": json.dumps(_parm_set_many(items))}]

    @app.tool("parm_set_expression")
    async def parm_set_expression(node_path: str, parm_name: str,
                                   expr: str, language: str = "python") -> list:
        """Set a channel expression. language: 'python' (default) or 'hscript'."""
        return [{"type": "text", "text": json.dumps(
            _parm_set_expression(node_path, parm_name, expr, language)
        )}]

    @app.tool("parm_get_all")
    async def parm_get_all(node_path: str) -> list:
        """Get all parameters of a node with their current evaluated values."""
        return [{"type": "text", "text": json.dumps(_parm_get_all(node_path))}]

    @app.tool("parm_revert")
    async def parm_revert(node_path: str, parm_name: str) -> list:
        """Revert a parameter to its default value."""
        return [{"type": "text", "text": json.dumps(_parm_revert(node_path, parm_name))}]

    @app.tool("parm_lock")
    async def parm_lock(node_path: str, parm_name: str, on: bool) -> list:
        """Lock or unlock a parameter to prevent changes."""
        return [{"type": "text", "text": json.dumps(_parm_lock(node_path, parm_name, on))}]

    @app.tool("parm_keyframe_set")
    async def parm_keyframe_set(node_path: str, parm_name: str,
                                 frame: "float | None" = None,
                                 value: "float | None" = None) -> list:
        """Set a keyframe. Defaults to current frame and current value if omitted."""
        return [{"type": "text", "text": json.dumps(
            _parm_keyframe_set(node_path, parm_name, frame, value)
        )}]

    @app.tool("parm_keyframe_delete")
    async def parm_keyframe_delete(node_path: str, parm_name: str, frame: float) -> list:
        """Delete the keyframe at a specific frame number."""
        return [{"type": "text", "text": json.dumps(
            _parm_keyframe_delete(node_path, parm_name, frame)
        )}]

    @app.tool("parm_keyframes_list")
    async def parm_keyframes_list(node_path: str, parm_name: str) -> list:
        """List all keyframes on a parameter with values and expressions."""
        return [{"type": "text", "text": json.dumps(_parm_keyframes_list(node_path, parm_name))}]

    @app.tool("parm_link")
    async def parm_link(src_node: str, src_parm: str,
                         dst_node: str, dst_parm: str) -> list:
        """Link dst_node/dst_parm to src_node/src_parm via ch() hscript expression."""
        return [{"type": "text", "text": json.dumps(
            _parm_link(src_node, src_parm, dst_node, dst_parm)
        )}]
