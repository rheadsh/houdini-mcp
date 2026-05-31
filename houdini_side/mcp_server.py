"""
MCP SSE server that runs as a daemon thread inside Houdini.

Usage (from Houdini Python Shell or startup script):
    from houdini_side.mcp_server import start_server, stop_server
    start_server()   # starts on $HOUDINI_MCP_PORT (default 9876)
    stop_server()    # graceful shutdown

Security: the server binds to 127.0.0.1 only and enforces Host/Origin header
validation to prevent DNS-rebinding attacks. No external network access is
possible by design.
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


def _build_app():
    from mcp.server.fastmcp import FastMCP
    from houdini_side.tools import ALL_REGISTERS

    app = FastMCP("houdini-mcp")
    for register_fn in ALL_REGISTERS:
        register_fn(app)
    return app


def _make_security_middleware(port: int):
    """
    Returns ASGI middleware that rejects DNS-rebinding and cross-origin requests.

    Blocks any request whose Host header is not 127.0.0.1:<port> or localhost:<port>,
    and any request whose Origin header is present and not a loopback origin.
    This defeats the DNS-rebinding attack: a rogue site cannot redirect its own
    origin to 127.0.0.1 because the browser will send an Origin header the
    middleware will reject.
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    _valid_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    _valid_origin_prefixes = (
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"https://127.0.0.1:{port}",
        f"https://localhost:{port}",
    )

    class _SecurityMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            host = request.headers.get("host", "")
            origin = request.headers.get("origin", "")

            if host not in _valid_hosts:
                log.warning("MCP: rejected request with Host=%r", host)
                return Response("Forbidden", status_code=403)

            if origin and not any(origin.startswith(p) for p in _valid_origin_prefixes):
                log.warning("MCP: rejected cross-origin request Origin=%r", origin)
                return Response("Forbidden", status_code=403)

            return await call_next(request)

    return _SecurityMiddleware


def start_server(port: Optional[int] = None):
    global _server_thread, _mcp_app, _uvicorn_server

    with _start_lock:
        if _server_thread and _server_thread.is_alive():
            log.warning("MCP server already running")
            return

        port = port or int(os.environ.get("HOUDINI_MCP_PORT", "9876"))
        _mcp_app = _build_app()

        def _run():
            global _uvicorn_server
            import asyncio
            import uvicorn

            assert _mcp_app is not None, "MCP app was not initialized before _run()"
            security_mw = _make_security_middleware(port)  # type: ignore[arg-type]
            starlette_app = _mcp_app.sse_app()
            starlette_app.add_middleware(security_mw)

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
        log.info("Houdini MCP server started on http://127.0.0.1:%d/sse", port)
        print(f"[houdini-mcp] Listening on http://127.0.0.1:{port}/sse")


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
