"""Shared helpers for production-oriented tool implementations."""
import os
from typing import Iterable


def resolve_output_path(
    hou_module,
    file_path: str,
    allowed_suffixes: Iterable[str] | None = None,
    create_dirs: bool = True,
) -> str:
    """Expand Houdini variables and optionally prepare a local output path."""
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

    if create_dirs:
        parent = os.path.dirname(real)
        if parent:
            os.makedirs(parent, exist_ok=True)

    return real
