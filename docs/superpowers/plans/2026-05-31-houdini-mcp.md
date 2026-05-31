# Houdini MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production MCP server (105 tools, 16 categories) that runs as an SSE thread inside an active Houdini session, giving Claude full programmatic access to `hou.*`.

**Architecture:** A Python thread inside Houdini hosts an MCP SSE server on `localhost:9876`. Tool calls are dispatched thread-safely to Houdini's main thread via `hou.postEventCallback()` with a `threading.Event` for synchronization. All tools return `{"success": bool, "data": {}, "warnings": []}`.

**Tech Stack:** Python 3.10+ (Houdini embedded), `mcp` Python SDK (SSE transport), `hou` module, `hython` for headless tests.

**QA Strategy:** After each implementation phase, a `qa-ux-engineer` agent runs **in parallel** with the next phase's implementation to review API design quality, error handling, test coverage, and response format consistency. QA review gates are marked with `🔍 QA GATE` below. Implementation proceeds concurrently — don't wait for QA unless the gate is marked `[BLOCKING]`.

---

## File Map

| File | Responsibility |
|------|---------------|
| `houdini_side/mcp_server.py` | MCP app init, tool registration, SSE server thread |
| `houdini_side/dispatcher.py` | Thread-safe `hou.*` dispatch via `postEventCallback` |
| `houdini_side/startup.py` | Houdini 456.py hook + shelf button creator |
| `houdini_side/tools/__init__.py` | Re-exports all register functions |
| `houdini_side/tools/session.py` | `session_info`, `hip_*` (6 tools) |
| `houdini_side/tools/nodes.py` | `node_*`, `network_box_*`, `sticky_note_*` (16 tools) |
| `houdini_side/tools/parameters.py` | `parm_*` (10 tools) |
| `houdini_side/tools/geometry.py` | `geo_*` (8 tools) |
| `houdini_side/tools/transforms.py` | `obj_*` (6 tools) |
| `houdini_side/tools/rendering.py` | `rop_*` (6 tools) |
| `houdini_side/tools/animation.py` | `time_*`, `fps_*`, `frame_range_*`, `channel_*`, `keyframe_*` (8 tools) |
| `houdini_side/tools/hda.py` | `hda_*` (8 tools) |
| `houdini_side/tools/dynamics.py` | `dop_*` (5 tools) |
| `houdini_side/tools/solaris.py` | `lop_*` (6 tools) |
| `houdini_side/tools/pdg.py` | `pdg_*` (5 tools) |
| `houdini_side/tools/takes.py` | `take_*` (4 tools) |
| `houdini_side/tools/vex.py` | `vex_*`, `vop_*` (7 tools) |
| `houdini_side/tools/utils.py` | `run_hscript`, `eval_expression`, `expand_string`, `find_file`, `env_*`, `perf_mon_*`, `viewport_screenshot`, `node_bundle_list`, `undo`, `redo`, `update_mode_set` (11 tools) |
| `install/houdini_mcp.json` | Houdini package descriptor |
| `install/setup.sh` | Installs mcp SDK into hython |
| `tests/conftest.py` | Shared `hou` mock fixtures |
| `tests/test_dispatcher.py` | Dispatcher unit tests (no hou needed) |
| `tests/test_session.py` | Session tool tests |
| `tests/test_nodes.py` | Node tool tests |
| `tests/test_parameters.py` | Parameter tool tests |
| `tests/test_geometry.py` | Geometry tool tests |

---

## Task 1: Install dependencies and scaffold project

**Files:**
- Create: `install/setup.sh`
- Create: `install/houdini_mcp.json`
- Create: `houdini_side/__init__.py`
- Create: `houdini_side/tools/__init__.py`
- Create: `tests/conftest.py`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `install/setup.sh`**

```bash
#!/usr/bin/env bash
set -e
# Find hython
HYTHON=$(which hython 2>/dev/null || echo "/Applications/Houdini/Current/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython")
if [ ! -f "$HYTHON" ]; then
    echo "Error: hython not found. Set PATH or edit HYTHON in this script."
    exit 1
fi
echo "Using hython: $HYTHON"
$HYTHON -m pip install "mcp>=1.0.0" --upgrade
echo "Done. MCP SDK installed into Houdini Python."
```

- [ ] **Step 2: Create `install/houdini_mcp.json`**

```json
{
    "name": "houdini-mcp",
    "path": "$HOUDINI_MCP_ROOT/houdini_side",
    "env": [
        { "HOUDINI_MCP_PORT": { "value": "9876" } },
        { "HOUDINI_MCP_ROOT": { "value": "$HOME/houdini-mcp" } }
    ],
    "houdini456": [ "$HOUDINI_MCP_ROOT/houdini_side/startup.py" ]
}
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
pytest>=7.0
pytest-mock>=3.0
```

- [ ] **Step 4: Create `houdini_side/__init__.py`** (empty)

```python
```

- [ ] **Step 5: Create `houdini_side/tools/__init__.py`**

```python
from .session import register as register_session
from .nodes import register as register_nodes
from .parameters import register as register_parameters
from .geometry import register as register_geometry
from .transforms import register as register_transforms
from .rendering import register as register_rendering
from .animation import register as register_animation
from .hda import register as register_hda
from .dynamics import register as register_dynamics
from .solaris import register as register_solaris
from .pdg import register as register_pdg
from .takes import register as register_takes
from .vex import register as register_vex
from .utils import register as register_utils

ALL_REGISTERS = [
    register_session, register_nodes, register_parameters,
    register_geometry, register_transforms, register_rendering,
    register_animation, register_hda, register_dynamics,
    register_solaris, register_pdg, register_takes,
    register_vex, register_utils,
]
```

- [ ] **Step 6: Create `tests/conftest.py`**

```python
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

class _UndoGroup:
    def __init__(self, label): self.label = label
    def __enter__(self): return self
    def __exit__(self, *a): pass

@pytest.fixture(autouse=True)
def mock_hou(monkeypatch):
    hou_mock = make_hou_mock()
    monkeypatch.setitem(sys.modules, "hou", hou_mock)
    return hou_mock
```

- [ ] **Step 7: Commit scaffold**

```bash
cd /path/to/houdini-mcp
git init
git add .
git commit -m "chore: project scaffold, install scripts, test fixtures"
```

---

## Task 2: Thread-safe dispatcher

**Files:**
- Create: `houdini_side/dispatcher.py`
- Create: `tests/test_dispatcher.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_dispatcher.py
import threading
import sys, types
import pytest

def test_dispatch_runs_callable(mock_hou):
    from houdini_side.dispatcher import dispatch

    results = []
    def work():
        results.append(42)
        return 42

    # In test context hou.isUIAvailable() is False, so dispatch runs inline
    val = dispatch(work)
    assert val == 42
    assert results == [42]

def test_dispatch_propagates_exception(mock_hou):
    from houdini_side.dispatcher import dispatch

    def bad():
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        dispatch(bad)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd houdini-mcp
python -m pytest tests/test_dispatcher.py -v
# Expected: ImportError or ModuleNotFoundError for dispatcher
```

- [ ] **Step 3: Implement `houdini_side/dispatcher.py`**

```python
"""
Thread-safe dispatcher for hou.* calls.

Houdini requires all hou.* calls on the main thread.
When the MCP server thread needs to call hou.*, it posts a callback
via hou.postEventCallback() and waits on a threading.Event.

In headless/test contexts (hou.isUIAvailable() is False),
the callable is executed inline on the calling thread.
"""
import threading
import traceback

try:
    import hou
    _HOU_AVAILABLE = True
except ImportError:
    _HOU_AVAILABLE = False


def dispatch(fn):
    """
    Execute fn() on Houdini's main thread and return its result.
    Raises any exception fn() raises.
    """
    if not _HOU_AVAILABLE or not hou.isUIAvailable():
        return fn()

    result_holder = [None]
    exc_holder = [None]
    done = threading.Event()

    def _callback():
        try:
            result_holder[0] = fn()
        except Exception as e:
            exc_holder[0] = e
        finally:
            done.set()

    hou.postEventCallback(_callback)
    done.wait(timeout=30.0)

    if not done.is_set():
        raise TimeoutError("Houdini main thread dispatch timed out after 30s")
    if exc_holder[0] is not None:
        raise exc_holder[0]
    return result_holder[0]


def ok(data, warnings=None):
    """Convenience: build a success response dict."""
    return {"success": True, "data": data, "warnings": warnings or []}


def err(e):
    """Convenience: build an error response dict from an exception."""
    return {
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_dispatcher.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add houdini_side/dispatcher.py tests/test_dispatcher.py
git commit -m "feat: thread-safe dispatcher with inline fallback for tests"
```

---

## Task 3: MCP server + tool registry

**Files:**
- Create: `houdini_side/mcp_server.py`

- [ ] **Step 1: Create `houdini_side/mcp_server.py`**

```python
"""
MCP SSE server that runs as a daemon thread inside Houdini.

Usage (from Houdini Python Shell or startup script):
    from houdini_side.mcp_server import start_server, stop_server
    start_server()   # starts on $HOUDINI_MCP_PORT (default 9876)
    stop_server()    # graceful shutdown
"""
import os
import threading
import logging

log = logging.getLogger("houdini-mcp")

_server_thread = None
_mcp_app = None


def _build_app():
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    import mcp.types as mcp_types
    from houdini_side.tools import ALL_REGISTERS

    app = Server("houdini-mcp")

    # Register all tool modules
    for register_fn in ALL_REGISTERS:
        register_fn(app)

    return app


def start_server(port=None):
    global _server_thread, _mcp_app

    if _server_thread and _server_thread.is_alive():
        log.warning("MCP server already running")
        return

    port = port or int(os.environ.get("HOUDINI_MCP_PORT", "9876"))
    _mcp_app = _build_app()

    def _run():
        import asyncio
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await _mcp_app.run(
                    streams[0], streams[1],
                    _mcp_app.create_initialization_options()
                )

        starlette_app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ])

        config = uvicorn.Config(starlette_app, host="127.0.0.1", port=port,
                                log_level="warning")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

    _server_thread = threading.Thread(target=_run, name="houdini-mcp-server",
                                       daemon=True)
    _server_thread.start()
    log.info(f"Houdini MCP server started on http://127.0.0.1:{port}/sse")
    print(f"[houdini-mcp] Listening on http://127.0.0.1:{port}/sse")


def stop_server():
    global _server_thread
    if _server_thread:
        # uvicorn daemon thread exits when main thread exits or via signal
        _server_thread = None
    print("[houdini-mcp] Server stopped.")
```

- [ ] **Step 2: Verify imports parse cleanly (no Houdini needed)**

```bash
python -c "import ast; ast.parse(open('houdini_side/mcp_server.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add houdini_side/mcp_server.py
git commit -m "feat: MCP SSE server with daemon thread and tool registry"
```

---

## Task 4: Startup script and shelf button

**Files:**
- Create: `houdini_side/startup.py`

- [ ] **Step 1: Create `houdini_side/startup.py`**

```python
"""
Loaded by Houdini via the houdini456 package hook.
Creates a shelf tool to start/stop the MCP server.
"""
import hou


def _create_shelf():
    shelf_name = "houdini_mcp"
    try:
        shelf = hou.shelves.shelf(shelf_name)
    except Exception:
        shelf = None

    if shelf is None:
        shelf = hou.shelves.newShelf(name=shelf_name, label="Houdini MCP")

    start_script = """
from houdini_side.mcp_server import start_server
start_server()
"""
    stop_script = """
from houdini_side.mcp_server import stop_server
stop_server()
"""
    try:
        start_tool = hou.shelves.tool("houdini_mcp_start")
    except Exception:
        start_tool = None

    if start_tool is None:
        hou.shelves.newTool(
            name="houdini_mcp_start",
            label="Start MCP Server",
            script=start_script,
            language=hou.scriptLanguage.Python,
        )
    try:
        stop_tool = hou.shelves.tool("houdini_mcp_stop")
    except Exception:
        stop_tool = None

    if stop_tool is None:
        hou.shelves.newTool(
            name="houdini_mcp_stop",
            label="Stop MCP Server",
            script=stop_script,
            language=hou.scriptLanguage.Python,
        )

    shelf.setTools([
        hou.shelves.tool("houdini_mcp_start"),
        hou.shelves.tool("houdini_mcp_stop"),
    ])


try:
    _create_shelf()
    print("[houdini-mcp] Shelf created. Use 'Start MCP Server' to begin.")
except Exception as e:
    print(f"[houdini-mcp] Could not create shelf: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add houdini_side/startup.py
git commit -m "feat: startup hook and shelf button for MCP server control"
```

---

## Task 5: Session tools (6 tools)

**Files:**
- Create: `houdini_side/tools/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session.py
import pytest

def test_session_info_returns_version(mock_hou):
    mock_hou.applicationVersionString.return_value = "20.5.000"
    mock_hou.userName.return_value = "artist"
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is True
    assert "20.5" in result["data"]["version"]

def test_hip_info_no_unsaved(mock_hou):
    mock_hou.hipFile.path.return_value = "/projects/test.hip"
    mock_hou.hipFile.hasUnsavedChanges.return_value = False
    from houdini_side.tools.session import _hip_info
    result = _hip_info()
    assert result["success"] is True
    assert result["data"]["path"] == "/projects/test.hip"
    assert result["data"]["has_unsaved_changes"] is False

def test_hip_save_calls_hipfile(mock_hou):
    saved = []
    mock_hou.hipFile.save = lambda path=None: saved.append(path)
    from houdini_side.tools.session import _hip_save
    result = _hip_save(None)
    assert result["success"] is True
    assert saved == [None]

def test_hip_load_calls_hipfile(mock_hou):
    loaded = []
    mock_hou.hipFile.load = lambda path, suppress_save_prompt=True: loaded.append(path)
    from houdini_side.tools.session import _hip_load
    result = _hip_load("/projects/scene.hip")
    assert result["success"] is True
    assert loaded == ["/projects/scene.hip"]
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_session.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement `houdini_side/tools/session.py`**

```python
"""Session and hip file management tools."""
import hou
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
    from mcp.types import Tool, TextContent
    import json

    @app.tool("session_info")
    async def session_info() -> list[TextContent]:
        """Get Houdini version, license, user and UI availability."""
        result = _session_info()
        return [TextContent(type="text", text=json.dumps(result))]

    @app.tool("hip_info")
    async def hip_info() -> list[TextContent]:
        """Get current scene file path and unsaved-changes status."""
        result = _hip_info()
        return [TextContent(type="text", text=json.dumps(result))]

    @app.tool("hip_new")
    async def hip_new() -> list[TextContent]:
        """Clear the scene (new empty hip file)."""
        result = _hip_new()
        return [TextContent(type="text", text=json.dumps(result))]

    @app.tool("hip_load")
    async def hip_load(path: str) -> list[TextContent]:
        """Load a .hip or .hiplc file from disk."""
        result = _hip_load(path)
        return [TextContent(type="text", text=json.dumps(result))]

    @app.tool("hip_save")
    async def hip_save(path: str = None) -> list[TextContent]:
        """Save the current scene. Uses current path if path is omitted."""
        result = _hip_save(path)
        return [TextContent(type="text", text=json.dumps(result))]

    @app.tool("hip_merge")
    async def hip_merge(path: str) -> list[TextContent]:
        """Merge another .hip file into the current scene."""
        result = _hip_merge(path)
        return [TextContent(type="text", text=json.dumps(result))]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_session.py -v
# Expected: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add houdini_side/tools/session.py tests/test_session.py
git commit -m "feat: session tools (session_info, hip_new/load/save/merge/info)"
```

---

## Task 6: Node tools — core CRUD (8 tools)

**Files:**
- Create: `houdini_side/tools/nodes.py` (partial — complete in Task 7)
- Create: `tests/test_nodes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_nodes.py
import types, pytest

def _make_node_mock(path="/obj/geo1", node_type="geo", children=None):
    n = types.SimpleNamespace()
    n.path = lambda: path
    n.name = lambda: path.split("/")[-1]
    n.type = lambda: types.SimpleNamespace(name=lambda: node_type)
    n.parent = lambda: types.SimpleNamespace(path=lambda: "/obj")
    n.children = lambda: children or []
    n.inputs = lambda: []
    n.outputs = lambda: []
    n.isBypassed = lambda: False
    n.isDisplayFlagSet = lambda: True
    n.isRenderFlagSet = lambda: False
    n.color = lambda: types.SimpleNamespace(rgb=lambda: (0.6, 0.6, 0.6))
    n.position = lambda: types.SimpleNamespace(x=lambda: 0.0, y=lambda: 0.0)
    n.comment = lambda: ""
    n.setName = lambda name: None
    n.destroy = lambda: None
    n.bypass = lambda on: None
    n.setPosition = lambda pos: None
    n.createNode = lambda t, name=None: _make_node_mock(f"{path}/{name or t}", t)
    n.setInput = lambda idx, src_node, src_out=0: None
    n.setColor = lambda c: None
    n.setComment = lambda s: None
    n.layoutChildren = lambda: None
    n.parmTuple = lambda name: None
    n.parm = lambda name: None
    return n


def test_node_get_returns_info(mock_hou):
    node = _make_node_mock()
    mock_hou.node = lambda path: node
    from houdini_side.tools.nodes import _node_get
    result = _node_get("/obj/geo1")
    assert result["success"] is True
    assert result["data"]["path"] == "/obj/geo1"
    assert result["data"]["type"] == "geo"


def test_node_get_missing(mock_hou):
    mock_hou.node = lambda path: None
    from houdini_side.tools.nodes import _node_get
    result = _node_get("/obj/nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_node_create(mock_hou):
    parent = _make_node_mock("/obj")
    created = []
    def create_node(node_type, name=None):
        child = _make_node_mock(f"/obj/{name or node_type}", node_type)
        created.append(child)
        return child
    parent.createNode = create_node
    mock_hou.node = lambda path: parent if path == "/obj" else None
    from houdini_side.tools.nodes import _node_create
    result = _node_create("/obj", "geo", "mygeo")
    assert result["success"] is True
    assert len(created) == 1


def test_node_list(mock_hou):
    children = [_make_node_mock("/obj/geo1"), _make_node_mock("/obj/cam1")]
    parent = _make_node_mock("/obj", children=children)
    mock_hou.node = lambda path: parent
    from houdini_side.tools.nodes import _node_list
    result = _node_list("/obj")
    assert result["success"] is True
    assert len(result["data"]["nodes"]) == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_nodes.py -v
# Expected: ImportError
```

- [ ] **Step 3: Implement core node functions in `houdini_side/tools/nodes.py`**

```python
"""Node creation, deletion, wiring, and network management tools."""
import json
import hou
from houdini_side.dispatcher import dispatch, ok, err


def _node_info(node):
    """Serialize a node to a dict."""
    try:
        inputs = [
            {"input_index": i, "node": c.node().path() if c and c.node() else None}
            for i, c in enumerate(node.inputs())
        ]
        outputs = [
            {"output_index": i, "node": c.node().path() if c and c.node() else None}
            for i, c in enumerate(node.outputs())
        ]
    except Exception:
        inputs, outputs = [], []

    try:
        pos = node.position()
        position = [pos[0], pos[1]]
    except Exception:
        position = [0.0, 0.0]

    try:
        color_rgb = list(node.color().rgb())
    except Exception:
        color_rgb = [0.6, 0.6, 0.6]

    return {
        "path": node.path(),
        "name": node.name(),
        "type": node.type().name(),
        "parent": node.parent().path() if node.parent() else None,
        "is_bypassed": node.isBypassed(),
        "display_flag": node.isDisplayFlagSet(),
        "render_flag": node.isRenderFlagSet(),
        "color": color_rgb,
        "position": position,
        "comment": node.comment(),
        "inputs": inputs,
        "outputs": outputs,
    }


def _node_get(path: str):
    try:
        def work():
            node = hou.node(path)
            if node is None:
                raise ValueError(f"Node not found: {path}")
            return ok(_node_info(node))
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_list(network_path: str, type_filter: str = None):
    try:
        def work():
            parent = hou.node(network_path)
            if parent is None:
                raise ValueError(f"Network not found: {network_path}")
            children = parent.children()
            if type_filter:
                children = [c for c in children if c.type().name() == type_filter]
            return ok({"nodes": [_node_info(c) for c in children]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_create(parent_path: str, node_type: str, name: str = None):
    try:
        def work():
            with hou.undos.group("mcp: create node"):
                parent = hou.node(parent_path)
                if parent is None:
                    raise ValueError(f"Parent network not found: {parent_path}")
                node = parent.createNode(node_type, name)
                return ok(_node_info(node))
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_delete(path: str):
    try:
        def work():
            with hou.undos.group("mcp: delete node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path}")
                node.destroy()
            return ok({"deleted": path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_rename(path: str, new_name: str):
    try:
        def work():
            with hou.undos.group("mcp: rename node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path}")
                node.setName(new_name)
                return ok({"path": node.path(), "name": node.name()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_connect(from_path: str, from_output: int,
                  to_path: str, to_input: int):
    try:
        def work():
            with hou.undos.group("mcp: connect nodes"):
                src = hou.node(from_path)
                dst = hou.node(to_path)
                if src is None:
                    raise ValueError(f"Source node not found: {from_path}")
                if dst is None:
                    raise ValueError(f"Dest node not found: {to_path}")
                dst.setInput(to_input, src, from_output)
            return ok({"connected": f"{from_path}[{from_output}] -> {to_path}[{to_input}]"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_disconnect(to_path: str, to_input: int):
    try:
        def work():
            with hou.undos.group("mcp: disconnect node"):
                dst = hou.node(to_path)
                if dst is None:
                    raise ValueError(f"Node not found: {to_path}")
                dst.setInput(to_input, None)
            return ok({"disconnected": f"{to_path}[{to_input}]"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_bypass(path: str, on: bool):
    try:
        def work():
            with hou.undos.group("mcp: bypass node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path}")
                node.bypass(on)
            return ok({"path": path, "bypassed": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_set_flag(path: str, flag: str, on: bool):
    """flag: 'display' | 'render' | 'template' | 'highlight' | 'bypass'"""
    try:
        def work():
            with hou.undos.group(f"mcp: set flag {flag}"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path}")
                flag_map = {
                    "display": "setDisplayFlag",
                    "render": "setRenderFlag",
                    "template": "setTemplateFlag",
                    "highlight": "setHighlightFlag",
                    "bypass": "bypass",
                }
                method_name = flag_map.get(flag)
                if not method_name:
                    raise ValueError(f"Unknown flag: {flag}. Use: {list(flag_map)}")
                getattr(node, method_name)(on)
            return ok({"path": path, "flag": flag, "value": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_cook(path: str):
    try:
        def work():
            node = hou.node(path)
            if node is None:
                raise ValueError(f"Node not found: {path}")
            node.cook(force=True)
            return ok({"cooked": path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_layout(network_path: str):
    try:
        def work():
            with hou.undos.group("mcp: layout network"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path}")
                parent.layoutChildren()
            return ok({"laid_out": network_path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_type_list(context: str):
    """context: 'sop'|'obj'|'dop'|'rop'|'lop'|'top'|'cop2'|'vop'|'shop'|'chop'"""
    try:
        def work():
            cat_fn_map = {
                "sop": hou.sopNodeTypeCategory,
                "obj": hou.objNodeTypeCategory,
                "dop": hou.dopNodeTypeCategory,
                "rop": hou.ropNodeTypeCategory,
                "lop": hou.lopNodeTypeCategory,
                "top": hou.topNodeTypeCategory,
                "cop2": hou.cop2NodeTypeCategory,
                "vop": hou.vopNodeTypeCategory,
                "shop": hou.shopNodeTypeCategory,
                "chop": hou.chopNodeTypeCategory,
            }
            if context not in cat_fn_map:
                raise ValueError(f"Unknown context: {context}. Use: {list(cat_fn_map)}")
            cat = cat_fn_map[context]()
            types = sorted(cat.nodeTypes().keys())
            return ok({"context": context, "types": types})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_move(path: str, x: float, y: float):
    try:
        def work():
            with hou.undos.group("mcp: move node"):
                node = hou.node(path)
                if node is None:
                    raise ValueError(f"Node not found: {path}")
                node.setPosition(hou.Vector2(x, y))
            return ok({"path": path, "position": [x, y]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _node_copy_paste(source_paths: list, dest_network: str):
    try:
        def work():
            with hou.undos.group("mcp: copy-paste nodes"):
                nodes = []
                for p in source_paths:
                    n = hou.node(p)
                    if n is None:
                        raise ValueError(f"Node not found: {p}")
                    nodes.append(n)
                dest = hou.node(dest_network)
                if dest is None:
                    raise ValueError(f"Dest network not found: {dest_network}")
                pasted = hou.copyNodesTo(nodes, dest)
                return ok({"pasted": [n.path() for n in pasted]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _network_box_create(network_path: str, name: str, color=None):
    try:
        def work():
            with hou.undos.group("mcp: create network box"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path}")
                box = parent.createNetworkBox()
                box.setComment(name)
                if color:
                    box.setColor(hou.Color(color))
                return ok({"comment": name})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _sticky_note_create(network_path: str, text: str, x: float, y: float):
    try:
        def work():
            with hou.undos.group("mcp: create sticky note"):
                parent = hou.node(network_path)
                if parent is None:
                    raise ValueError(f"Network not found: {network_path}")
                note = parent.createStickyNote()
                note.setText(text)
                note.setPosition(hou.Vector2(x, y))
                return ok({"text": text, "position": [x, y]})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    from mcp.types import TextContent

    @app.tool("node_get")
    async def node_get(path: str) -> list[TextContent]:
        """Get info about a node: type, flags, connections, color, position."""
        return [TextContent(type="text", text=json.dumps(_node_get(path)))]

    @app.tool("node_list")
    async def node_list(network_path: str, type_filter: str = None) -> list[TextContent]:
        """List all children of a network. Optional type_filter (e.g. 'box')."""
        return [TextContent(type="text", text=json.dumps(_node_list(network_path, type_filter)))]

    @app.tool("node_create")
    async def node_create(parent_path: str, node_type: str, name: str = None) -> list[TextContent]:
        """Create a node inside a network. Use node_type_list to get valid types."""
        return [TextContent(type="text", text=json.dumps(_node_create(parent_path, node_type, name)))]

    @app.tool("node_delete")
    async def node_delete(path: str) -> list[TextContent]:
        """Delete a node permanently."""
        return [TextContent(type="text", text=json.dumps(_node_delete(path)))]

    @app.tool("node_rename")
    async def node_rename(path: str, new_name: str) -> list[TextContent]:
        """Rename a node."""
        return [TextContent(type="text", text=json.dumps(_node_rename(path, new_name)))]

    @app.tool("node_connect")
    async def node_connect(from_path: str, from_output: int, to_path: str, to_input: int) -> list[TextContent]:
        """Wire from_path output to to_path input."""
        return [TextContent(type="text", text=json.dumps(_node_connect(from_path, from_output, to_path, to_input)))]

    @app.tool("node_disconnect")
    async def node_disconnect(to_path: str, to_input: int) -> list[TextContent]:
        """Disconnect an input on a node."""
        return [TextContent(type="text", text=json.dumps(_node_disconnect(to_path, to_input)))]

    @app.tool("node_bypass")
    async def node_bypass(path: str, on: bool) -> list[TextContent]:
        """Toggle bypass flag on a node."""
        return [TextContent(type="text", text=json.dumps(_node_bypass(path, on)))]

    @app.tool("node_set_flag")
    async def node_set_flag(path: str, flag: str, on: bool) -> list[TextContent]:
        """Set a flag: display | render | template | highlight | bypass."""
        return [TextContent(type="text", text=json.dumps(_node_set_flag(path, flag, on)))]

    @app.tool("node_cook")
    async def node_cook(path: str) -> list[TextContent]:
        """Force-cook a node."""
        return [TextContent(type="text", text=json.dumps(_node_cook(path)))]

    @app.tool("node_layout")
    async def node_layout(network_path: str) -> list[TextContent]:
        """Auto-layout all nodes in a network."""
        return [TextContent(type="text", text=json.dumps(_node_layout(network_path)))]

    @app.tool("node_type_list")
    async def node_type_list(context: str) -> list[TextContent]:
        """List all node types in a context: sop|obj|dop|rop|lop|top|cop2|vop|shop|chop."""
        return [TextContent(type="text", text=json.dumps(_node_type_list(context)))]

    @app.tool("node_move")
    async def node_move(path: str, x: float, y: float) -> list[TextContent]:
        """Move a node to position (x, y) in the network editor."""
        return [TextContent(type="text", text=json.dumps(_node_move(path, x, y)))]

    @app.tool("node_copy_paste")
    async def node_copy_paste(source_paths: list, dest_network: str) -> list[TextContent]:
        """Copy nodes and paste them into dest_network."""
        return [TextContent(type="text", text=json.dumps(_node_copy_paste(source_paths, dest_network)))]

    @app.tool("network_box_create")
    async def network_box_create(network_path: str, name: str, color: list = None) -> list[TextContent]:
        """Create a network box. color is [r, g, b] floats 0-1."""
        return [TextContent(type="text", text=json.dumps(_network_box_create(network_path, name, color)))]

    @app.tool("sticky_note_create")
    async def sticky_note_create(network_path: str, text: str, x: float, y: float) -> list[TextContent]:
        """Create a sticky note at position (x, y)."""
        return [TextContent(type="text", text=json.dumps(_sticky_note_create(network_path, text, x, y)))]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_nodes.py -v
# Expected: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add houdini_side/tools/nodes.py tests/test_nodes.py
git commit -m "feat: 16 node management tools"
```

---

## Task 7: Parameter tools (10 tools)

**Files:**
- Create: `houdini_side/tools/parameters.py`
- Create: `tests/test_parameters.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_parameters.py
import types, pytest

def _make_parm(name="tx", value=0.0, default=0.0):
    p = types.SimpleNamespace()
    p.name = lambda: name
    p.eval = lambda: value
    p.set = lambda v: setattr(p, '_val', v)
    p.revert = lambda: None
    p.lock = lambda on: None
    p.setExpression = lambda expr, lang=None: None
    p.keyframes = lambda: []
    p.setKeyframe = lambda kf: None
    p.deleteKeyframeAtFrame = lambda f: None
    p.parmTemplate = lambda: types.SimpleNamespace(
        defaultValue=lambda: (default,),
        type=lambda: None,
    )
    return p

def _make_node_with_parm(parm_name="tx", parm_value=5.0):
    import types
    node = types.SimpleNamespace()
    parm = _make_parm(parm_name, parm_value)
    node.parm = lambda name: parm if name == parm_name else None
    node.path = lambda: "/obj/geo1"
    node.parmTuples = lambda: []
    node.parms = lambda: [parm]
    return node

def test_parm_get(mock_hou):
    node = _make_node_with_parm("tx", 5.0)
    mock_hou.node = lambda p: node
    from houdini_side.tools.parameters import _parm_get
    result = _parm_get("/obj/geo1", "tx")
    assert result["success"] is True
    assert result["data"]["value"] == 5.0

def test_parm_get_missing_node(mock_hou):
    mock_hou.node = lambda p: None
    from houdini_side.tools.parameters import _parm_get
    result = _parm_get("/obj/nonexistent", "tx")
    assert result["success"] is False

def test_parm_set(mock_hou):
    set_vals = []
    parm = _make_parm("tx")
    parm.set = lambda v: set_vals.append(v)
    node = types.SimpleNamespace()
    node.parm = lambda name: parm if name == "tx" else None
    mock_hou.node = lambda p: node
    import types
    from houdini_side.tools.parameters import _parm_set
    result = _parm_set("/obj/geo1", "tx", 3.14)
    assert result["success"] is True
    assert set_vals == [3.14]
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_parameters.py -v
```

- [ ] **Step 3: Implement `houdini_side/tools/parameters.py`**

```python
"""Parameter read/write, expressions, keyframes."""
import json
import hou
from houdini_side.dispatcher import dispatch, ok, err


def _parm_get(node_path: str, parm_name: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path}")
            parm = node.parm(parm_name)
            if parm is None:
                parm_tuple = node.parmTuple(parm_name)
                if parm_tuple is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                return ok({"name": parm_name, "value": list(parm_tuple.eval())})
            return ok({"name": parm_name, "value": parm.eval()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_set(node_path: str, parm_name: str, value):
    try:
        def work():
            with hou.undos.group("mcp: set parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                parm = node.parm(parm_name)
                if parm is None:
                    parm_tuple = node.parmTuple(parm_name)
                    if parm_tuple is None:
                        raise ValueError(f"Parameter not found: {parm_name}")
                    parm_tuple.set(value if isinstance(value, (list, tuple)) else [value])
                else:
                    parm.set(value)
            return ok({"node": node_path, "parm": parm_name, "value": value})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_set_expression(node_path: str, parm_name: str, expr: str,
                          language: str = "python"):
    try:
        def work():
            with hou.undos.group("mcp: set expression"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                lang = (hou.exprLanguage.Python if language == "python"
                        else hou.exprLanguage.Hscript)
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                parm.setExpression(expr, lang)
            return ok({"node": node_path, "parm": parm_name, "expression": expr})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_get_all(node_path: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path}")
            result = {}
            for parm in node.parms():
                try:
                    result[parm.name()] = parm.eval()
                except Exception:
                    result[parm.name()] = None
            return ok({"node": node_path, "parameters": result})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_revert(node_path: str, parm_name: str):
    try:
        def work():
            with hou.undos.group("mcp: revert parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                parm.revertToDefaults()
            return ok({"reverted": parm_name})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_lock(node_path: str, parm_name: str, on: bool):
    try:
        def work():
            with hou.undos.group("mcp: lock parm"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                parm.lock(on)
            return ok({"parm": parm_name, "locked": on})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframe_set(node_path: str, parm_name: str,
                        frame: float = None, value=None):
    try:
        def work():
            with hou.undos.group("mcp: set keyframe"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                kf = hou.Keyframe()
                if frame is not None:
                    kf.setFrame(frame)
                else:
                    kf.setFrame(hou.frame())
                if value is not None:
                    kf.setValue(value)
                else:
                    kf.setValue(parm.eval())
                parm.setKeyframe(kf)
                return ok({"parm": parm_name, "frame": kf.frame(), "value": kf.value()})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframe_delete(node_path: str, parm_name: str, frame: float):
    try:
        def work():
            with hou.undos.group("mcp: delete keyframe"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path}")
                parm = node.parm(parm_name)
                if parm is None:
                    raise ValueError(f"Parameter not found: {parm_name}")
                parm.deleteKeyframeAtFrame(frame)
            return ok({"parm": parm_name, "deleted_frame": frame})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_keyframes_list(node_path: str, parm_name: str):
    try:
        def work():
            node = hou.node(node_path)
            if node is None:
                raise ValueError(f"Node not found: {node_path}")
            parm = node.parm(parm_name)
            if parm is None:
                raise ValueError(f"Parameter not found: {parm_name}")
            kfs = []
            for kf in parm.keyframes():
                entry = {"frame": kf.frame()}
                try:
                    entry["value"] = kf.value()
                except Exception:
                    pass
                try:
                    entry["expression"] = kf.expression()
                except Exception:
                    pass
                kfs.append(entry)
            return ok({"parm": parm_name, "keyframes": kfs})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _parm_link(src_node: str, src_parm: str, dst_node: str, dst_parm: str):
    try:
        def work():
            with hou.undos.group("mcp: link parm"):
                dst = hou.node(dst_node)
                if dst is None:
                    raise ValueError(f"Dest node not found: {dst_node}")
                p = dst.parm(dst_parm)
                if p is None:
                    raise ValueError(f"Dest parm not found: {dst_parm}")
                expr = f'ch("{src_node}/{src_parm}")'
                p.setExpression(expr, hou.exprLanguage.Hscript)
            return ok({"linked": f"{dst_node}/{dst_parm} -> {src_node}/{src_parm}"})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    from mcp.types import TextContent

    @app.tool("parm_get")
    async def parm_get(node_path: str, parm_name: str) -> list[TextContent]:
        """Get the evaluated value of a parameter."""
        return [TextContent(type="text", text=json.dumps(_parm_get(node_path, parm_name)))]

    @app.tool("parm_set")
    async def parm_set(node_path: str, parm_name: str, value) -> list[TextContent]:
        """Set a parameter value. Use a list for vector params."""
        return [TextContent(type="text", text=json.dumps(_parm_set(node_path, parm_name, value)))]

    @app.tool("parm_set_expression")
    async def parm_set_expression(node_path: str, parm_name: str, expr: str, language: str = "python") -> list[TextContent]:
        """Set a channel expression. language: 'python' or 'hscript'."""
        return [TextContent(type="text", text=json.dumps(_parm_set_expression(node_path, parm_name, expr, language)))]

    @app.tool("parm_get_all")
    async def parm_get_all(node_path: str) -> list[TextContent]:
        """Get all parameters of a node with their current evaluated values."""
        return [TextContent(type="text", text=json.dumps(_parm_get_all(node_path)))]

    @app.tool("parm_revert")
    async def parm_revert(node_path: str, parm_name: str) -> list[TextContent]:
        """Revert a parameter to its default value."""
        return [TextContent(type="text", text=json.dumps(_parm_revert(node_path, parm_name)))]

    @app.tool("parm_lock")
    async def parm_lock(node_path: str, parm_name: str, on: bool) -> list[TextContent]:
        """Lock or unlock a parameter."""
        return [TextContent(type="text", text=json.dumps(_parm_lock(node_path, parm_name, on)))]

    @app.tool("parm_keyframe_set")
    async def parm_keyframe_set(node_path: str, parm_name: str, frame: float = None, value: float = None) -> list[TextContent]:
        """Set a keyframe on a parameter. Defaults to current frame and current value."""
        return [TextContent(type="text", text=json.dumps(_parm_keyframe_set(node_path, parm_name, frame, value)))]

    @app.tool("parm_keyframe_delete")
    async def parm_keyframe_delete(node_path: str, parm_name: str, frame: float) -> list[TextContent]:
        """Delete a keyframe at a specific frame."""
        return [TextContent(type="text", text=json.dumps(_parm_keyframe_delete(node_path, parm_name, frame)))]

    @app.tool("parm_keyframes_list")
    async def parm_keyframes_list(node_path: str, parm_name: str) -> list[TextContent]:
        """List all keyframes on a parameter with values and expressions."""
        return [TextContent(type="text", text=json.dumps(_parm_keyframes_list(node_path, parm_name)))]

    @app.tool("parm_link")
    async def parm_link(src_node: str, src_parm: str, dst_node: str, dst_parm: str) -> list[TextContent]:
        """Link dst_node/dst_parm to src_node/src_parm via ch() expression."""
        return [TextContent(type="text", text=json.dumps(_parm_link(src_node, src_parm, dst_node, dst_parm)))]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_parameters.py -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add houdini_side/tools/parameters.py tests/test_parameters.py
git commit -m "feat: 10 parameter tools (get/set/expr/keyframes/lock/link)"
```

---

## Task 8: Geometry tools (8 tools)

**Files:**
- Create: `houdini_side/tools/geometry.py`
- Create: `tests/test_geometry.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_geometry.py
import types, pytest

def _make_geo(npoints=10, nprims=4):
    g = types.SimpleNamespace()
    g.pointCount = lambda: npoints
    g.primCount = lambda: nprims
    g.vertexCount = lambda: nprims * 4
    g.pointAttribs = lambda: []
    g.primAttribs = lambda: []
    g.vertexAttribs = lambda: []
    g.globalAttribs = lambda: []
    g.pointGroups = lambda: []
    g.primGroups = lambda: []
    g.vertexGroups = lambda: []
    g.edgeGroups = lambda: []
    bbox = types.SimpleNamespace()
    bbox.minvec = lambda: types.SimpleNamespace(x=lambda:-1.0, y=lambda:-1.0, z=lambda:-1.0)
    bbox.maxvec = lambda: types.SimpleNamespace(x=lambda: 1.0, y=lambda: 1.0, z=lambda: 1.0)
    bbox.sizevec = lambda: types.SimpleNamespace(x=lambda: 2.0, y=lambda: 2.0, z=lambda: 2.0)
    bbox.center = lambda: types.SimpleNamespace(x=lambda: 0.0, y=lambda: 0.0, z=lambda: 0.0)
    g.boundingBox = lambda: bbox
    g.save = lambda path: None
    return g

def _make_sop(geo):
    sop = types.SimpleNamespace()
    sop.geometry = lambda: geo
    return sop

def test_geo_info(mock_hou):
    geo = _make_geo(100, 50)
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_info
    result = _geo_info("/obj/geo1/box1")
    assert result["success"] is True
    assert result["data"]["point_count"] == 100
    assert result["data"]["prim_count"] == 50

def test_geo_bbox(mock_hou):
    geo = _make_geo()
    sop = _make_sop(geo)
    mock_hou.node = lambda p: sop
    from houdini_side.tools.geometry import _geo_bbox
    result = _geo_bbox("/obj/geo1/box1")
    assert result["success"] is True
    assert result["data"]["min"] == [-1.0, -1.0, -1.0]
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_geometry.py -v
```

- [ ] **Step 3: Implement `houdini_side/tools/geometry.py`**

```python
"""SOP geometry inspection and export tools."""
import json
import hou
from houdini_side.dispatcher import dispatch, ok, err


def _geo_info(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            if geo is None:
                raise ValueError(f"No geometry on node: {sop_path}")
            return ok({
                "point_count": geo.pointCount(),
                "prim_count": geo.primCount(),
                "vertex_count": geo.vertexCount(),
                "point_attribs": [a.name() for a in geo.pointAttribs()],
                "prim_attribs": [a.name() for a in geo.primAttribs()],
                "vertex_attribs": [a.name() for a in geo.vertexAttribs()],
                "global_attribs": [a.name() for a in geo.globalAttribs()],
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_attributes(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()

            def attrib_info(a):
                return {
                    "name": a.name(),
                    "type": str(a.dataType()),
                    "size": a.size(),
                    "default": list(a.defaultValue()) if hasattr(a.defaultValue(), '__iter__') else a.defaultValue(),
                }

            return ok({
                "point": [attrib_info(a) for a in geo.pointAttribs()],
                "prim": [attrib_info(a) for a in geo.primAttribs()],
                "vertex": [attrib_info(a) for a in geo.vertexAttribs()],
                "global": [attrib_info(a) for a in geo.globalAttribs()],
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_attribute_values(sop_path: str, attrib_name: str, max_count: int = 100):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            attrib = (geo.findPointAttrib(attrib_name)
                      or geo.findPrimAttrib(attrib_name)
                      or geo.findVertexAttrib(attrib_name)
                      or geo.findGlobalAttrib(attrib_name))
            if attrib is None:
                raise ValueError(f"Attribute not found: {attrib_name}")
            if attrib.type() == hou.attribType.Point:
                items = list(geo.points())[:max_count]
                vals = [p.attribValue(attrib_name) for p in items]
            elif attrib.type() == hou.attribType.Prim:
                items = list(geo.prims())[:max_count]
                vals = [p.attribValue(attrib_name) for p in items]
            else:
                vals = []
            vals = [list(v) if hasattr(v, '__iter__') and not isinstance(v, str) else v for v in vals]
            return ok({"attrib": attrib_name, "count": len(vals), "values": vals})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_groups(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            return ok({
                "point_groups": [{"name": g.name(), "size": len(g.points())} for g in geo.pointGroups()],
                "prim_groups": [{"name": g.name(), "size": len(g.prims())} for g in geo.primGroups()],
                "vertex_groups": [{"name": g.name()} for g in geo.vertexGroups()],
                "edge_groups": [{"name": g.name()} for g in geo.edgeGroups()],
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_points(sop_path: str, max_count: int = 100):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            pts = list(geo.points())[:max_count]
            positions = [list(p.position()) for p in pts]
            return ok({"count": len(positions), "positions": positions})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_bbox(sop_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            bbox = geo.boundingBox()
            mn = bbox.minvec()
            mx = bbox.maxvec()
            sz = bbox.sizevec()
            ct = bbox.center()
            return ok({
                "min": [mn[0], mn[1], mn[2]],
                "max": [mx[0], mx[1], mx[2]],
                "size": [sz[0], sz[1], sz[2]],
                "center": [ct[0], ct[1], ct[2]],
            })
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_save(sop_path: str, file_path: str):
    try:
        def work():
            node = hou.node(sop_path)
            if node is None:
                raise ValueError(f"Node not found: {sop_path}")
            geo = node.geometry()
            geo.save(file_path)
            return ok({"saved_to": file_path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def _geo_load(parent_path: str, file_path: str):
    try:
        def work():
            with hou.undos.group("mcp: load geometry"):
                parent = hou.node(parent_path)
                if parent is None:
                    raise ValueError(f"Parent not found: {parent_path}")
                file_sop = parent.createNode("file")
                file_sop.parm("file").set(file_path)
                return ok({"node": file_sop.path(), "file": file_path})
        return dispatch(work)
    except Exception as e:
        return err(e)


def register(app):
    from mcp.types import TextContent

    @app.tool("geo_info")
    async def geo_info(sop_path: str) -> list[TextContent]:
        """Get geometry statistics: point/prim/vertex counts and attribute names."""
        return [TextContent(type="text", text=json.dumps(_geo_info(sop_path)))]

    @app.tool("geo_attributes")
    async def geo_attributes(sop_path: str) -> list[TextContent]:
        """List all attributes with type, size, and default value."""
        return [TextContent(type="text", text=json.dumps(_geo_attributes(sop_path)))]

    @app.tool("geo_attribute_values")
    async def geo_attribute_values(sop_path: str, attrib_name: str, max_count: int = 100) -> list[TextContent]:
        """Get first max_count values of a point or prim attribute."""
        return [TextContent(type="text", text=json.dumps(_geo_attribute_values(sop_path, attrib_name, max_count)))]

    @app.tool("geo_groups")
    async def geo_groups(sop_path: str) -> list[TextContent]:
        """List all point/prim/vertex/edge groups with their sizes."""
        return [TextContent(type="text", text=json.dumps(_geo_groups(sop_path)))]

    @app.tool("geo_points")
    async def geo_points(sop_path: str, max_count: int = 100) -> list[TextContent]:
        """Get point positions (first max_count points)."""
        return [TextContent(type="text", text=json.dumps(_geo_points(sop_path, max_count)))]

    @app.tool("geo_bbox")
    async def geo_bbox(sop_path: str) -> list[TextContent]:
        """Get the bounding box: min, max, size, center."""
        return [TextContent(type="text", text=json.dumps(_geo_bbox(sop_path)))]

    @app.tool("geo_save")
    async def geo_save(sop_path: str, file_path: str) -> list[TextContent]:
        """Export geometry to file (.bgeo, .obj, .fbx, .usd)."""
        return [TextContent(type="text", text=json.dumps(_geo_save(sop_path, file_path)))]

    @app.tool("geo_load")
    async def geo_load(parent_path: str, file_path: str) -> list[TextContent]:
        """Create a File SOP loading geometry from file_path inside parent_path."""
        return [TextContent(type="text", text=json.dumps(_geo_load(parent_path, file_path)))]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_geometry.py -v
# Expected: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add houdini_side/tools/geometry.py tests/test_geometry.py
git commit -m "feat: 8 geometry tools (info, attributes, groups, points, bbox, save/load)"
```

---

## Task 9: Remaining tool modules (pattern-based)

The following modules follow the **exact same pattern** established in Tasks 5-8:
1. Private `_fn()` functions that call `dispatch(work)` and return `ok()/err()`
2. A `register(app)` function with `@app.tool()` decorators
3. All destructive ops wrapped in `hou.undos.group("mcp: ...")`

Implement each module in order. Full signatures below.

### `houdini_side/tools/transforms.py` — 6 tools

```python
def _obj_transform_get(obj_path: str, space: str = "world"):
    # space: "world" or "local"
    # node = hou.node(obj_path) as ObjNode
    # m = node.worldTransform() if space == "world" else node.localTransform()
    # return ok({"matrix": [list(row) for row in m.asTuple()]})

def _obj_transform_set(obj_path: str, matrix4x4: list):
    # m = hou.Matrix4(matrix4x4)
    # node.setWorldTransform(m)

def _obj_translate(obj_path: str, tx: float, ty: float, tz: float):
    # node.parmTuple("t").set((tx, ty, tz))

def _obj_rotate(obj_path: str, rx: float, ry: float, rz: float):
    # node.parmTuple("r").set((rx, ry, rz))

def _obj_scale(obj_path: str, sx: float, sy: float, sz: float):
    # node.parmTuple("s").set((sx, sy, sz))

def _obj_parent(child_path: str, parent_path=None):
    # child = hou.node(child_path)
    # if parent_path: child.setInput(0, hou.node(parent_path))
    # else: child.setInput(0, None)
```

- [ ] Implement transforms.py following above signatures
- [ ] Run: `python -m pytest tests/ -v -k transform` (add at least 2 tests)
- [ ] Commit: `git commit -m "feat: 6 object transform tools"`

---

### `houdini_side/tools/rendering.py` — 6 tools

```python
def _rop_list(network_path: str = "/out"):
    # Recurse children of network_path, find nodes of ropNodeTypeCategory

def _rop_render(rop_path: str, frame_range: list = None, step: float = 1.0):
    # node = hou.node(rop_path)
    # if frame_range: node.render(frame_range=frame_range, res_fraction=1.0, ignore_inputs=False)
    # else: node.render()

def _rop_render_status(rop_path: str):
    # returns node cook state via node.isCooking() or similar

def _rop_get_output(rop_path: str):
    # parm names vary: "vm_picture" (Mantra), "picture" (Karma), "copoutput" etc.
    # Try common output parm names and return first non-None

def _rop_set_output(rop_path: str, output_path: str):
    # Same parm name detection, then parm.set(output_path)

def _rop_frame_range_override(rop_path: str, start: float, end: float):
    # node.parm("trange").set(1)  # enable override
    # node.parmTuple("f").set((start, end, 1))
```

- [ ] Implement rendering.py
- [ ] Add 2 tests to `tests/test_rendering.py`
- [ ] Commit: `git commit -m "feat: 6 ROP rendering tools"`

---

### `houdini_side/tools/animation.py` — 8 tools

```python
def _time_get():     # hou.frame(), hou.time()
def _time_set(frame: float):   # hou.setFrame(frame)
def _fps_get():      # hou.fps()
def _fps_set(fps: float):      # hou.setFps(fps)
def _frame_range_get():        # hou.playbar.frameRange()
def _frame_range_set(start: float, end: float):  # hou.playbar.setFrameRange(start, end)
def _channel_list(node_path: str):
    # [p.name() for p in node.parms() if p.keyframes()]
def _keyframe_list(node_path: str, parm_name: str):
    # parm.keyframes() -> [{frame, value, expression, slope}]
```

- [ ] Implement animation.py
- [ ] Add 3 tests: `test_time_get`, `test_fps_get`, `test_channel_list`
- [ ] Commit: `git commit -m "feat: 8 animation and time tools"`

---

### `houdini_side/tools/hda.py` — 8 tools

```python
def _hda_list():
    # hou.hda.loadedFiles() -> list paths
    # For each: hou.hda.definitionsInFile(path) -> list HDADefinition

def _hda_info(hda_node_type: str):
    # hou.hdaDefinition(hou.sopNodeTypeCategory(), hda_node_type, None)

def _hda_install(hda_path: str):
    # hou.hda.installFile(hda_path)

def _hda_uninstall(hda_node_type: str):
    # def_obj.destroy()

def _hda_save(node_path: str, hda_file_path: str = None):
    # node.type().definition().save(hda_file_path or existing_path)

def _hda_create(node_paths: list, hda_name: str, hda_label: str, hda_file_path: str):
    # nodes = [hou.node(p) for p in node_paths]
    # hou.Node.createDigitalAsset(nodes[0], hda_name, hda_file_path, hda_label)

def _hda_section_get(hda_node_type: str, section_name: str):
    # defn.section(section_name).contents()

def _hda_section_set(hda_node_type: str, section_name: str, content: str):
    # defn.section(section_name).setContents(content)
```

- [ ] Implement hda.py
- [ ] Add 2 tests (mock hou.hda module)
- [ ] Commit: `git commit -m "feat: 8 HDA digital asset tools"`

---

### `houdini_side/tools/dynamics.py` — 5 tools

```python
def _dop_sim_enable(dop_net_path: str, on: bool):
    # node.parm("resimulate") or hou.setSimulationEnabled(on)

def _dop_sim_reset(dop_net_path: str):
    # node = hou.node(dop_net_path); node.parm("resimulate").pressButton()

def _dop_object_list(dop_net_path: str):
    # sim = node.simulation(); [obj.name() for obj in sim.objects()]

def _dop_object_info(dop_net_path: str, object_name: str):
    # sim.findObject(object_name) -> DopObject

def _dop_data_get(dop_net_path: str, object_name: str, data_name: str):
    # obj.findData(data_name) -> DopData
```

- [ ] Implement dynamics.py
- [ ] Commit: `git commit -m "feat: 5 DOP dynamics tools"`

---

### `houdini_side/tools/solaris.py` — 6 tools

```python
def _lop_stage_info(lop_path: str):
    # node = hou.node(lop_path); stage = node.stage()
    # stage.GetPseudoRoot().GetAllChildren()

def _lop_prim_list(lop_path: str, prim_path: str = "/"):
    # stage.GetPrimAtPath(prim_path).GetAllChildren()

def _lop_prim_info(lop_path: str, prim_path: str):
    # prim.GetAttributes(), prim.GetVariantSets()

def _lop_save_usd(lop_path: str, file_path: str):
    # stage.Export(file_path) or node.stage().Export(file_path)

def _lop_variant_set(lop_path: str, prim_path: str, varset: str, variant: str):
    # stage.GetPrimAtPath(prim_path).GetVariantSets().SetSelection(varset, variant)

def _lop_load_masks(lop_path: str):
    # node.loadMasks() -> LopViewportLoadMasks
```

- [ ] Implement solaris.py (requires `pxr` module — guard with try/except ImportError)
- [ ] Commit: `git commit -m "feat: 6 Solaris/USD LOP tools"`

---

### `houdini_side/tools/pdg.py` — 5 tools

```python
def _pdg_cook(top_net_path: str):
    # node = hou.node(top_net_path); node.executeGraph(block=False)

def _pdg_dirty(top_net_path: str, node_name: str = None):
    # node.dirtyAllTasks(remove_outputs=False) or specific child

def _pdg_cancel(top_net_path: str):
    # node.cancelCook()

def _pdg_status(top_net_path: str):
    # node.cookState() -> hou.topCookState.*

def _pdg_output_list(top_net_path: str, node_name: str = None):
    # node.workItemOutputFiles()
```

- [ ] Implement pdg.py
- [ ] Commit: `git commit -m "feat: 5 PDG/TOP tools"`

---

### `houdini_side/tools/takes.py` — 4 tools

```python
def _take_list():
    # hou.takes.takes() -> list Take

def _take_create(name: str, parent: str = None):
    # hou.takes.rootTake().addChildTake(name)

def _take_set_current(name: str):
    # hou.takes.setCurrentTake(hou.takes.findTake(name))

def _take_parm_include(node_path: str, parm_name: str):
    # hou.takes.currentTake().addParmTuple(node.parmTuple(parm_name))
```

- [ ] Implement takes.py
- [ ] Commit: `git commit -m "feat: 4 take management tools"`

---

### `houdini_side/tools/vex.py` — 7 tools

```python
def _vex_run(code: str, context: str = "sop"):
    # hou.runVex(code, context) or via attribwrangle approach

def _vex_context_list():
    # hou.vexContexts() -> list VexContext

def _vop_network_list(search_path: str = "/"):
    # Walk tree from search_path, find nodes with vopNodeTypeCategory children

def _vop_node_create(vop_net_path: str, node_type: str, name: str = None):
    # parent = hou.node(vop_net_path); parent.createNode(node_type, name)

def _vop_node_connect(from_path: str, from_port: str,
                       to_path: str, to_port: str):
    # Uses VOP input/output port names (strings, not indices)
    # to_node.setNamedInput(to_port, from_node, from_port)

def _vop_code_generate(vop_net_path: str):
    # node.type().definition() or node.parm("vopoutput") for compiled VEX

def _vop_snippet_set(snippet_node_path: str, code: str):
    # node.parm("snippet").set(code) — works for attribwrangle, vopsop etc.
```

- [ ] Implement vex.py
- [ ] Commit: `git commit -m "feat: 7 VEX/VOP tools"`

---

### `houdini_side/tools/utils.py` — 11 tools

```python
def _run_hscript(command: str):
    # out, err = hou.hscript(command); return ok({"stdout": out, "stderr": err})

def _eval_expression(expr: str):
    # result = hou.hscriptExpression(expr); return ok({"result": result})

def _expand_string(template: str):
    # return ok({"expanded": hou.expandString(template)})

def _find_file(filename: str):
    # return ok({"path": hou.findFile(filename)})

def _path_list():
    # return ok({"paths": list(hou.houdiniPath())})

def _env_get(var_name: str):
    # return ok({"value": hou.getenv(var_name)})

def _env_set(var_name: str, value: str):
    # hou.putenv(var_name, value)

def _file_references():
    # hou.fileReferences() -> list of (parm, filename)

def _undo():
    # hou.undos.performUndo()

def _redo():
    # hou.undos.performRedo()

def _update_mode_set(mode: str):
    # mode: "auto"|"manual"|"on_request"
    # hou.setUpdateMode(hou.updateMode.AutoUpdate / Manual / OnRequest)

def _perf_mon_start():
    # profile = hou.perfMon.startProfile("mcp")

def _perf_mon_stop():
    # profile.stop(); return ok({"stats": profile.stats()})

def _viewport_screenshot(file_path: str = None):
    # viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    # viewer.curViewport().saveViewToFile(file_path or "/tmp/mcp_screenshot.png")

def _node_bundle_list():
    # hou.nodeBundles() -> list NodeBundle
```

- [ ] Implement utils.py
- [ ] Commit: `git commit -m "feat: 11 utility tools (hscript, env, perf, screenshot, undo/redo)"`

---

## Task 10: Integration test suite

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Create integration smoke test**

```python
# tests/test_integration.py
"""
Run with: hython -m pytest tests/test_integration.py -v
These tests require a real Houdini installation.
"""
import pytest

# Skip all if not running under hython
pytestmark = pytest.mark.skipif(
    not __import__("sys").executable.endswith("hython"),
    reason="Integration tests require hython"
)

def test_session_info_real():
    import hou
    from houdini_side.tools.session import _session_info
    result = _session_info()
    assert result["success"] is True
    assert "version" in result["data"]
    assert result["data"]["version"]  # non-empty


def test_create_and_delete_node():
    import hou
    from houdini_side.tools.nodes import _node_create, _node_delete, _node_get
    hou.hipFile.clear(suppress_save_prompt=True)
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "test_mcp_geo")

    result = _node_get("/obj/test_mcp_geo")
    assert result["success"] is True
    assert result["data"]["type"] == "geo"

    del_result = _node_delete("/obj/test_mcp_geo")
    assert del_result["success"] is True
    assert hou.node("/obj/test_mcp_geo") is None


def test_parm_get_and_set():
    import hou
    from houdini_side.tools.parameters import _parm_get, _parm_set
    hou.hipFile.clear(suppress_save_prompt=True)
    geo = hou.node("/obj").createNode("geo", "parm_test")
    box = geo.createNode("box")
    _parm_set(box.path(), "sizex", 5.0)
    result = _parm_get(box.path(), "sizex")
    assert result["success"] is True
    assert abs(result["data"]["value"] - 5.0) < 0.001
    geo.destroy()


def test_geo_info_real():
    import hou
    from houdini_side.tools.geometry import _geo_info
    hou.hipFile.clear(suppress_save_prompt=True)
    geo = hou.node("/obj").createNode("geo", "geo_test")
    box = geo.createNode("box")
    result = _geo_info(box.path())
    assert result["success"] is True
    assert result["data"]["point_count"] > 0
    geo.destroy()
```

- [ ] **Step 2: Run unit tests (all should pass)**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
# Expected: all pass
```

- [ ] **Step 3: Run integration tests (requires hython)**

```bash
hython -m pytest tests/test_integration.py -v
# Expected: 4 passed
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test suite for session, nodes, parms, geometry"
```

---

## Task 11: Setup script, README, and final wiring

**Files:**
- Create: `README.md`
- Finalize: `install/setup.sh`

- [ ] **Step 1: Write README.md**

```markdown
# houdini-mcp

MCP server for Houdini — gives Claude direct access to an active Houdini session.
105 tools across 16 categories: nodes, geometry, parameters, animation, rendering,
HDAs, DOPs, Solaris/USD, PDG, VEX/VOPs, takes, and utilities.

## Install

\`\`\`bash
bash install/setup.sh          # installs mcp SDK into hython
cp install/houdini_mcp.json $HOUDINI_USER_PREF_DIR/packages/
\`\`\`

Edit `houdini_mcp.json`: set `HOUDINI_MCP_ROOT` to this repo's path.

## Start

In Houdini: **Shelf → Houdini MCP → Start MCP Server**

## Configure Claude Desktop

\`\`\`json
{
  "mcpServers": {
    "houdini": { "url": "http://localhost:9876/sse" }
  }
}
\`\`\`

## Tools (105 total)

| Category | Count | Prefix |
|----------|-------|--------|
| Session & hip files | 6 | `hip_`, `session_` |
| Nodes | 16 | `node_`, `network_box_`, `sticky_note_` |
| Parameters | 10 | `parm_` |
| Geometry (SOPs) | 8 | `geo_` |
| Object Transforms | 6 | `obj_` |
| Rendering (ROPs) | 6 | `rop_` |
| Animation & Time | 8 | `time_`, `fps_`, `frame_range_`, `channel_`, `keyframe_` |
| Digital Assets | 8 | `hda_` |
| Dynamics (DOPs) | 5 | `dop_` |
| Solaris/USD (LOPs) | 6 | `lop_` |
| PDG/TOPs | 5 | `pdg_` |
| Takes | 4 | `take_` |
| VEX/VOPs | 7 | `vex_`, `vop_` |
| Utilities | 11 | various |

## Test

\`\`\`bash
python -m pytest tests/ -v --ignore=tests/test_integration.py  # unit tests
hython -m pytest tests/test_integration.py -v                  # integration
\`\`\`
```

- [ ] **Step 2: Final import check**

```bash
python -c "
import sys, types
sys.modules['hou'] = types.ModuleType('hou')
from houdini_side.tools import ALL_REGISTERS
print(f'Registered {len(ALL_REGISTERS)} tool modules')
"
```

- [ ] **Step 3: Final commit**

```bash
git add README.md install/setup.sh
git commit -m "docs: README, install script, project complete"
```

---

---

## QA Gate Tasks — `qa-ux-engineer` in Parallel

Each QA gate spawns a `qa-ux-engineer` subagent **in parallel** with the next implementation task. The agent reviews the files listed and returns a structured report (Critical / Major / Minor / Suggestions). The implementer reads the report and resolves Critical + Major issues before the next gate.

> **How to spawn in parallel:** When subagent-driven-development dispatches Task N+1, simultaneously dispatch the corresponding QA gate agent against the just-committed code.

---

### 🔍 QA Gate 1 — Architecture review
*Trigger: after Task 4 is committed. Run in parallel with Task 5.*
*Non-blocking — fix Critical issues before Task 6.*

**Agent:** `qa-ux-engineer`

**Files to review:**
- `houdini_side/dispatcher.py`
- `houdini_side/mcp_server.py`
- `houdini_side/startup.py`
- `houdini_side/tools/__init__.py`
- `tests/conftest.py`
- `tests/test_dispatcher.py`

**Review prompt for agent:**
```
Review the Houdini MCP server infrastructure code for a production Python MCP server that runs
as a daemon thread inside Houdini. This is NOT a frontend project — apply your QA methodology
to Python API quality, not UI. Focus on:

1. FUNCTIONAL CORRECTNESS: Is the thread-safety pattern in dispatcher.py correct?
   Does hou.postEventCallback() + threading.Event guarantee execution on the main thread?
   What happens on a 30-second timeout — does the server recover or hang?

2. ERROR HANDLING: Are all HOM exceptions (hou.ObjectWasDeleted, hou.PermissionError,
   hou.OperationFailed, hou.LicenseError) properly caught and serialized in err()?
   Can any exception escape the dispatch() boundary and crash the server thread?

3. API DESIGN (UX of the MCP tools): Are the ok()/err() response shapes consistent
   and easy for an LLM to parse? Is the JSON structure unambiguous?

4. TEST COVERAGE: Are the dispatcher unit tests sufficient? What cases are missing?

5. CONCURRENCY: Can two tool calls arrive simultaneously and cause a race condition
   on _result_holder or _exc_holder in dispatcher.py?

Files are in houdini-mcp/houdini_side/. Return Critical/Major/Minor findings.
```

- [ ] Spawn QA Gate 1 agent in parallel with Task 5
- [ ] Read QA Gate 1 report
- [ ] Fix any Critical issues before starting Task 6
- [ ] Commit fixes: `git commit -m "fix: QA Gate 1 — [description of fixes]"`

---

### 🔍 QA Gate 2 — Session + Node + Parameter tools
*Trigger: after Task 7 is committed. Run in parallel with Task 8.*
*Non-blocking — fix Critical issues before Task 9.*

**Agent:** `qa-ux-engineer`

**Files to review:**
- `houdini_side/tools/session.py`
- `houdini_side/tools/nodes.py`
- `houdini_side/tools/parameters.py`
- `tests/test_session.py`
- `tests/test_nodes.py`
- `tests/test_parameters.py`

**Review prompt for agent:**
```
Review 32 Python tool handlers for a production Houdini MCP server. These tools are the
"API surface" that Claude uses to control Houdini — their naming, parameter design, and
error messages are the UX. Focus on:

1. API NAMING CONSISTENCY: Are tool names, parameter names, and response keys consistent
   across all three modules? (e.g., does session use "path" where nodes use "node_path"?)

2. ERROR MESSAGES: Are error strings actionable? An LLM must understand from the error
   what went wrong and how to fix it. "Node not found: /obj/foo" is good.
   "Error" is not. Audit every raise ValueError() and err() call.

3. MISSING EDGE CASES:
   - node_connect: what if from_output index is out of range?
   - parm_set: what if value type mismatches parm type (e.g. string to float parm)?
   - node_create: what if node_type is invalid for the parent context?

4. TEST GAPS: What happy paths and edge cases are missing from the test files?
   Provide concrete Given/When/Then test cases for the 3 most critical gaps.

5. UNDO GROUP CONSISTENCY: Are all destructive operations wrapped in hou.undos.group()?
   Flag any that are missing.

Return Critical/Major/Minor findings with specific line-level references.
```

- [ ] Spawn QA Gate 2 agent in parallel with Task 8
- [ ] Read QA Gate 2 report
- [ ] Fix Critical + Major issues before starting Task 9
- [ ] Commit fixes: `git commit -m "fix: QA Gate 2 — [description]"`

---

### 🔍 QA Gate 3 — Geometry, Transforms, Rendering, Animation
*Trigger: after geometry.py, transforms.py, rendering.py, animation.py are committed (first half of Task 9).*
*Run in parallel with implementing hda.py through utils.py.*
*Non-blocking — fix Critical issues before integration tests.*

**Agent:** `qa-ux-engineer`

**Files to review:**
- `houdini_side/tools/geometry.py`
- `houdini_side/tools/transforms.py`
- `houdini_side/tools/rendering.py`
- `houdini_side/tools/animation.py`

**Review prompt for agent:**
```
Review 28 Python tool handlers (geometry, transforms, rendering, animation) for a
Houdini MCP server. Focus on:

1. DATA SERIALIZATION: geo_points() returns list of Vector3 positions. Are hou.Vector3
   objects correctly converted to [x, y, z] lists before JSON serialization?
   Same for Matrix4 in obj_transform_get — is it properly flattened?

2. GEO_ATTRIBUTE_VALUES: The attrib.type() comparison uses hou.attribType.Point/Prim.
   Are these enum comparisons correct, or should it be attrib.type() == hou.attribType.Point?
   Test the fallback for vertex/global attribs.

3. ROP_RENDER: rop_render() calls node.render() which is blocking in Houdini.
   Is there a timeout or progress callback? Could this block the MCP server indefinitely?
   Suggest a non-blocking approach or warn in the tool docstring.

4. ROP_GET_OUTPUT: The output parm name varies by renderer (vm_picture, picture, etc.).
   Is the list of tried parm names exhaustive for production renderers (Mantra, Karma,
   Arnold, Redshift, V-Ray)? List any missing ones.

5. ANIMATION EDGE CASES: frame_range_set — does hou.playbar.setFrameRange() exist?
   Verify the correct API call. What if start > end?

Return Critical/Major/Minor findings.
```

- [ ] Spawn QA Gate 3 agent after first 4 modules of Task 9 are done
- [ ] Read QA Gate 3 report
- [ ] Fix Critical issues before Task 10
- [ ] Commit fixes: `git commit -m "fix: QA Gate 3 — [description]"`

---

### 🔍 QA Gate 4 — Final quality sign-off [BLOCKING]
*Trigger: after Task 10 (integration tests) is committed.*
*BLOCKING — must resolve all Critical + Major issues before Task 11 (README + final commit).*

**Agent:** `qa-ux-engineer`

**Files to review:**
- `houdini_side/tools/hda.py`
- `houdini_side/tools/dynamics.py`
- `houdini_side/tools/solaris.py`
- `houdini_side/tools/pdg.py`
- `houdini_side/tools/takes.py`
- `houdini_side/tools/vex.py`
- `houdini_side/tools/utils.py`
- `tests/test_integration.py`
- All files in `houdini_side/tools/` for cross-cutting consistency

**Review prompt for agent:**
```
This is a final production readiness review of a Houdini MCP server with 105 tools.
Perform a COMPREHENSIVE review focused on:

1. CROSS-CUTTING CONSISTENCY (all tool modules):
   - Are all tool docstrings clear enough for an LLM to use the tool correctly?
   - Are parameter names consistent? (some use "node_path", some "path" — should be one convention)
   - Are all response "data" keys snake_case?
   - Does every tool return {"success": true/false, "data": {}, "warnings": []}?
     Find any that deviate from this contract.

2. SOLARIS/USD SAFETY: lop_* tools call pxr.Usd.Stage methods.
   - Is the pxr import guarded with try/except ImportError?
   - What happens if the LOP node hasn't cooked yet and stage() returns None?

3. VEX SECURITY: vop_snippet_set sets arbitrary code on a VEX Snippet node.
   Is this acceptable given run_python was explicitly removed for security?
   Should it have the same restrictions? Provide a recommendation.

4. INTEGRATION TEST COVERAGE:
   - Are the 4 integration tests sufficient for a production handoff?
   - What are the 3 highest-risk scenarios NOT covered by existing tests?
   - Write concrete hython test cases for those 3 scenarios.

5. OVERALL API UX SCORE: If Claude is the "user" of this API, rate:
   - Tool discoverability: are names and docstrings clear enough to use without docs?
   - Error recovery: are error messages actionable enough for Claude to self-correct?
   - Completeness: are there obvious gaps in the 105-tool surface?

Return Critical/Major/Minor findings + overall readiness verdict.
```

- [ ] Spawn QA Gate 4 agent after Task 10
- [ ] **BLOCKING**: Resolve ALL Critical issues
- [ ] Resolve Major issues (or document as known limitations in README)
- [ ] Commit fixes: `git commit -m "fix: QA Gate 4 — production readiness fixes"`
- [ ] Proceed to Task 11 only after QA Gate 4 is resolved

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|-----------|
| SSE server in Houdini thread | Task 3: `mcp_server.py` |
| Thread-safe hou.* dispatch | Task 2: `dispatcher.py` |
| Houdini package auto-load | Task 1: `houdini_mcp.json` |
| Shelf start/stop buttons | Task 4: `startup.py` |
| 6 session tools | Task 5 |
| 16 node tools | Task 6 |
| 10 parameter tools | Task 7 |
| 8 geometry tools | Task 8 |
| 6 transform tools | Task 9 (transforms) |
| 6 ROP tools | Task 9 (rendering) |
| 8 animation tools | Task 9 (animation) |
| 8 HDA tools | Task 9 (hda) |
| 5 DOP tools | Task 9 (dynamics) |
| 6 LOP/USD tools | Task 9 (solaris) |
| 5 PDG tools | Task 9 (pdg) |
| 4 take tools | Task 9 (takes) |
| 7 VEX/VOP tools | Task 9 (vex) |
| 11 utility tools | Task 9 (utils) |
| JSON `{success, data, warnings}` format | `dispatcher.py` ok()/err() |
| `hou.undos.group()` wrapping | All destructive tools |
| run_python removed (security) | Not included |
| Integration tests | Task 10 |
| Configurable port via env var | `mcp_server.py` + package JSON |
| Architecture QA review | QA Gate 1 |
| Tool API + error message QA | QA Gate 2 |
| Geo/rendering/animation QA | QA Gate 3 |
| Production readiness QA (BLOCKING) | QA Gate 4 |

All spec requirements covered. No gaps found.
