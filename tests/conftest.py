import sys
import types
import pytest

def make_hou_mock():
    """Create a minimal hou mock for unit testing without Houdini installed."""
    hou = types.ModuleType("hou")

    # Exceptions
    class HouError(Exception): pass
    class ObjectWasDeleted(HouError): pass
    class PermissionError(HouError): pass
    class OperationFailed(HouError): pass
    class InvalidInput(HouError): pass
    class LicenseError(HouError): pass
    class NodeError(HouError): pass

    hou.Error = HouError
    hou.ObjectWasDeleted = ObjectWasDeleted
    hou.PermissionError = PermissionError
    hou.OperationFailed = OperationFailed
    hou.InvalidInput = InvalidInput
    hou.LicenseError = LicenseError
    hou.NodeError = NodeError

    # hipFile submodule
    hipFile = types.ModuleType("hou.hipFile")
    hipFile.path = lambda: "/tmp/untitled.hip"
    hipFile.hasUnsavedChanges = lambda: False
    hipFile.load = lambda path, suppress_save_prompt=True: None
    hipFile.save = lambda path=None: None
    hipFile.clear = lambda suppress_save_prompt=True: None
    hipFile.merge = lambda path: None
    hou.hipFile = hipFile

    # undos submodule
    class _UndoGroup:
        def __init__(self, label): self.label = label
        def __enter__(self): return self
        def __exit__(self, *a): pass

    undos = types.ModuleType("hou.undos")
    undos.group = lambda label: _UndoGroup(label)
    hou.undos = undos

    hou.applicationVersionString = lambda: "20.5.000"
    hou.applicationName = lambda: "houdini"
    hou.applicationVersion = lambda: (20, 5, 0)
    hou.licenseCategory = lambda: None
    hou.userName = lambda: "testuser"
    hou.node = lambda path: None
    hou.root = lambda: None
    hou.frame = lambda: 1.0
    hou.setFrame = lambda f: None
    hou.time = lambda: 0.0
    hou.fps = lambda: 24.0
    hou.setFps = lambda fps: None
    hou.playbar = types.ModuleType("hou.playbar")
    hou.playbar.frameRange = lambda: (1.0, 240.0)
    hou.isUIAvailable = lambda: False
    hou.hscript = lambda cmd: ("", "")
    hou.hscriptExpression = lambda expr: 0.0
    hou.expandString = lambda s: s
    hou.getenv = lambda k, default=None: default
    hou.putenv = lambda k, v: None
    hou.findFile = lambda f: ""
    hou.houdiniPath = lambda: []

    return hou


@pytest.fixture(autouse=True)
def mock_hou(monkeypatch):
    hou_mock = make_hou_mock()
    monkeypatch.setitem(sys.modules, "hou", hou_mock)
    return hou_mock
