"""VEX and VOP network tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import as_text, set_parm_value


def _vex_run(code: str, context: str = "sop"):
    """
    Execute VEX code via hou.runVex(). The exact API signature varies across
    Houdini versions. For reliable VEX execution, prefer vop_snippet_set to set
    code on an Attribute Wrangle, then use node_cook to execute it.
    """
    try:
        def work():
            run_vex = getattr(hou, "runVex", None)
            if run_vex is None:
                raise RuntimeError(
                    "hou.runVex() is not available in this Houdini version. "
                    "Use vop_snippet_set to set VEX code on an Attribute Wrangle node "
                    "and node_cook to execute it instead."
                )
            # hou.runVex(code, inputs_dict, context) — inputs/outputs are optional
            try:
                result = run_vex(code, {}, context)
            except TypeError:
                # Older API: hou.runVex(code, context)
                result = run_vex(code, context)
            return ok({"result": str(result), "context": context})
        return dispatch(work, label="vex_run")
    except Exception as e:
        return err(e)


def _vex_context_list():
    try:
        def work():
            ctxs = [{"name": c.name(), "label": str(c)} for c in hou.vexContexts()]
            return ok({"contexts": ctxs})
        return dispatch(work, label="vex_context_list")
    except Exception as e:
        return err(e)


def _vop_network_list(search_path: str = "/"):
    try:
        def work():
            root = hou.node(search_path)
            if root is None:
                raise ValueError(f"Search root not found: {search_path!r}")
            vop_cat = hou.vopNodeTypeCategory()
            results = []
            def _walk(node, depth=0):
                if depth > 50:
                    return
                for child in node.children():
                    if child.type().category() == vop_cat:
                        results.append(child.path())
                    try:
                        _walk(child, depth + 1)
                    except Exception:
                        pass
            _walk(root)
            return ok({"vop_networks": results, "count": len(results)})
        return dispatch(work, label="vop_network_list")
    except Exception as e:
        return err(e)


def _vop_node_create(vop_net_path: str, node_type: str,
                      name: "str | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: create vop node"):
                net = hou.node(vop_net_path)
                if net is None:
                    raise ValueError(f"VOP network not found: {vop_net_path!r}")
                node = net.createNode(node_type, name)
                return ok({"path": node.path(), "type": node_type})
        return dispatch(work, label="vop_node_create")
    except Exception as e:
        return err(e)


def _vop_node_connect(from_path: str, from_port: str,
                       to_path: str, to_port: str):
    try:
        def work():
            with hou.undos.group("mcp: connect vop"):
                src = hou.node(from_path)
                dst = hou.node(to_path)
                if src is None:
                    raise ValueError(f"Source VOP not found: {from_path!r}")
                if dst is None:
                    raise ValueError(f"Dest VOP not found: {to_path!r}")
                dst.setNamedInput(to_port, src, from_port)
                return ok({"connected": f"{from_path}.{from_port} -> {to_path}.{to_port}"})
        return dispatch(work, label="vop_node_connect")
    except Exception as e:
        return err(e)


def _vop_code_generate(vop_net_path: str):
    try:
        def work():
            node = hou.node(vop_net_path)
            if node is None:
                raise ValueError(f"VOP network not found: {vop_net_path!r}")
            try:
                code = node.type().definition().sections().get(
                    "VEXcode", None
                )
                if code:
                    return ok({"code": code.contents(), "source": "definition"})
            except Exception:
                pass
            # Fallback: try vopoutput parm
            p = node.parm("vopoutput")
            if p:
                return ok({"code": p.eval(), "source": "vopoutput"})
            return ok({"code": None, "note": "VEX code not accessible on this node type"})
        return dispatch(work, label="vop_code_generate")
    except Exception as e:
        return err(e)


def _vop_snippet_set(snippet_node_path: str, code: str):
    try:
        def work():
            with hou.undos.group("mcp: set vex snippet"):
                node = hou.node(snippet_node_path)
                if node is None:
                    raise ValueError(f"Snippet node not found: {snippet_node_path!r}")
                p = node.parm("snippet")
                if p is None:
                    # Try 'code' parm (vopsop)
                    p = node.parm("code")
                if p is None:
                    raise ValueError(
                        f"No 'snippet' or 'code' parm on {snippet_node_path!r}. "
                        "Use parm_set for other parm names."
                    )
                set_parm_value(p, code)
                return ok({"set_on": snippet_node_path, "parm": p.name()})
        return dispatch(work, label="vop_snippet_set")
    except Exception as e:
        return err(e)


def register(app):

    @app.tool("vex_run")
    async def vex_run(code: str, context: str = "sop") -> list:
        """Execute VEX code via hou.runVex(). context: sop, pop, cop2, etc.
        WARNING: this executes arbitrary VEX in the Houdini session."""
        return as_text(_vex_run(code, context))

    @app.tool("vex_context_list")
    async def vex_context_list() -> list:
        """List all available VEX contexts (sop, pop, cop2, chop, etc.)."""
        return as_text(_vex_context_list())

    @app.tool("vop_network_list")
    async def vop_network_list(search_path: str = "/") -> list:
        """Find all VOP networks in the scene tree starting from search_path."""
        return as_text(_vop_network_list(search_path))

    @app.tool("vop_node_create")
    async def vop_node_create(vop_net_path: str, node_type: str,
                               name: "str | None" = None) -> list:
        """Create a VOP node inside a VOP network."""
        return as_text(_vop_node_create(vop_net_path, node_type, name))

    @app.tool("vop_node_connect")
    async def vop_node_connect(from_path: str, from_port: str,
                                to_path: str, to_port: str) -> list:
        """Connect VOP nodes by named port (e.g. from_port='out', to_port='x')."""
        return as_text(_vop_node_connect(from_path, from_port, to_path, to_port))

    @app.tool("vop_code_generate")
    async def vop_code_generate(vop_net_path: str) -> list:
        """Retrieve the generated VEX code from a VOP network."""
        return as_text(_vop_code_generate(vop_net_path))

    @app.tool("vop_snippet_set")
    async def vop_snippet_set(snippet_node_path: str, code: str) -> list:
        """Set the VEX snippet code on an Attribute Wrangle, VOP SOP, etc."""
        return as_text(_vop_snippet_set(snippet_node_path, code))
