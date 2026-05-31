# Spec: SSE → Streamable HTTP Transport

**Date:** 2026-05-31
**Branch:** http

## Goal

Switch the Houdini MCP server from the legacy SSE transport to the MCP Streamable HTTP transport for better scalability, cleaner session management, and alignment with the MCP spec's recommended transport.

## Architecture

### Server (`houdini_side/mcp_server.py`)

- `_build_app(port: int)` — accepts port at build time; constructs `FastMCP` with built-in `TransportSecuritySettings(allowed_hosts=["localhost:{port}", "127.0.0.1:{port}"])`. The SDK's native DNS-rebinding protection replaces the custom `_make_security_middleware` entirely.
- `_run()` — calls `_mcp_app.streamable_http_app()` instead of `sse_app()`. No custom middleware added — security handled by FastMCP constructor argument.
- `start_server()` — passes resolved port to `_build_app(port)`.
- `_make_security_middleware()` — deleted.

### Endpoint change

| Before | After |
|--------|-------|
| `GET /sse` (persistent stream) | `POST /mcp` (single endpoint) |
| `POST /messages/` | — |

### Client config files

All three config locations update `"type"` and URL:

| File | Before | After |
|------|--------|-------|
| `.mcp.json` (project root) | `"type": "sse"`, `/sse` | `"type": "http"`, `/mcp` |
| `mcp-testing/.mcp.json` | _(no type)_, `/sse` | `"type": "http"`, `/mcp` |
| `~/.claude.json` | `"type": "sse"`, `/sse` | re-registered via `claude mcp add --transport http` |

### Documentation

`README.md`: update URL reference and transport description.

## What does NOT change

- Port (`9876`) and host binding (`127.0.0.1`)
- `asyncio.SelectorEventLoop()` workaround (Houdini haio policy still applies)
- All `@app.tool()` registrations
- Install scripts (`setup.sh`, `setup.ps1`, reference JSONs) — server-side only, no client URLs
- Tests — `test_integration.py` calls Houdini internals directly, no server URL references

## Security

`TransportSecuritySettings` in the MCP SDK covers the same DNS-rebinding attack surface as the removed custom middleware: it validates `Host` and `Origin` headers against the allowed lists.
