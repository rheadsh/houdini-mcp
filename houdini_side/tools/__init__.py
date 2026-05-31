from .session import register as register_session

_optional_modules = [
    ("nodes", "register_nodes"),
    ("parameters", "register_parameters"),
    ("geometry", "register_geometry"),
    ("transforms", "register_transforms"),
    ("rendering", "register_rendering"),
    ("animation", "register_animation"),
    ("hda", "register_hda"),
    ("dynamics", "register_dynamics"),
    ("solaris", "register_solaris"),
    ("pdg", "register_pdg"),
    ("takes", "register_takes"),
    ("vex", "register_vex"),
    ("utils", "register_utils"),
]

_globals = globals()
for _mod_name, _reg_name in _optional_modules:
    try:
        import importlib as _importlib
        _mod = _importlib.import_module(f".{_mod_name}", package=__name__)
        _globals[_reg_name] = _mod.register
    except (ImportError, ModuleNotFoundError):
        _globals[_reg_name] = None

ALL_REGISTERS = [
    fn for fn in [
        register_session,
        _globals.get("register_nodes"),
        _globals.get("register_parameters"),
        _globals.get("register_geometry"),
        _globals.get("register_transforms"),
        _globals.get("register_rendering"),
        _globals.get("register_animation"),
        _globals.get("register_hda"),
        _globals.get("register_dynamics"),
        _globals.get("register_solaris"),
        _globals.get("register_pdg"),
        _globals.get("register_takes"),
        _globals.get("register_vex"),
        _globals.get("register_utils"),
    ]
    if fn is not None
]
