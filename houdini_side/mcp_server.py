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
    from mcp.server.transport_security import TransportSecuritySettings
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

        import uvicorn

        starlette_app = _mcp_app.streamable_http_app()
        config = uvicorn.Config(
            starlette_app, host="127.0.0.1", port=port,  # type: ignore[arg-type]
            log_level="warning",
        )
        _uvicorn_server = uvicorn.Server(config)

        def _run():
            import asyncio

            assert _mcp_app is not None, "MCP app was not initialized before _run()"

            # Houdini replaces the asyncio event loop *policy* with haio, so
            # asyncio.new_event_loop() still returns a haio loop that only
            # works on the main thread. Bypass the policy entirely by
            # instantiating the standard SelectorEventLoop directly.
            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)
            try:
                server = _uvicorn_server
                assert server is not None
                loop.run_until_complete(server.serve())
            finally:
                loop.close()

        _server_thread = threading.Thread(
            target=_run, name="houdini-mcp-server", daemon=True
        )
        _server_thread.start()
        log.info("Houdini MCP server starting on http://127.0.0.1:%d/mcp", port)
        print(f"[houdini-mcp] Starting on http://127.0.0.1:{port}/mcp")


def stop_server():
    global _server_thread, _uvicorn_server

    if _uvicorn_server is not None:
        _uvicorn_server.should_exit = True
        if _server_thread is not None:
            _server_thread.join(timeout=5.0)
            if _server_thread.is_alive():
                log.warning("MCP server thread did not stop within 5s")
                print("[houdini-mcp] Warning: server thread still running after 5s")
                return
            else:
                print("[houdini-mcp] Server stopped.")
    else:
        print("[houdini-mcp] Server was not running.")

    _server_thread = None
    _uvicorn_server = None
