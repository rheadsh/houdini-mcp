"""ROP rendering tools."""
import threading
import time
import uuid

import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import as_text

# Output parameter names by renderer (tried in priority order)
_OUTPUT_PARMS = [
    "vm_picture",               # Mantra (ifd)
    "picture",                  # Karma (lop)
    "ri_display",               # RenderMan / PRMan
    "copoutput",                # COP2 ROP
    "outputimage",              # generic / Indie
    "RS_outputFileNamePrefix",  # Redshift
    "ar_picture",               # Arnold (HtoA)
]


_RENDER_JOBS = {}
_RENDER_JOBS_LOCK = threading.Lock()


def _now():
    return time.time()


def _job_update(job_id: str, **updates):
    with _RENDER_JOBS_LOCK:
        job = _RENDER_JOBS.setdefault(job_id, {"job_id": job_id})
        job.update(updates)
        return dict(job)


def _job_snapshot(job_id: str):
    with _RENDER_JOBS_LOCK:
        job = _RENDER_JOBS.get(job_id)
        return dict(job) if job else None


def _normalize_frame_range(frame_range, step: float):
    try:
        step = float(step)
    except (TypeError, ValueError) as exc:
        raise ValueError("step must be a positive number") from exc
    if step <= 0:
        raise ValueError("step must be a positive number")

    if frame_range is None:
        return None, step
    if not isinstance(frame_range, (list, tuple)) or len(frame_range) != 2:
        raise ValueError("frame_range must be [start, end]")
    try:
        start = float(frame_range[0])
        end = float(frame_range[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("frame_range values must be numbers") from exc
    if end < start:
        raise ValueError("frame_range end must be >= start")
    return [start, end], step


def _render_args(frame_range, step: float, verbose: bool = False):
    kwargs = {}
    if frame_range is not None:
        kwargs["frame_range"] = (frame_range[0], frame_range[1], step)
    if verbose:
        kwargs["verbose"] = True
        kwargs["output_progress"] = True
    return kwargs


def _node_output(node):
    for parm_name in _OUTPUT_PARMS:
        parm = node.parm(parm_name)
        if parm is not None:
            return {"output": parm.eval(), "parm": parm_name}
    return {"output": None, "parm": None}


def _render_metadata(rop_path: str, frame_range, step: float, verbose: bool,
                     mode: str):
    return {
        "path": rop_path,
        "frame_range": frame_range,
        "step": step,
        "verbose": bool(verbose),
        "mode": mode,
    }


def _call_render(node, frame_range, step: float, verbose: bool = False,
                 extra_kwargs=None):
    kwargs = _render_args(frame_range, step, verbose)
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    if kwargs:
        node.render(**kwargs)
    else:
        node.render()
    return kwargs


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
                step: float = 1.0, verbose: bool = False):
    try:
        frame_range, step = _normalize_frame_range(frame_range, step)

        def work():
            node = hou.node(rop_path)
            if node is None:
                raise ValueError(f"ROP not found: {rop_path!r}")
            started = _now()
            render_kwargs = _call_render(node, frame_range, step, verbose)
            data = _render_metadata(rop_path, frame_range, step, verbose,
                                    "blocking")
            data.update({
                "rendered": rop_path,
                "render_kwargs": dict(render_kwargs),
                "started_at": started,
                "finished_at": _now(),
            })
            if verbose:
                data.update(_node_output(node))
            return ok(data)
        return dispatch(work, label="rop_render")
    except Exception as e:
        return err(e)


def _rop_render_start(rop_path: str, frame_range: "list | None" = None,
                      step: float = 1.0, verbose: bool = False):
    try:
        frame_range, step = _normalize_frame_range(frame_range, step)

        def work():
            node = hou.node(rop_path)
            if node is None:
                raise ValueError(f"ROP not found: {rop_path!r}")

            job_id = f"rop-{uuid.uuid4().hex}"
            started = _now()
            base = _render_metadata(rop_path, frame_range, step, verbose,
                                    "nonblocking")
            _job_update(job_id, status="starting", started_at=started, **base)

            attempts = (
                {"block": False},
                {"blocking": False},
            )
            errors = []
            for extra in attempts:
                try:
                    render_kwargs = _call_render(node, frame_range, step,
                                                 verbose, extra)
                    data = _job_update(job_id, status="running",
                                       render_kwargs=dict(render_kwargs),
                                       nonblocking_arg=dict(extra))
                    data["note"] = (
                        "Render was started with Houdini non-blocking API. "
                        "Use rop_render_job_status or rop_render_status to poll."
                    )
                    return ok(data)
                except TypeError as exc:
                    errors.append(str(exc))

            render_kwargs = _call_render(node, frame_range, step, verbose)
            data = _job_update(job_id, status="completed", mode="blocking",
                               render_kwargs=dict(render_kwargs),
                               finished_at=_now(),
                               fallback_errors=errors)
            data["note"] = (
                "ROP render API did not accept non-blocking arguments; "
                "render completed before returning."
            )
            return ok(data)
        return dispatch(work, label="rop_render_start")
    except Exception as e:
        return err(e)


def _rop_render_job_status(job_id: str):
    try:
        def work():
            job = _job_snapshot(job_id)
            if job is None:
                raise ValueError(f"Render job not found: {job_id!r}")
            rop_path = job.get("path")
            if rop_path:
                node = hou.node(rop_path)
                if node is not None:
                    job["is_cooking"] = getattr(node, "isCooking", lambda: False)()
                    if job.get("status") == "running" and not job["is_cooking"]:
                        job["status"] = "unknown_or_completed"
            return ok(job)
        return dispatch(work, label="rop_render_job_status")
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

    @app.tool("rop_list")
    async def rop_list(network_path: str = "/out") -> list:
        """List all ROP nodes in a network (default: /out)."""
        return as_text(_rop_list(network_path))

    @app.tool("rop_render")
    async def rop_render(rop_path: str, frame_range: "list | None" = None,
                          step: float = 1.0, verbose: bool = False) -> list:
        """Execute a ROP render. frame_range: [start, end]. WARNING: This is blocking."""
        return as_text(_rop_render(rop_path, frame_range, step, verbose))

    @app.tool("rop_render_start")
    async def rop_render_start(rop_path: str, frame_range: "list | None" = None,
                               step: float = 1.0, verbose: bool = False) -> list:
        """Start a ROP render with Houdini non-blocking API when available; returns job metadata."""
        return as_text(_rop_render_start(rop_path, frame_range, step, verbose))

    @app.tool("rop_render_async")
    async def rop_render_async(rop_path: str, frame_range: "list | None" = None,
                               step: float = 1.0, verbose: bool = False) -> list:
        """Alias for rop_render_start."""
        return as_text(_rop_render_start(rop_path, frame_range, step, verbose))

    @app.tool("rop_render_job_status")
    async def rop_render_job_status(job_id: str) -> list:
        """Return local metadata for a render job started by rop_render_start."""
        return as_text(_rop_render_job_status(job_id))

    @app.tool("rop_render_status")
    async def rop_render_status(rop_path: str) -> list:
        """Check whether a ROP is currently cooking."""
        return as_text(_rop_render_status(rop_path))

    @app.tool("rop_get_output")
    async def rop_get_output(rop_path: str) -> list:
        """Get the output file path from a ROP node (tries common parm names)."""
        return as_text(_rop_get_output(rop_path))

    @app.tool("rop_set_output")
    async def rop_set_output(rop_path: str, output_path: str) -> list:
        """Set the render output path on a ROP node."""
        return as_text(_rop_set_output(rop_path, output_path))

    @app.tool("rop_frame_range_override")
    async def rop_frame_range_override(rop_path: str, start: float, end: float) -> list:
        """Override the frame range on a ROP node (enables trange and sets f parm)."""
        return as_text(_rop_frame_range_override(rop_path, start, end))
