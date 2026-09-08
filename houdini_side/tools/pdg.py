"""PDG/TOP graph tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import as_text, as_list


def _safe_call(obj, name, default=None, *args, **kwargs):
    fn = getattr(obj, name, None)
    if fn is None:
        return default
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def _safe_attr_or_call(obj, name, default=None):
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def _state_name(value):
    if value is None:
        return None
    name = getattr(value, "name", None)
    if callable(name):
        try:
            return str(name())
        except TypeError:
            pass
    return str(value)


def _target_node(top_net_path: str, node_name: "str | None" = None):
    net = hou.node(top_net_path)
    if net is None:
        raise ValueError(f"TOP network not found: {top_net_path!r}")
    if not node_name:
        return net
    target = net.node(node_name)
    if target is None:
        raise ValueError(f"TOP node {node_name!r} not found in {top_net_path!r}")
    return target


def _collect_work_items(target):
    # H21/H22 expose workItems as a property on the underlying pdg.Node.
    # Keep method-style fallbacks for older Houdini versions.
    pdg_node = _safe_call(target, "getPDGNode")
    for owner in (pdg_node, target):
        if owner is None:
            continue
        for name in ("workItems", "allWorkItems", "workItemList"):
            items = _safe_attr_or_call(owner, name)
            if items is not None:
                return as_list(items)

    graph = _safe_call(target, "getPDGGraphContext")
    if graph is None:
        graph = _safe_call(target, "graphContext")
    if graph is not None:
        for name in ("workItems", "allWorkItems"):
            items = _safe_attr_or_call(graph, name)
            if items is not None:
                return as_list(items)
    return []


def _file_path(value):
    path = _safe_attr_or_call(value, "path")
    return str(path if path is not None else value)


def _work_item_outputs(item):
    outputs = _safe_attr_or_call(item, "outputFiles")
    if outputs is None:
        outputs = _safe_attr_or_call(item, "expectedOutputFiles")
    if outputs is None:
        outputs = _safe_attr_or_call(item, "outputs", [])
    return [_file_path(value) for value in as_list(outputs)]


def _work_item_logs(item):
    logs = []
    for method_name in ("logMessages", "messages", "logs"):
        values = _safe_call(item, method_name)
        if values:
            logs.extend(str(value) for value in values)

    for attr_name in ("log", "logPath", "logFile"):
        value = _safe_attr_or_call(item, attr_name)
        if value:
            logs.append(str(value))
    return logs


def _work_item_info(item, include_logs: bool = False):
    info = {
        "id": _safe_attr_or_call(item, "id"),
        "index": _safe_attr_or_call(item, "index"),
        "name": _safe_attr_or_call(item, "name"),
        "state": _state_name(_safe_attr_or_call(item, "state")),
        "node": str(_safe_attr_or_call(item, "node", "")),
        "outputs": _work_item_outputs(item),
    }
    if info["name"] is None:
        info["name"] = str(item)
    if include_logs:
        info["logs"] = _work_item_logs(item)
    return info


def _is_failed_item(item):
    failed = _safe_attr_or_call(item, "isFailed")
    if failed is not None:
        return bool(failed)
    state = (_state_name(_safe_attr_or_call(item, "state")) or "").lower()
    return "fail" in state or "error" in state


def _pdg_cook(top_net_path: str):
    try:
        def work():
            node = hou.node(top_net_path)
            if node is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
            cook = getattr(node, "cookWorkItems", None)
            if cook is not None:
                cook(block=False)
            else:
                node.executeGraph(block=False)
            return ok({"cooking": top_net_path})
        return dispatch(work, label="pdg_cook")
    except Exception as e:
        return err(e)


def _pdg_dirty(top_net_path: str, node_name: "str | None" = None):
    try:
        def work():
            net = hou.node(top_net_path)
            if net is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
            if node_name:
                target = net.node(node_name)
                if target is None:
                    raise ValueError(f"TOP node {node_name!r} not found in {top_net_path!r}")
                dirty = getattr(target, "dirtyAllWorkItems", None)
                if dirty is not None:
                    dirty(remove_outputs=False)
                else:
                    target.dirtyAllTasks(remove_outputs=False)
            else:
                dirty = getattr(net, "dirtyAllWorkItems", None)
                if dirty is not None:
                    dirty(remove_outputs=False)
                else:
                    net.dirtyAllTasks(remove_outputs=False)
            return ok({"dirtied": node_name or top_net_path})
        return dispatch(work, label="pdg_dirty")
    except Exception as e:
        return err(e)


def _pdg_cancel(top_net_path: str):
    try:
        def work():
            node = hou.node(top_net_path)
            if node is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
            node.cancelCook()
            return ok({"cancelled": top_net_path})
        return dispatch(work, label="pdg_cancel")
    except Exception as e:
        return err(e)


def _pdg_status(top_net_path: str):
    try:
        def work():
            node = hou.node(top_net_path)
            if node is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
            get_state = getattr(node, "getCookState", None)
            state = str(get_state(False) if get_state is not None else node.cookState())
            return ok({"path": top_net_path, "state": state})
        return dispatch(work, label="pdg_status")
    except Exception as e:
        return err(e)


def _pdg_output_list(top_net_path: str, node_name: "str | None" = None):
    try:
        def work():
            net = hou.node(top_net_path)
            if net is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
            target = net.node(node_name) if node_name else net
            if target is None:
                raise ValueError(f"TOP node {node_name!r} not found")
            outputs = []
            for item in _collect_work_items(target):
                outputs.extend(_work_item_outputs(item))
            outputs = list(dict.fromkeys(outputs))
            return ok({"outputs": outputs, "count": len(outputs)})
        return dispatch(work, label="pdg_output_list")
    except Exception as e:
        return err(e)


def _pdg_workitems(top_net_path: str, node_name: "str | None" = None,
                   include_logs: bool = False):
    try:
        def work():
            target = _target_node(top_net_path, node_name)
            items = [_work_item_info(item, include_logs)
                     for item in _collect_work_items(target)]
            return ok({
                "path": top_net_path,
                "node": node_name,
                "workitems": items,
                "count": len(items),
            })
        return dispatch(work, label="pdg_workitems")
    except Exception as e:
        return err(e)


def _pdg_failed_items(top_net_path: str, node_name: "str | None" = None,
                      include_logs: bool = True):
    try:
        def work():
            target = _target_node(top_net_path, node_name)
            failed = [
                _work_item_info(item, include_logs)
                for item in _collect_work_items(target)
                if _is_failed_item(item)
            ]
            return ok({
                "path": top_net_path,
                "node": node_name,
                "failed_items": failed,
                "count": len(failed),
            })
        return dispatch(work, label="pdg_failed_items")
    except Exception as e:
        return err(e)


def _pdg_logs(top_net_path: str, node_name: "str | None" = None,
              failed_only: bool = False):
    try:
        def work():
            target = _target_node(top_net_path, node_name)
            entries = []
            for item in _collect_work_items(target):
                if failed_only and not _is_failed_item(item):
                    continue
                info = _work_item_info(item, include_logs=True)
                entries.append({
                    "id": info["id"],
                    "index": info["index"],
                    "name": info["name"],
                    "state": info["state"],
                    "logs": info["logs"],
                })
            return ok({
                "path": top_net_path,
                "node": node_name,
                "failed_only": failed_only,
                "logs": entries,
                "count": len(entries),
            })
        return dispatch(work, label="pdg_logs")
    except Exception as e:
        return err(e)


def register(app):

    @app.tool("pdg_cook")
    async def pdg_cook(top_net_path: str) -> list:
        """Start cooking a PDG/TOP network asynchronously."""
        return as_text(_pdg_cook(top_net_path))

    @app.tool("pdg_dirty")
    async def pdg_dirty(top_net_path: str, node_name: "str | None" = None) -> list:
        """Mark a TOP network or specific node as dirty (needs re-cook)."""
        return as_text(_pdg_dirty(top_net_path, node_name))

    @app.tool("pdg_cancel")
    async def pdg_cancel(top_net_path: str) -> list:
        """Cancel an active PDG cook."""
        return as_text(_pdg_cancel(top_net_path))

    @app.tool("pdg_status")
    async def pdg_status(top_net_path: str) -> list:
        """Get the current cook state of a TOP network."""
        return as_text(_pdg_status(top_net_path))

    @app.tool("pdg_output_list")
    async def pdg_output_list(top_net_path: str, node_name: "str | None" = None) -> list:
        """List output file paths from PDG work items."""
        return as_text(_pdg_output_list(top_net_path, node_name))

    @app.tool("pdg_workitems")
    async def pdg_workitems(top_net_path: str, node_name: "str | None" = None,
                            include_logs: bool = False) -> list:
        """List PDG work items with defensive metadata extraction."""
        return as_text(_pdg_workitems(top_net_path, node_name, include_logs))

    @app.tool("pdg_failed_items")
    async def pdg_failed_items(top_net_path: str, node_name: "str | None" = None,
                               include_logs: bool = True) -> list:
        """List failed PDG work items, including logs by default."""
        return as_text(_pdg_failed_items(top_net_path, node_name, include_logs))

    @app.tool("pdg_logs")
    async def pdg_logs(top_net_path: str, node_name: "str | None" = None,
                       failed_only: bool = False) -> list:
        """Collect log/message metadata from PDG work items."""
        return as_text(_pdg_logs(top_net_path, node_name, failed_only))
