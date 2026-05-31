# SSE → Streamable HTTP Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the Houdini MCP server from the legacy SSE transport to MCP Streamable HTTP on a new `http` branch.

**Architecture:** Replace `FastMCP.sse_app()` with `FastMCP.streamable_http_app()`, pass `TransportSecuritySettings` at construction time (removing the custom middleware), update all client config files from `/sse` to `/mcp`, and update documentation.

**Tech Stack:** Python 3.11, `mcp>=1.27` (`FastMCP`, `TransportSecuritySettings`), uvicorn, Starlette, `asyncio.SelectorEventLoop` (Houdini haio workaround)

---

### Task 1: Create the `http` branch

**Files:**
- No file changes — git only

- [ ] **Step 1: Create and switch to the branch**

```bash
git checkout -b http
```

Expected output: `Switched to a new branch 'http'`

- [ ] **Step 2: Verify**

```bash
git branch
```

Expected: `* http` is the active branch.

---

### Task 2: Rewrite `mcp_server.py` for Streamable HTTP

**Files:**
- Modify: `houdini_side/mcp_server.py`

The changes are:
- `_build_app()` gains a `port: int` parameter and constructs `FastMCP` with `TransportSecuritySettings` — replaces the custom middleware.
- `_make_security_middleware()` is deleted entirely.
- `start_server()` passes `port` to `_build_app(port)`.
- `_run()` calls `streamable_http_app()` instead of `sse_app()`, no middleware added.
- Log/print messages updated from `/sse` to `/mcp`.

- [ ] **Step 1: Replace the full file**

Write `houdini_side/mcp_server.py` with this exact content:

```python
"""
MCP Streamable HTTP server that runs as a daemon thread inside Houdini.

Usage (from Houdini Python Shell or startup script):
    from houdini_side.mcp_server import start_server, stop_server
    start_server()   # starts on $HOUDINI_MCP_PORT (default 9876)
    stop_server()    # graceful shutdown

Security: the server binds to 127.0.0.1 only. DNS-rebinding protection is
provided by FastMCP's built-in TransportSecuritySettings (Host/Origin header
validation). No external network access is possible by design.
"""
import os
import threading
import logging
from typing import Optional

log = logging.getLogger("houdini-mcp")

_server_thread: Optional[threading.Thread] = None
_mcp_app = None
_uvicorn_server = None          # tracked for clean shutdown
_start_lock = threading.Lock()  # prevents double-start race condition


def _build_app(port: int):
    from mcp.server.fastmcp import FastMCP
    from mcp.server.streamable_http import TransportSecuritySettings
    from houdini_side.tools import ALL_REGISTERS

    security = TransportSecuritySettings(
        allowed_hosts=[f"localhost:{port}", f"127.0.0.1:{port}"],
    )
    app = FastMCP("houdini-mcp", transport_security=security)
    for register_fn in ALL_REGISTERS:
        register_fn(app)
    return app


def start_server(port: Optional[int] = None):
    global _server_thread, _mcp_app, _uvicorn_server

    with _start_lock:
        if _server_thread and _server_thread.is_alive():
            log.warning("MCP server already running")
            return

        port = port or int(os.environ.get("HOUDINI_MCP_PORT", "9876"))
        _mcp_app = _build_app(port)

        def _run():
            global _uvicorn_server
            import asyncio
            import uvicorn

            assert _mcp_app is not None, "MCP app was not initialized before _run()"
            starlette_app = _mcp_app.streamable_http_app()

            config = uvicorn.Config(
                starlette_app, host="127.0.0.1", port=port,  # type: ignore[arg-type]
                log_level="warning",
            )
            _uvicorn_server = uvicorn.Server(config)

            # Houdini replaces the asyncio event loop *policy* with haio, so
            # asyncio.new_event_loop() still returns a haio loop that only
            # works on the main thread. Bypass the policy entirely by
            # instantiating the standard SelectorEventLoop directly.
            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_uvicorn_server.serve())
            finally:
                loop.close()

        _server_thread = threading.Thread(
            target=_run, name="houdini-mcp-server", daemon=True
        )
        _server_thread.start()
        log.info("Houdini MCP server started on http://127.0.0.1:%d/mcp", port)
        print(f"[houdini-mcp] Listening on http://127.0.0.1:{port}/mcp")


def stop_server():
    global _server_thread, _uvicorn_server

    if _uvicorn_server is not None:
        _uvicorn_server.should_exit = True
        if _server_thread is not None:
            _server_thread.join(timeout=5.0)
            if _server_thread.is_alive():
                log.warning("MCP server thread did not stop within 5s")
                print("[houdini-mcp] Warning: server thread still running after 5s")
            else:
                print("[houdini-mcp] Server stopped.")
    else:
        print("[houdini-mcp] Server was not running.")

    _server_thread = None
    _uvicorn_server = None
```

- [ ] **Step 2: Verify the import path for TransportSecuritySettings**

```bash
/Applications/Houdini/Current/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython -c "
from mcp.server.streamable_http import TransportSecuritySettings
from mcp.server.fastmcp import FastMCP
app = FastMCP('test', transport_security=TransportSecuritySettings(allowed_hosts=['localhost:9876']))
print('OK:', type(app.streamable_http_app()))
"
```

Expected: `OK: <class 'starlette.applications.Starlette'>`

- [ ] **Step 3: Commit**

```bash
git add houdini_side/mcp_server.py
git commit -m "feat: switch MCP transport from SSE to Streamable HTTP"
```

---

### Task 3: Update client config files

**Files:**
- Create: `.mcp.json` (project root)
- Modify: `mcp-testing/.mcp.json`

Both files need `"type": "http"` and the URL changed from `/sse` to `/mcp`.

- [ ] **Step 1: Write project-root `.mcp.json`**

```json
{
  "mcpServers": {
    "houdini": {
      "type": "http",
      "url": "http://localhost:9876/mcp"
    }
  }
}
```

Save as `.mcp.json` at the repo root.

- [ ] **Step 2: Update `mcp-testing/.mcp.json`**

```json
{
  "mcpServers": {
    "houdini": {
      "type": "http",
      "url": "http://localhost:9876/mcp"
    }
  }
}
```

- [ ] **Step 3: Re-register in user-level Claude Code config**

Remove the old SSE entry and add the HTTP one:

```bash
claude mcp remove houdini --scope user
claude mcp add --transport http --scope user houdini http://localhost:9876/mcp
```

Expected output on add: `Added HTTP MCP server houdini with URL: http://localhost:9876/mcp to user config`

- [ ] **Step 4: Commit**

```bash
git add .mcp.json mcp-testing/.mcp.json
git commit -m "config: update MCP client URLs from SSE /sse to HTTP /mcp"
```

---

### Task 4: Update README

**Files:**
- Modify: `README.md`

Two references need updating: the "Start the server" section and the "Configure Claude Desktop" snippet.

- [ ] **Step 1: Update "Start the server" section**

Find and replace in `README.md`:

```
The server starts on `http://localhost:9876/sse` (configurable via `HOUDINI_MCP_PORT`).
```

Replace with:

```
The server starts on `http://localhost:9876/mcp` (configurable via `HOUDINI_MCP_PORT`).
```

- [ ] **Step 2: Update the env variable table description**

Find:

```
| `HOUDINI_MCP_PORT` | `9876` | Local SSE server port |
```

Replace with:

```
| `HOUDINI_MCP_PORT` | `9876` | Local HTTP server port |
```

- [ ] **Step 3: Update "Configure Claude Desktop" snippet**

Find:

```json
{
  "mcpServers": {
    "houdini": {
      "url": "http://localhost:9876/sse"
    }
  }
}
```

Replace with:

```json
{
  "mcpServers": {
    "houdini": {
      "type": "http",
      "url": "http://localhost:9876/mcp"
    }
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update server URL from SSE /sse to HTTP /mcp"
```

---

### Task 5: Verify end-to-end

No code changes — this task confirms everything works before the branch is ready to merge.

- [ ] **Step 1: Start the server in Houdini Python Shell**

In Houdini → Windows → Python Shell:

```python
import importlib, houdini_side.mcp_server as m
importlib.reload(m)
m.start_server()
```

Expected output: `[houdini-mcp] Listening on http://127.0.0.1:9876/mcp`

- [ ] **Step 2: Verify the endpoint responds**

```bash
curl -s -X POST http://localhost:9876/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' \
  | head -3
```

Expected: a JSON-RPC response or SSE event starting with `event:` / `data:`.

- [ ] **Step 3: Restart Claude Code and verify MCP connection**

Quit and reopen Claude Code from the repo directory, then run:

```
/mcp
```

Expected: `houdini` listed with status `connected` (not `pending` or `error`).

- [ ] **Step 4: Confirm the branch is ready**

```bash
git log --oneline http ~3
```

Expected: three commits visible — server change, config update, docs update.
