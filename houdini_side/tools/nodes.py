"""Node creation, deletion, wiring, flags, and network management tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _node_info(node):
    """Serialize a hou node to a plain dict."""
    try:
        inputs = [
            {"input_index": i, "node": c.node().path() if c and c.node() else None}
            for i, c in enumerate(node.inputs())
        ]
    except Exception:
        inputs = []
    try:
        outputs = [
            {"output_index": i, "node": c.node().path() if c and c.node() else None}
            for i, c in enumerate(node.outputs())
        ]
    except Exception:
        outputs = []
    try:
        pos = node.position()
        position = [pos[0], pos[1]]
    except Exception:
        position = [0.0, 0.0]
    try:
        color_rgb = list(node.color().rgb())
    except Exception:
        color_rgb = [0.6, 0.6, 0.6]
    return {
        "path": node.path(),
        "name": node.name(),
        "type": node.type().name(),
        "parent": node.parent().path() if node.parent() else None,
        "is_bypassed": node.isBypassed(),
        "display_flag": node.isDisplayFlagSet(),
        "render_flag": node.isRenderFlagSet(),
        "color": color_rgb,
        "position": position,
        "comment": node.comment(),
        "inputs": inputs,
        "outputs": outputs,
    }


def _node_get(path: str):
    try:
        def work():
            node = hou.node(path)
            if node is None:
                raise ValueError(f"Node not found: {path!r}")
            return ok(_node_info(node))
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_list(network_path: str, type_filter: "str | None" = None):
    try:
        def work():
            parent = hou.node(network_path)
            if parent is None:
                raise ValueError(f"Network not found: {network_path!r}")
            children = parent.children()
            if type_filter:
                children = [c for c in children if c.type().name() == type_filter]
            return ok({"nodes": [_node_info(c) for c in children]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_create(parent_path: str, node_type: str, name: "str | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: create node"):
                parent = hou.node(parent_path)
                if parent is None:
                    raise ValueError(f"Parent network not found: {parent_path!r}")
                node = parent.createNode(node_type, name)
                return ok(_node_info(node))
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_delete(path: str):
    try:
        def work():
            with hou.undos.group("mcp: delete node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                node.destroy()
            return ok({"deleted": path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_rename(path: str, new_name: str):
    try:
        def work():
            with hou.undos.group("mcp: rename node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                node.setName(new_name)
                return ok({"path": node.path(), "name": node.name()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_move(path: str, x: float, y: float):
    try:
        def work():
            with hou.undos.group("mcp: move node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                node.setPosition(hou.Vector2(x, y))
            return ok({"path": path, "position": [x, y]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_connect(from_path: str, from_output: int,
                  to_path: str, to_input: int):
    try:
        def work():
            with hou.undos.group("mcp: connect nodes"):
                src = hou.node(from_path)
                dst = hou.node(to_path)
                if src is None:
                    raise ValueError(f"Source node not found: {from_path!r}")
                if dst is None:
                    raise ValueError(f"Dest node not found: {to_path!r}")
                dst.setInput(to_input, src, from_output)
            return ok({"connected": f"{from_path}[{from_output}]->{to_path}[{to_input}]"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_disconnect(to_path: str, to_input: int):
    try:
        def work():
            with hou.undos.group("mcp: disconnect node"):
                dst = hou.node(to_path)
                if dst is None:
                    raise ValueError(f"Node not found: {to_path!r}")
                dst.setInput(to_input, None)
            return ok({"disconnected": f"{to_path}[{to_input}]"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_bypass(path: str, on: bool):
    try:
        def work():
            with hou.undos.group("mcp: bypass node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                node.bypass(on)
            return ok({"path": path, "bypassed": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


_FLAG_METHODS = {
    "display": "setDisplayFlag",
    "render": "setRenderFlag",
    "template": "setTemplateFlag",
    "highlight": "setHighlightFlag",
    "bypass": "bypass",
}


def _node_set_flag(path: str, flag: str, on: bool):
    try:
        def work():
            method_name = _FLAG_METHODS.get(flag)
            if not method_name:
                raise ValueError(
                    f"Unknown flag: {flag!r}. Valid: {list(_FLAG_METHODS)}"
                )
            with hou.undos.group(f"mcp: set flag {flag}"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                getattr(node, method_name)(on)
            return ok({"path": path, "flag": flag, "value": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_cook(path: str):
    try:
        def work():
            node = hou.node(path)
            if node is None:
                raise ValueError(f"Node not found: {path!r}")
            node.cook(force=True)
            return ok({"cooked": path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_layout(network_path: str):
    try:
        def work():
            with hou.undos.group("mcp: layout network"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path!r}")
                parent.layoutChildren()
            return ok({"laid_out": network_path})
        return dispatch(work)
    except Exception as e:
        return err(e)


_CONTEXT_CATEGORIES = {
    "sop": "sopNodeTypeCategory",
    "obj": "objNodeTypeCategory",
    "dop": "dopNodeTypeCategory",
    "rop": "ropNodeTypeCategory",
    "lop": "lopNodeTypeCategory",
    "top": "topNodeTypeCategory",
    "cop2": "cop2NodeTypeCategory",
    "vop": "vopNodeTypeCategory",
    "shop": "shopNodeTypeCategory",
    "chop": "chopNodeTypeCategory",
}


def _node_type_list(context: str):
    try:
        def work():
            fn_name = _CONTEXT_CATEGORIES.get(context.lower())
            if not fn_name:
                raise ValueError(
                    f"Unknown context: {context!r}. Valid: {list(_CONTEXT_CATEGORIES)}"
                )
            cat = getattr(hou, fn_name)()
            types_list = sorted(cat.nodeTypes().keys())
            return ok({"context": context, "types": types_list})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_copy_paste(source_paths: list, dest_network: str):
    try:
        def work():
            with hou.undos.group("mcp: copy-paste nodes"):
                nodes = []
                for p in source_paths:
                    n = hou.node(p)
                    if n is None:
                        raise ValueError(f"Source node not found: {p!r}")
                    nodes.append(n)
                dest = hou.node(dest_network)
                if dest is None:
                    raise ValueError(f"Dest network not found: {dest_network!r}")
                pasted = hou.copyNodesTo(nodes, dest)
                return ok({"pasted": [n.path() for n in pasted]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _network_box_create(network_path: str, name: str,
                         color: "list | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: create network box"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path!r}")
                box = parent.createNetworkBox()
                box.setComment(name)
                if color:
                    box.setColor(hou.Color(color))
                return ok({"comment": name})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _sticky_note_create(network_path: str, text: str,
                         x: float, y: float):
    try:
        def work():
            with hou.undos.group("mcp: create sticky note"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path!r}")
                note = parent.createStickyNote()
                note.setText(text)
                note.setPosition(hou.Vector2(x, y))
                return ok({"text": text, "position": [x, y]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    """Register all 16 node management tools."""
    import json

    @app.tool("node_get")
    async def node_get(path: str) -> list:
        """Get info about a node: type, flags, connections, color, position."""
        return [{"type": "text", "text": json.dumps(_node_get(path))}]

    @app.tool("node_list")
    async def node_list(network_path: str, type_filter: "str | None" = None) -> list:
        """List all children of a network. Optional type_filter (e.g. 'box')."""
        return [{"type": "text", "text": json.dumps(_node_list(network_path, type_filter))}]

    @app.tool("node_create")
    async def node_create(parent_path: str, node_type: str, name: "str | None" = None) -> list:
        """Create a node inside a network. Use node_type_list to get valid types."""
        return [{"type": "text", "text": json.dumps(_node_create(parent_path, node_type, name))}]

    @app.tool("node_delete")
    async def node_delete(path: str) -> list:
        """Delete a node permanently (undoable)."""
        return [{"type": "text", "text": json.dumps(_node_delete(path))}]

    @app.tool("node_rename")
    async def node_rename(path: str, new_name: str) -> list:
        """Rename a node."""
        return [{"type": "text", "text": json.dumps(_node_rename(path, new_name))}]

    @app.tool("node_move")
    async def node_move(path: str, x: float, y: float) -> list:
        """Move a node to (x, y) in the network editor."""
        return [{"type": "text", "text": json.dumps(_node_move(path, x, y))}]

    @app.tool("node_connect")
    async def node_connect(from_path: str, from_output: int,
                            to_path: str, to_input: int) -> list:
        """Wire from_path[from_output] to to_path[to_input]."""
        return [{"type": "text", "text": json.dumps(
            _node_connect(from_path, from_output, to_path, to_input)
        )}]

    @app.tool("node_disconnect")
    async def node_disconnect(to_path: str, to_input: int) -> list:
        """Disconnect an input on a node."""
        return [{"type": "text", "text": json.dumps(_node_disconnect(to_path, to_input))}]

    @app.tool("node_bypass")
    async def node_bypass(path: str, on: bool) -> list:
        """Toggle bypass flag on a node."""
        return [{"type": "text", "text": json.dumps(_node_bypass(path, on))}]

    @app.tool("node_set_flag")
    async def node_set_flag(path: str, flag: str, on: bool) -> list:
        """Set a node flag. flag: display | render | template | highlight | bypass."""
        return [{"type": "text", "text": json.dumps(_node_set_flag(path, flag, on))}]

    @app.tool("node_cook")
    async def node_cook(path: str) -> list:
        """Force-cook a node."""
        return [{"type": "text", "text": json.dumps(_node_cook(path))}]

    @app.tool("node_layout")
    async def node_layout(network_path: str) -> list:
        """Auto-layout all nodes in a network."""
        return [{"type": "text", "text": json.dumps(_node_layout(network_path))}]

    @app.tool("node_type_list")
    async def node_type_list(context: str) -> list:
        """List all node types in context: sop|obj|dop|rop|lop|top|cop2|vop|shop|chop."""
        return [{"type": "text", "text": json.dumps(_node_type_list(context))}]

    @app.tool("node_copy_paste")
    async def node_copy_paste(source_paths: list, dest_network: str) -> list:
        """Copy nodes and paste them into dest_network."""
        return [{"type": "text", "text": json.dumps(_node_copy_paste(source_paths, dest_network))}]

    @app.tool("network_box_create")
    async def network_box_create(network_path: str, name: str,
                                  color: "list | None" = None) -> list:
        """Create a network box with a label. color is [r, g, b] floats 0-1."""
        return [{"type": "text", "text": json.dumps(_network_box_create(network_path, name, color))}]

    @app.tool("sticky_note_create")
    async def sticky_note_create(network_path: str, text: str,
                                  x: float, y: float) -> list:
        """Create a sticky note at position (x, y) in the network editor."""
        return [{"type": "text", "text": json.dumps(_sticky_note_create(network_path, text, x, y))}]
