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

    # Vector/Math types
    import types as _types

    class _Vector2:
        def __init__(self, x=0.0, y=0.0): self.x, self.y = x, y
        def __getitem__(self, i): return (self.x, self.y)[i]

    class _Matrix4:
        def asTuple(self): return tuple([0.0] * 16)           # flat 16-float
        def asTupleOfTuples(self): return tuple([tuple([0.0]*4)]*4)  # nested 4x4
        def __init__(self, data=None): pass

    class _Color:
        def __init__(self, rgb=(0.6, 0.6, 0.6)): self._rgb = rgb
        def rgb(self): return self._rgb

    class _Keyframe:
        def __init__(self): self._frame = 1.0; self._value = 0.0; self._expr = ""
        def setFrame(self, f): self._frame = f
        def frame(self): return self._frame
        def setValue(self, v): self._value = v
        def value(self): return self._value
        def setExpression(self, e, lang=None): self._expr = e
        def expression(self): return self._expr

    hou.Vector2 = _Vector2
    hou.Matrix4 = _Matrix4
    hou.Color = _Color
    hou.Keyframe = _Keyframe
    hou.copyNodesTo = lambda nodes, dest: []
    hou.moveNodesTo = lambda nodes, dest: []

    # exprLanguage enum
    exprLanguage = _types.SimpleNamespace()
    exprLanguage.Python = "python"
    exprLanguage.Hscript = "hscript"
    hou.exprLanguage = exprLanguage

    # attribType enum
    attribType = _types.SimpleNamespace()
    attribType.Point = "point"
    attribType.Prim = "prim"
    attribType.Vertex = "vertex"
    attribType.Global = "global"
    hou.attribType = attribType

    # updateMode enum
    updateMode = _types.SimpleNamespace()
    updateMode.AutoUpdate = "auto"
    updateMode.Manual = "manual"
    updateMode.OnRequest = "on_request"
    hou.updateMode = updateMode
    hou.setUpdateMode = lambda mode: None

    # Node type category callables
    _mock_cat = _types.SimpleNamespace(
        nodeTypes=lambda: {},
        name=lambda: "mock"
    )
    hou.sopNodeTypeCategory = lambda: _mock_cat
    hou.objNodeTypeCategory = lambda: _mock_cat
    hou.dopNodeTypeCategory = lambda: _mock_cat
    hou.ropNodeTypeCategory = lambda: _mock_cat
    hou.lopNodeTypeCategory = lambda: _mock_cat
    hou.topNodeTypeCategory = lambda: _mock_cat
    hou.cop2NodeTypeCategory = lambda: _mock_cat
    hou.vopNodeTypeCategory = lambda: _mock_cat
    hou.shopNodeTypeCategory = lambda: _mock_cat
    hou.chopNodeTypeCategory = lambda: _mock_cat

    # hda submodule
    hda = _types.ModuleType("hou.hda")
    hda.loadedFiles = lambda: []
    hda.definitionsInFile = lambda path: []
    hda.installFile = lambda path: None
    hou.hda = hda

    # takes submodule
    takes_mod = _types.ModuleType("hou.takes")
    _root_take = _types.SimpleNamespace(
        name=lambda: "Main",
        children=lambda: [],
        addChildTake=lambda name: _types.SimpleNamespace(name=lambda: name, children=lambda: []),
    )
    takes_mod.rootTake = lambda: _root_take
    takes_mod.currentTake = lambda: _root_take
    takes_mod.setCurrentTake = lambda t: None
    takes_mod.findTake = lambda name: _root_take
    takes_mod.takes = lambda: [_root_take]
    hou.takes = takes_mod

    # undos extensions
    hou.undos.performUndo = lambda: None
    hou.undos.performRedo = lambda: None

    # playbar extensions
    hou.playbar.setFrameRange = lambda start, end: None
    hou.playbar.setFrameRange.__name__ = "setFrameRange"

    # perfMon submodule
    perfMon = _types.ModuleType("hou.perfMon")
    _profile = _types.SimpleNamespace(stop=lambda: None, stats=lambda: {})
    perfMon.startProfile = lambda label: _profile
    hou.perfMon = perfMon

    # vex
    hou.vexContexts = lambda: []
    hou.runVex = lambda code, ctx: {}

    # fileReferences
    hou.fileReferences = lambda: []

    # UI
    hou.ui = _types.ModuleType("hou.ui")
    hou.ui.paneTabOfType = lambda t: None

    # selectableNodeBundles
    hou.nodeBundles = lambda: []

    # simulation
    hou.setSimulationEnabled = lambda on: None
    hou.simulationEnabled = lambda: True

    return hou


@pytest.fixture(autouse=True)
def mock_hou(monkeypatch):
    hou_mock = make_hou_mock()
    monkeypatch.setitem(sys.modules, "hou", hou_mock)
    # Evict tool modules so each test gets a fresh import with the new hou mock.
    _tool_prefix = "houdini_side.tools."
    for key in list(sys.modules):
        if key.startswith(_tool_prefix) or key == "houdini_side.tools":
            monkeypatch.delitem(sys.modules, key, raising=False)
    return hou_mock
