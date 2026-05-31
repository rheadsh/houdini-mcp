"""Utility and miscellaneous tools."""
import sys
import platform
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _run_hscript(command: str):
    try:
        def work():
            stdout, stderr = hou.hscript(command)
            return ok({"stdout": stdout, "stderr": stderr})
        return dispatch(work, label="run_hscript")
    except Exception as e:
        return err(e)


def _eval_expression(expr: str):
    try:
        def work():
            result = hou.hscriptExpression(expr)
            return ok({"expression": expr, "result": result})
        return dispatch(work, label="eval_expression")
    except Exception as e:
        return err(e)


def _expand_string(template: str):
    try:
        def work():
            return ok({"template": template,
                       "expanded": hou.expandString(template)})
        return dispatch(work, label="expand_string")
    except Exception as e:
        return err(e)


def _find_file(filename: str):
    try:
        def work():
            try:
                found = hou.findFile(filename)
                return ok({"filename": filename, "path": found})
            except hou.OperationFailed:
                return ok({"filename": filename, "path": None,
                           "note": "File not found in $HOUDINI_PATH"})
        return dispatch(work, label="find_file")
    except Exception as e:
        return err(e)


def _path_list():
    try:
        def work():
            return ok({"paths": list(hou.houdiniPath())})
        return dispatch(work, label="path_list")
    except Exception as e:
        return err(e)


def _env_get(var_name: str):
    try:
        def work():
            return ok({"name": var_name,
                       "value": hou.getenv(var_name)})
        return dispatch(work, label="env_get")
    except Exception as e:
        return err(e)


def _env_set(var_name: str, value: str):
    try:
        def work():
            hou.putenv(var_name, value)
            return ok({"name": var_name, "value": value})
        return dispatch(work, label="env_set")
    except Exception as e:
        return err(e)


def _file_references():
    try:
        def work():
            refs = [
                {"parm": p.path(), "file": f}
                for p, f in hou.fileReferences()
            ]
            return ok({"references": refs, "count": len(refs)})
        return dispatch(work, label="file_references")
    except Exception as e:
        return err(e)


def _undo():
    try:
        def work():
            hou.undos.performUndo()
            return ok({"undone": True})
        return dispatch(work, label="undo")
    except Exception as e:
        return err(e)


def _redo():
    try:
        def work():
            hou.undos.performRedo()
            return ok({"redone": True})
        return dispatch(work, label="redo")
    except Exception as e:
        return err(e)


def _update_mode_set(mode: str):
    try:
        def work():
            mode_map = {
                "auto": hou.updateMode.AutoUpdate,
                "manual": hou.updateMode.Manual,
                "on_request": hou.updateMode.OnRequest,
            }
            m = mode_map.get(mode.lower())
            if m is None:
                raise ValueError(
                    f"Unknown update mode: {mode!r}. "
                    f"Valid: {list(mode_map)}"
                )
            hou.setUpdateMode(m)
            return ok({"mode": mode})
        return dispatch(work, label="update_mode_set")
    except Exception as e:
        return err(e)


def _viewport_screenshot(file_path: "str | None" = None):
    try:
        def work():
            if not hou.isUIAvailable():
                raise RuntimeError(
                    "viewport_screenshot requires an active Houdini UI. "
                    "Not available in headless mode."
                )
            ui = getattr(hou, 'ui', None)
            if ui is None:
                raise RuntimeError("hou.ui not available")
            import hou as _hou
            pane_tab_type = _hou.paneTabType
            viewer = ui.paneTabOfType(pane_tab_type.SceneViewer)
            if viewer is None:
                raise RuntimeError("No Scene Viewer pane tab found")
            out_path = file_path or "/tmp/mcp_screenshot.png"
            viewer.curViewport().saveViewToFile(out_path)
            return ok({"saved_to": out_path})
        return dispatch(work, label="viewport_screenshot")
    except Exception as e:
        return err(e)


def _node_bundle_list():
    try:
        def work():
            bundles = [
                {"name": b.name(), "count": len(b.nodes())}
                for b in hou.nodeBundles()
            ]
            return ok({"bundles": bundles, "count": len(bundles)})
        return dispatch(work, label="node_bundle_list")
    except Exception as e:
        return err(e)


def _houdini_env_diagnostics():
    try:
        def work():
            env_names = [
                "HOUDINI_MCP_ROOT",
                "HOUDINI_MCP_PORT",
                "HOUDINI_MCP_PROJECT_ROOT",
                "HOUDINI_MCP_DISPATCH_TIMEOUT",
                "HIP",
                "JOB",
                "HOUDINI_PATH",
            ]
            env = {name: hou.getenv(name) for name in env_names}
            return ok({
                "houdini": {
                    "version": hou.applicationVersionString(),
                    "name": hou.applicationName(),
                    "ui_available": hou.isUIAvailable(),
                    "user": hou.userName(),
                },
                "python": {
                    "version": sys.version.split()[0],
                    "executable": sys.executable,
                },
                "platform": platform.platform(),
                "houdini_path": list(hou.houdiniPath()),
                "env": env,
            })
        return dispatch(work, label="houdini_env_diagnostics")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("run_hscript")
    async def run_hscript(command: str) -> list:
        """Execute an hscript command. Returns stdout and stderr."""
        return [{"type": "text", "text": json.dumps(_run_hscript(command))}]

    @app.tool("eval_expression")
    async def eval_expression(expr: str) -> list:
        """Evaluate an hscript expression (e.g. '$HIP', '$F', 'strlen(\"hello\")')."""
        return [{"type": "text", "text": json.dumps(_eval_expression(expr))}]

    @app.tool("expand_string")
    async def expand_string(template: str) -> list:
        """Expand $VARIABLES and `hscript expressions` in a string."""
        return [{"type": "text", "text": json.dumps(_expand_string(template))}]

    @app.tool("find_file")
    async def find_file(filename: str) -> list:
        """Find a file by name in $HOUDINI_PATH. Returns the full path or null."""
        return [{"type": "text", "text": json.dumps(_find_file(filename))}]

    @app.tool("path_list")
    async def path_list() -> list:
        """List all directories in $HOUDINI_PATH."""
        return [{"type": "text", "text": json.dumps(_path_list())}]

    @app.tool("env_get")
    async def env_get(var_name: str) -> list:
        """Get the value of a Houdini environment variable."""
        return [{"type": "text", "text": json.dumps(_env_get(var_name))}]

    @app.tool("env_set")
    async def env_set(var_name: str, value: str) -> list:
        """Set a Houdini session environment variable."""
        return [{"type": "text", "text": json.dumps(_env_set(var_name, value))}]

    @app.tool("file_references")
    async def file_references() -> list:
        """List all external file references in the current scene."""
        return [{"type": "text", "text": json.dumps(_file_references())}]

    @app.tool("undo")
    async def undo() -> list:
        """Undo the last undoable action in Houdini."""
        return [{"type": "text", "text": json.dumps(_undo())}]

    @app.tool("redo")
    async def redo() -> list:
        """Redo the last undone action."""
        return [{"type": "text", "text": json.dumps(_redo())}]

    @app.tool("update_mode_set")
    async def update_mode_set(mode: str) -> list:
        """Set the scene update mode. mode: 'auto', 'manual', or 'on_request'."""
        return [{"type": "text", "text": json.dumps(_update_mode_set(mode))}]

    @app.tool("viewport_screenshot")
    async def viewport_screenshot(file_path: "str | None" = None) -> list:
        """Capture the active viewport to a PNG file. Requires Houdini UI."""
        return [{"type": "text", "text": json.dumps(_viewport_screenshot(file_path))}]

    @app.tool("node_bundle_list")
    async def node_bundle_list() -> list:
        """List all node bundles with their names and node counts."""
        return [{"type": "text", "text": json.dumps(_node_bundle_list())}]

    @app.tool("houdini_env_diagnostics")
    async def houdini_env_diagnostics() -> list:
        """Return Houdini/Python/environment diagnostics for studio support."""
        return [{"type": "text", "text": json.dumps(_houdini_env_diagnostics())}]
