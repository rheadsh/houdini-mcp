"""Session and hip file management tools."""
import os
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import enforce_project_root, as_text

_HIP_SUFFIXES = (".hip", ".hiplc", ".hipnc")


def _validate_hip_path(path: str, must_exist: bool = False) -> str:
    """
    Validate and canonicalize a hip file path.

    Resolves symlinks (realpath) to defeat path-traversal attacks, enforces a
    .hip/.hiplc/.hipnc suffix, and optionally restricts to HOUDINI_MCP_PROJECT_ROOT.
    Returns the canonical path or raises ValueError.
    """
    real = os.path.realpath(path)
    if not any(real.lower().endswith(s) for s in _HIP_SUFFIXES):
        raise ValueError(
            f"Invalid extension for {os.path.basename(real)!r}. "
            "Only .hip, .hiplc, .hipnc are allowed."
        )
    enforce_project_root(real)
    if must_exist and not os.path.isfile(real):
        raise ValueError(f"File not found: {real!r}")
    return real


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
        return dispatch(work, label="session_info")
    except Exception as e:
        return err(e)


def _hip_info():
    try:
        def work():
            return ok({
                "path": hou.hipFile.path(),
                "has_unsaved_changes": hou.hipFile.hasUnsavedChanges(),
            })
        return dispatch(work, label="hip_info")
    except Exception as e:
        return err(e)


def _hip_new():
    try:
        def work():
            hou.hipFile.clear(suppress_save_prompt=True)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work, label="hip_new")
    except Exception as e:
        return err(e)


def _hip_load(path: str):
    try:
        safe = _validate_hip_path(path, must_exist=True)

        def work():
            hou.hipFile.load(safe, suppress_save_prompt=True)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work, label="hip_load")
    except Exception as e:
        return err(e)


def _hip_save(path: "str | None" = None):
    try:
        safe: "str | None" = _validate_hip_path(path) if path is not None else None

        def work():
            hou.hipFile.save(safe)
            return ok({"path": hou.hipFile.path()})
        return dispatch(work, label="hip_save")
    except Exception as e:
        return err(e)


def _hip_merge(path: str):
    try:
        safe = _validate_hip_path(path, must_exist=True)

        def work():
            hou.hipFile.merge(safe)
            return ok({"merged": safe})
        return dispatch(work, label="hip_merge")
    except Exception as e:
        return err(e)


def register(app):
    """Register all session tools with the MCP app."""

    @app.tool("session_info")
    async def session_info() -> list:
        """Get Houdini version, application name, user and UI availability."""
        return as_text(_session_info())

    @app.tool("hip_info")
    async def hip_info() -> list:
        """Get current scene file path and unsaved-changes status."""
        return as_text(_hip_info())

    @app.tool("hip_new")
    async def hip_new() -> list:
        """Clear the scene (new empty hip file). Unsaved changes will be lost."""
        return as_text(_hip_new())

    @app.tool("hip_load")
    async def hip_load(path: str) -> list:
        """Load a .hip or .hiplc file from disk."""
        return as_text(_hip_load(path))

    @app.tool("hip_save")
    async def hip_save(path: "str | None" = None) -> list:
        """Save the current scene. Uses current path if path is omitted."""
        return as_text(_hip_save(path))

    @app.tool("hip_merge")
    async def hip_merge(path: str) -> list:
        """Merge another .hip file into the current scene."""
        return as_text(_hip_merge(path))
