"""Node creation, deletion, wiring, flags, and network management tools."""
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
        return dispatch(work, label="node_get")
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
        return dispatch(work, label="node_list")
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
        return dispatch(work, label="node_create")
    except Exception as e:
        return err(e)


def _node_create_many(parent_path: str, specs: list):
    try:
        def work():
            with hou.undos.group("mcp: create many nodes"):
                parent = hou.node(parent_path)
                if parent is None:
                    raise ValueError(f"Parent network not found: {parent_path!r}")
                created = []
                for index, spec in enumerate(specs):
                    node_type = spec.get("node_type")
                    if not node_type:
                        raise ValueError(f"Missing node_type in spec {index}")
                    node = parent.createNode(node_type, spec.get("name"))
                    position = spec.get("position")
                    if position is not None:
                        if not (isinstance(position, (list, tuple)) and len(position) == 2):
                            raise ValueError(f"position must be [x, y] in spec {index}")
                        node.setPosition(hou.Vector2(position[0], position[1]))
                    parms = spec.get("parms")
                    if parms:
                        for parm_name, value in parms.items():
                            _set_node_parm(node, parm_name, value)
                    created.append(_node_info(node))
                return ok({"count": len(created), "nodes": created})
        return dispatch(work, label="node_create_many")
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
        return dispatch(work, label="node_delete")
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
        return dispatch(work, label="node_rename")
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
        return dispatch(work, label="node_move")
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
        return dispatch(work, label="node_connect")
    except Exception as e:
        return err(e)


def _node_connect_many(connections: list):
    try:
        def work():
            with hou.undos.group("mcp: connect many nodes"):
                connected = []
                for index, connection in enumerate(connections):
                    from_path = connection.get("from_path")
                    to_path = connection.get("to_path")
                    if not from_path:
                        raise ValueError(f"Missing from_path in connection {index}")
                    if not to_path:
                        raise ValueError(f"Missing to_path in connection {index}")
                    from_output = connection.get("from_output", 0)
                    to_input = connection.get("to_input", 0)
                    src = hou.node(from_path)
                    dst = hou.node(to_path)
                    if src is None:
                        raise ValueError(f"Source node not found: {from_path!r}")
                    if dst is None:
                        raise ValueError(f"Dest node not found: {to_path!r}")
                    dst.setInput(to_input, src, from_output)
                    connected.append(
                        {"from": from_path, "from_output": from_output,
                         "to": to_path, "to_input": to_input}
                    )
                return ok({"count": len(connected), "connections": connected})
        return dispatch(work, label="node_connect_many")
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
        return dispatch(work, label="node_disconnect")
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
        return dispatch(work, label="node_bypass")
    except Exception as e:
        return err(e)


_FLAG_METHODS = {
    "display": "setDisplayFlag",
    "render": "setRenderFlag",
    "template": "setTemplateFlag",
    "highlight": "setHighlightFlag",
    # Note: use node_bypass tool for bypass flag
}


def _node_set_flag(path: str, flag: str, on: bool):
    try:
        def work():
            method_name = _FLAG_METHODS.get(flag)
            if not method_name:
                raise ValueError(
                    f"Unknown flag: {flag!r}. Valid: display | render | template | highlight"
                )
            with hou.undos.group(f"mcp: set flag {flag}"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path!r}")
                getattr(node, method_name)(on)
                return ok({"path": path, "flag": flag, "value": on})
        return dispatch(work, label="node_set_flag")
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
        return dispatch(work, label="node_cook")
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
        return dispatch(work, label="node_layout")
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
        return dispatch(work, label="node_type_list")
    except Exception as e:
        return err(e)


def _parm_template_info(template):
    info = {}
    for key, method_name in (
        ("name", "name"),
        ("label", "label"),
        ("type", "type"),
        ("num_components", "numComponents"),
    ):
        try:
            value = getattr(template, method_name)()
            info[key] = str(value) if key == "type" else value
        except Exception:
            pass
    return info


def _node_type_info(context: str, node_type: str):
    try:
        def work():
            fn_name = _CONTEXT_CATEGORIES.get(context.lower())
            if not fn_name:
                raise ValueError(
                    f"Unknown context: {context!r}. Valid: {list(_CONTEXT_CATEGORIES)}"
                )
            cat = getattr(hou, fn_name)()
            node_types = cat.nodeTypes()
            nt = node_types.get(node_type)
            if nt is None:
                raise ValueError(f"Node type not found: {node_type!r} in {context!r}")

            data: dict = {"name": node_type, "category": context}
            for key, method_name in (
                ("description", "description"),
                ("label", "description"),
                ("min_inputs", "minNumInputs"),
                ("max_inputs", "maxNumInputs"),
            ):
                try:
                    data[key] = getattr(nt, method_name)()
                except Exception:
                    pass
            try:
                data["name"] = nt.name()
            except Exception:
                pass
            try:
                data["category"] = nt.category().name()
            except Exception:
                try:
                    data["category"] = cat.name()
                except Exception:
                    pass
            try:
                group = nt.parmTemplateGroup()
                templates = group.entries()
                data["parm_templates"] = [_parm_template_info(t) for t in templates]
            except Exception:
                pass
            return ok(data)
        return dispatch(work, label="node_type_info")
    except Exception as e:
        return err(e)


def _node_copy_paste(source_paths: list, network_path: str):
    try:
        def work():
            with hou.undos.group("mcp: copy-paste nodes"):
                nodes = []
                for p in source_paths:
                    n = hou.node(p)
                    if n is None:
                        raise ValueError(f"Source node not found: {p!r}")
                    nodes.append(n)
                dest = hou.node(network_path)
                if dest is None:
                    raise ValueError(f"Dest network not found: {network_path!r}")
                pasted = hou.copyNodesTo(nodes, dest)
                return ok({"pasted": [n.path() for n in pasted]})
        return dispatch(work, label="node_copy_paste")
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
                if color is not None:
                    if not (isinstance(color, (list, tuple)) and len(color) == 3
                            and all(isinstance(v, (int, float)) for v in color)):
                        raise ValueError(
                            f"color must be a list of exactly 3 numeric values (r, g, b), got: {color!r}"
                        )
                    box.setColor(hou.Color(color))
                return ok({"comment": name})
        return dispatch(work, label="network_box_create")
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
        return dispatch(work, label="sticky_note_create")
    except Exception as e:
        return err(e)


def register(app):
    """Register all 19 node management tools."""
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

    @app.tool("node_create_many")
    async def node_create_many(parent_path: str, specs: list) -> list:
        """Create many nodes in one undo group. specs: [{node_type, name?, position?, parms?}]."""
        return [{"type": "text", "text": json.dumps(_node_create_many(parent_path, specs))}]

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

    @app.tool("node_connect_many")
    async def node_connect_many(connections: list) -> list:
        """Wire many connections in one undo group. items: [{from_path, from_output, to_path, to_input}]."""
        return [{"type": "text", "text": json.dumps(_node_connect_many(connections))}]

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
        """Set a node flag. flag: display | render | template | highlight. Use node_bypass for bypass."""
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

    @app.tool("node_type_info")
    async def node_type_info(context: str, node_type: str) -> list:
        """Get metadata for one node type in context: sop|obj|dop|rop|lop|top|cop2|vop|shop|chop."""
        return [{"type": "text", "text": json.dumps(_node_type_info(context, node_type))}]

    @app.tool("node_copy_paste")
    async def node_copy_paste(source_paths: list, network_path: str) -> list:
        """Copy nodes and paste them into network_path."""
        return [{"type": "text", "text": json.dumps(_node_copy_paste(source_paths, network_path))}]

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
