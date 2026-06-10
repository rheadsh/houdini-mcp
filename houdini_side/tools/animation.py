"""Animation, time, and channel tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import as_text


def _time_get():
    try:
        def work():
            return ok({"frame": hou.frame(), "time": hou.time(),
                       "fps": hou.fps()})
        return dispatch(work, label="time_get")
    except Exception as e:
        return err(e)


def _time_set(frame: float):
    try:
        def work():
            hou.setFrame(frame)
            return ok({"frame": hou.frame()})
        return dispatch(work, label="time_set")
    except Exception as e:
        return err(e)


def _fps_get():
    try:
        def work():
            return ok({"fps": hou.fps()})
        return dispatch(work, label="fps_get")
    except Exception as e:
        return err(e)


def _fps_set(fps: float):
    try:
        def work():
            if fps <= 0:
                raise ValueError(f"FPS must be positive, got {fps!r}")
            hou.setFps(fps)
            return ok({"fps": hou.fps()})
        return dispatch(work, label="fps_set")
    except Exception as e:
        return err(e)


def _frame_range_get():
    try:
        def work():
            r = hou.playbar.frameRange()
            return ok({"start": r[0], "end": r[1]})
        return dispatch(work, label="frame_range_get")
    except Exception as e:
        return err(e)


def _frame_range_set(start: float, end: float):
    try:
        def work():
            if end < start:
                raise ValueError(
                    f"end ({end}) must be >= start ({start})"
                )
            hou.playbar.setFrameRange(start, end)
            return ok({"start": start, "end": end})
        return dispatch(work, label="frame_range_set")
    except Exception as e:
        return err(e)


def _channel_list(node_path: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path!r}")
            animated = [
                p.name() for p in node.parms()
                if p.keyframes()
            ]
            return ok({"node": node_path, "animated_parms": animated,
                       "count": len(animated)})
        return dispatch(work, label="channel_list")
    except Exception as e:
        return err(e)


def _keyframe_list(node_path: str, parm_name: str):
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
                try:
                    entry["slope"] = kf.slope()
                except Exception:
                    pass
                kfs.append(entry)
            return ok({"parm": parm_name, "keyframes": kfs,
                       "count": len(kfs)})
        return dispatch(work, label="keyframe_list")
    except Exception as e:
        return err(e)


def register(app):

    @app.tool("time_get")
    async def time_get() -> list:
        """Get current frame number, time in seconds, and scene FPS."""
        return as_text(_time_get())

    @app.tool("time_set")
    async def time_set(frame: float) -> list:
        """Jump to a specific frame number."""
        return as_text(_time_set(frame))

    @app.tool("fps_get")
    async def fps_get() -> list:
        """Get the scene frames-per-second rate."""
        return as_text(_fps_get())

    @app.tool("fps_set")
    async def fps_set(fps: float) -> list:
        """Set the scene FPS. Must be positive."""
        return as_text(_fps_set(fps))

    @app.tool("frame_range_get")
    async def frame_range_get() -> list:
        """Get the global playbar frame range (start, end)."""
        return as_text(_frame_range_get())

    @app.tool("frame_range_set")
    async def frame_range_set(start: float, end: float) -> list:
        """Set the global playbar frame range."""
        return as_text(_frame_range_set(start, end))

    @app.tool("channel_list")
    async def channel_list(node_path: str) -> list:
        """List all animated parameters (those with keyframes) on a node."""
        return as_text(_channel_list(node_path))

    @app.tool("keyframe_list")
    async def keyframe_list(node_path: str, parm_name: str) -> list:
        """List all keyframes on a parameter with frame, value, expression, slope."""
        return as_text(_keyframe_list(node_path, parm_name))
