# Houdini MCP Server — Design Spec

**Date:** 2026-05-31  
**Status:** Implemented

## Summary

Production MCP server (108 tools, 16 categories) running as an SSE daemon thread inside
an active Houdini session. Gives Claude full programmatic access to the Houdini Python API
(`hou.*`) for scene generation, technical assistance, and production pipeline automation.

## Architecture

```
Claude Desktop / Claude Code
        │
        │ HTTP SSE  →  http://localhost:9876/sse
        ▼
┌────────────────────────────────────────────┐
│  Houdini (proceso vivo)                    │
│  Thread: MCP SSE Server                   │
│  ┌──────────────────────────────────────┐  │
│  │  Tool handler → dispatch(work)       │  │
│  │  → hou.postEventCallback()           │  │
│  │  → executes hou.* on main thread     │  │
│  │  → serializes to JSON               │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

## Key Decisions

- **Thread safety**: `hou.postEventCallback()` + `threading.Event` (30s timeout with cancellation flag)
- **Security**: DNS-rebinding middleware (Host/Origin header checks), path validation for hip files
- **Response format**: `{"success": bool, "data": {}, "warnings": []}` for all 108 tools
- **Undo**: All destructive ops wrapped in `hou.undos.group("mcp: ...")`
- **No run_python**: Excluded for security; `hda_section_set` carries explicit code-execution warning
- **USD/Solaris**: `_require_pxr()` guard on all LOP tools

## Tool Categories

| Category | Count | Key Tools |
|----------|-------|-----------|
| Session & hip files | 6 | `hip_load`, `hip_save`, `session_info` |
| Nodes | 16 | `node_create`, `node_connect`, `node_set_flag` |
| Parameters | 10 | `parm_get`, `parm_set`, `parm_set_expression` |
| Geometry (SOPs) | 8 | `geo_info`, `geo_bbox`, `geo_attribute_values` |
| Object Transforms | 6 | `obj_translate`, `obj_transform_get` |
| Rendering (ROPs) | 6 | `rop_render`, `rop_set_output` |
| Animation & Time | 8 | `time_set`, `frame_range_set`, `keyframe_list` |
| Digital Assets | 8 | `hda_create`, `hda_section_get` |
| Dynamics (DOPs) | 5 | `dop_sim_reset`, `dop_object_list` |
| Solaris/USD (LOPs) | 6 | `lop_stage_info`, `lop_prim_list` |
| PDG/TOPs | 5 | `pdg_cook`, `pdg_status` |
| Takes | 4 | `take_create`, `take_set_current` |
| VEX/VOPs | 7 | `vop_snippet_set`, `vop_node_create` |
| Utilities | 13 | `run_hscript`, `undo`, `viewport_screenshot` |
