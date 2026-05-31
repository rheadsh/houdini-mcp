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
    from houdini_side.tools import ALL_REGISTERS

    app = Server("houdini-mcp")

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
        _server_thread = None
    print("[houdini-mcp] Server stopped.")
