"""ROP rendering tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err

# Output parameter names by renderer type (tried in order)
_OUTPUT_PARMS = ["vm_picture", "picture", "ri_display", "copoutput",
                 "outputimage", "RS_outputFileNamePrefix"]


def _rop_list(network_path: str = "/out"):
    try:
        def work():
            parent = hou.node(network_path)
            if parent is None:
                raise ValueError(f"Network not found: {network_path!r}")
            rop_cat = hou.ropNodeTypeCategory()
            rops = [
                {"path": c.path(), "type": c.type().name()}
                for c in parent.children()
                if c.type().category() == rop_cat
            ]
            return ok({"rops": rops, "network": network_path})
        return dispatch(work, label="rop_list")
    except Exception as e:
        return err(e)


def _rop_render(rop_path: str, frame_range: "list | None" = None,
                step: float = 1.0):
    try:
        def work():
            node = hou.node(rop_path)
            if node is None:
                raise ValueError(f"ROP not found: {rop_path!r}")
            if frame_range and len(frame_range) == 2:
                node.render(frame_range=(frame_range[0], frame_range[1], step))
            else:
                node.render()
            return ok({"rendered": rop_path,
                       "frame_range": frame_range})
        return dispatch(work, label="rop_render")
    except Exception as e:
        return err(e)


def _rop_render_status(rop_path: str):
    try:
        def work():
            node = hou.node(rop_path)
            if node is None:
                raise ValueError(f"ROP not found: {rop_path!r}")
            cooking = getattr(node, "isCooking", lambda: False)()
            return ok({"path": rop_path, "is_cooking": cooking})
        return dispatch(work, label="rop_render_status")
    except Exception as e:
        return err(e)


def _rop_get_output(rop_path: str):
    try:
        def work():
            node = hou.node(rop_path)
            if node is None:
                raise ValueError(f"ROP not found: {rop_path!r}")
            for parm_name in _OUTPUT_PARMS:
                p = node.parm(parm_name)
                if p is not None:
                    return ok({"path": rop_path, "output": p.eval(),
                               "parm": parm_name})
            return ok({"path": rop_path, "output": None,
                       "parm": None,
                       "note": "No known output parm found. Try parm_get_all."})
        return dispatch(work, label="rop_get_output")
    except Exception as e:
        return err(e)


def _rop_set_output(rop_path: str, output_path: str):
    try:
        def work():
            with hou.undos.group("mcp: set rop output"):
                node = hou.node(rop_path)
                if node is None:
                    raise ValueError(f"ROP not found: {rop_path!r}")
                for parm_name in _OUTPUT_PARMS:
                    p = node.parm(parm_name)
                    if p is not None:
                        p.set(output_path)
                        return ok({"path": rop_path, "output": output_path,
                                   "parm": parm_name})
                raise ValueError(
                    f"No known output parm on {rop_path!r}. "
                    f"Use parm_set directly with the correct parm name."
                )
        return dispatch(work, label="rop_set_output")
    except Exception as e:
        return err(e)


def _rop_frame_range_override(rop_path: str, start: float, end: float):
    try:
        def work():
            with hou.undos.group("mcp: set rop frame range"):
                node = hou.node(rop_path)
                if node is None:
                    raise ValueError(f"ROP not found: {rop_path!r}")
                # Enable frame range override
                trange = node.parm("trange")
                if trange:
                    trange.set(1)
                f_parm = node.parmTuple("f")
                if f_parm:
                    f_parm.set((start, end, 1))
                return ok({"path": rop_path, "start": start, "end": end})
        return dispatch(work, label="rop_frame_range_override")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("rop_list")
    async def rop_list(network_path: str = "/out") -> list:
        """List all ROP nodes in a network (default: /out)."""
        return [{"type": "text", "text": json.dumps(_rop_list(network_path))}]

    @app.tool("rop_render")
    async def rop_render(rop_path: str, frame_range: "list | None" = None,
                          step: float = 1.0) -> list:
        """Execute a ROP render. frame_range: [start, end]. WARNING: This is blocking."""
        return [{"type": "text", "text": json.dumps(_rop_render(rop_path, frame_range, step))}]

    @app.tool("rop_render_status")
    async def rop_render_status(rop_path: str) -> list:
        """Check whether a ROP is currently cooking."""
        return [{"type": "text", "text": json.dumps(_rop_render_status(rop_path))}]

    @app.tool("rop_get_output")
    async def rop_get_output(rop_path: str) -> list:
        """Get the output file path from a ROP node (tries common parm names)."""
        return [{"type": "text", "text": json.dumps(_rop_get_output(rop_path))}]

    @app.tool("rop_set_output")
    async def rop_set_output(rop_path: str, output_path: str) -> list:
        """Set the render output path on a ROP node."""
        return [{"type": "text", "text": json.dumps(_rop_set_output(rop_path, output_path))}]

    @app.tool("rop_frame_range_override")
    async def rop_frame_range_override(rop_path: str, start: float, end: float) -> list:
        """Override the frame range on a ROP node (enables trange and sets f parm)."""
        return [{"type": "text", "text": json.dumps(_rop_frame_range_override(rop_path, start, end))}]
