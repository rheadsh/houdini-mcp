# houdini-mcp

MCP server for Houdini — gives Claude direct access to an active Houdini session.
108 tools across 14 categories: nodes, geometry, parameters, animation, rendering,
HDAs, DOPs, Solaris/USD, PDG, VEX/VOPs, takes, and utilities.

Requires Houdini 20.0+ with an active session (not headless).

## Install

```bash
# 1. Install MCP SDK into Houdini's Python
bash install/setup.sh

# 2. Install the Houdini package (edits $HOUDINI_USER_PREF_DIR/packages/)
cp install/houdini_mcp.json "$HOUDINI_USER_PREF_DIR/packages/"
```

Edit `houdini_mcp.json` and set `HOUDINI_MCP_ROOT` to the absolute path of this repo.

## Start the server

In Houdini: **Shelf → Houdini MCP → Start MCP Server**

The server starts on `http://localhost:9876/sse` (configurable via `HOUDINI_MCP_PORT`).

## Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "houdini": {
      "url": "http://localhost:9876/sse"
    }
  }
}
```

## Optional: restrict file access

Set `HOUDINI_MCP_PROJECT_ROOT` to limit hip file operations to a directory:

```bash
export HOUDINI_MCP_PROJECT_ROOT=/projects/myshow
```

## Test

```bash
# Unit tests (no Houdini needed)
python -m pytest tests/ --ignore=tests/test_integration.py -v

# Integration tests (requires hython)
hython -m pytest tests/test_integration.py -v
```

## Tool categories (108 total)

| Category | Count | Prefix(es) |
|----------|-------|------------|
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
| Utilities | 13 | `run_hscript`, `eval_expression`, `expand_string`, `undo`, `redo`, etc. |

## Security notes

- The server binds to `127.0.0.1` only and enforces `Host`/`Origin` header validation
  to prevent DNS-rebinding attacks.
- `hda_section_set` can write executable Python into HDA sections — use with care.
- `HOUDINI_MCP_PROJECT_ROOT` restricts hip file paths to a directory sandbox.
- `run_python` (arbitrary Python execution) is intentionally excluded.
