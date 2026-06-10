"""Tool module registry.

Each module exposes a register(app) function. Modules are optional so a
Houdini build missing a feature (e.g. USD) degrades gracefully — but a
failed import is logged instead of silently dropping its tools.
"""
import importlib
import logging

log = logging.getLogger("houdini-mcp")

_MODULE_NAMES = [
    "session",
    "nodes",
    "parameters",
    "geometry",
    "transforms",
    "rendering",
    "animation",
    "hda",
    "dynamics",
    "solaris",
    "pdg",
    "takes",
    "vex",
    "utils",
]

ALL_REGISTERS = []
for _mod_name in _MODULE_NAMES:
    try:
        _mod = importlib.import_module(f".{_mod_name}", package=__name__)
        ALL_REGISTERS.append(_mod.register)
    except (ImportError, ModuleNotFoundError) as _exc:
        log.warning("Tool module %r not loaded: %s", _mod_name, _exc)
