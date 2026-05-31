"""Session and hip file management tools."""
import json
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err


def _session_info():
    try:
        def work():
            return ok({
                "version": hou.applicationVersionString(),
                "name": hou.applicationName(),
                "version_tuple": list(hou.applicationVersion()),
                "user": hou.userName(),
                "ui_available": hou.isUIAvailable(),
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _hip_info():
    try:
        def work():
            return ok({
                "path": hou.hipFile.path(),
                "has_unsaved_changes": hou.hipFile.hasUnsavedChanges(),
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _hip_new():
    try:
        def work():
            hou.hipFile.clear(suppress_save_prompt=True)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _hip_load(path: str):
    try:
        def work():
            hou.hipFile.load(path, suppress_save_prompt=True)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _hip_save(path=None):
    try:
        def work():
            hou.hipFile.save(path)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _hip_merge(path: str):
    try:
        def work():
            hou.hipFile.merge(path)
            return ok({"merged": path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    """Register all session tools with the MCP app."""

    @app.tool("session_info")
    async def session_info() -> list:
        """Get Houdini version, application name, user and UI availability."""
        return [{"type": "text", "text": json.dumps(_session_info())}]

    @app.tool("hip_info")
    async def hip_info() -> list:
        """Get current scene file path and unsaved-changes status."""
        return [{"type": "text", "text": json.dumps(_hip_info())}]

    @app.tool("hip_new")
    async def hip_new() -> list:
        """Clear the scene (new empty hip file). Unsaved changes will be lost."""
        return [{"type": "text", "text": json.dumps(_hip_new())}]

    @app.tool("hip_load")
    async def hip_load(path: str) -> list:
        """Load a .hip or .hiplc file from disk."""
        return [{"type": "text", "text": json.dumps(_hip_load(path))}]

    @app.tool("hip_save")
    async def hip_save(path: str = None) -> list:
        """Save the current scene. Uses current path if path is omitted."""
        return [{"type": "text", "text": json.dumps(_hip_save(path))}]

    @app.tool("hip_merge")
    async def hip_merge(path: str) -> list:
        """Merge another .hip file into the current scene."""
        return [{"type": "text", "text": json.dumps(_hip_merge(path))}]
