"""PDG/TOP graph tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _pdg_cook(top_net_path: str):
    try:
        def work():
            node = hou.node(top_net_path)
            if node is None:
                raise ValueError(f"TOP network not found: {top_net_path!r}")
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
                target.dirtyAllTasks(remove_outputs=False)
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
            state = str(node.cookState())
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
            outputs = [str(f) for f in target.workItemOutputFiles()]
            return ok({"outputs": outputs, "count": len(outputs)})
        return dispatch(work, label="pdg_output_list")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("pdg_cook")
    async def pdg_cook(top_net_path: str) -> list:
        """Start cooking a PDG/TOP network asynchronously."""
        return [{"type": "text", "text": json.dumps(_pdg_cook(top_net_path))}]

    @app.tool("pdg_dirty")
    async def pdg_dirty(top_net_path: str, node_name: "str | None" = None) -> list:
        """Mark a TOP network or specific node as dirty (needs re-cook)."""
        return [{"type": "text", "text": json.dumps(_pdg_dirty(top_net_path, node_name))}]

    @app.tool("pdg_cancel")
    async def pdg_cancel(top_net_path: str) -> list:
        """Cancel an active PDG cook."""
        return [{"type": "text", "text": json.dumps(_pdg_cancel(top_net_path))}]

    @app.tool("pdg_status")
    async def pdg_status(top_net_path: str) -> list:
        """Get the current cook state of a TOP network."""
        return [{"type": "text", "text": json.dumps(_pdg_status(top_net_path))}]

    @app.tool("pdg_output_list")
    async def pdg_output_list(top_net_path: str, node_name: "str | None" = None) -> list:
        """List output file paths from PDG work items."""
        return [{"type": "text", "text": json.dumps(_pdg_output_list(top_net_path, node_name))}]
