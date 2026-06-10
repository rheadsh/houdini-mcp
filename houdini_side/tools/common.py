"""Shared helpers for production-oriented tool implementations."""
import os
from typing import Iterable


def enforce_project_root(real_path: str) -> None:
    """Raise ValueError if real_path escapes HOUDINI_MCP_PROJECT_ROOT (when set).

    real_path must already be canonical (os.path.realpath) so symlinks
    cannot be used to escape the root.
    """
    root = os.environ.get("HOUDINI_MCP_PROJECT_ROOT", "")
    if not root:
        return
    root_real = os.path.realpath(root)
    if not real_path.startswith(root_real + os.sep) and real_path != root_real:
        raise ValueError(
            f"Path {real_path!r} is outside HOUDINI_MCP_PROJECT_ROOT={root_real!r}."
        )


def resolve_output_path(
    hou_module,
    file_path: str,
    allowed_suffixes: Iterable[str] | None = None,
    create_dirs: bool = True,
) -> str:
    """Expand Houdini variables and optionally prepare a local output path.

    Enforces HOUDINI_MCP_PROJECT_ROOT confinement when that variable is set.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("file_path must be a non-empty string")

    expanded = hou_module.expandString(file_path)
    real = os.path.realpath(os.path.expanduser(expanded))

    suffixes = tuple(s.lower() for s in allowed_suffixes or ())
    if suffixes and not real.lower().endswith(suffixes):
        raise ValueError(
            f"Invalid output extension for {os.path.basename(real)!r}. "
            f"Allowed: {', '.join(suffixes)}"
        )

    enforce_project_root(real)

    if create_dirs:
        parent = os.path.dirname(real)
        if parent:
            os.makedirs(parent, exist_ok=True)

    return real


def validate_read_path(hou_module, file_path: str) -> str:
    """Validate a path Houdini will read, without rewriting it.

    Returns the original string (frame variables like $F must survive on
    file parms), but checks the expanded path against
    HOUDINI_MCP_PROJECT_ROOT when that variable is set.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("file_path must be a non-empty string")

    expanded = hou_module.expandString(file_path)
    real = os.path.realpath(os.path.expanduser(expanded))
    enforce_project_root(real)
    return file_path
