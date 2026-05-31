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

## Tool reference

All tools return `{"success": true, "data": {...}}` on success or `{"success": false, "error": "...", "error_type": "..."}` on failure.

### Session & hip files

| Tool | Parameters | Description |
|------|-----------|-------------|
| `session_info` | — | Get Houdini version, application name, user and UI availability |
| `hip_info` | — | Get current scene file path and unsaved-changes status |
| `hip_new` | — | Clear the scene (new empty hip file). Unsaved changes will be lost |
| `hip_load` | `path: str` | Load a `.hip` or `.hiplc` file from disk |
| `hip_save` | `path?: str` | Save the current scene. Uses current path if omitted |
| `hip_merge` | `path: str` | Merge another `.hip` file into the current scene |

### Nodes

| Tool | Parameters | Description |
|------|-----------|-------------|
| `node_get` | `path: str` | Get node info: type, flags, connections, color, position |
| `node_list` | `network_path: str`, `type_filter?: str` | List all children of a network. Optional type filter (e.g. `'box'`) |
| `node_create` | `parent_path: str`, `node_type: str`, `name?: str` | Create a node. Use `node_type_list` to find valid type names |
| `node_delete` | `path: str` | Delete a node permanently (undoable) |
| `node_rename` | `path: str`, `new_name: str` | Rename a node |
| `node_move` | `path: str`, `x: float`, `y: float` | Move a node to `(x, y)` in the network editor |
| `node_connect` | `from_path: str`, `from_output: int`, `to_path: str`, `to_input: int` | Wire `from_path[from_output]` to `to_path[to_input]` |
| `node_disconnect` | `to_path: str`, `to_input: int` | Disconnect an input on a node |
| `node_bypass` | `path: str`, `on: bool` | Toggle bypass flag |
| `node_set_flag` | `path: str`, `flag: str`, `on: bool` | Set a flag: `display` \| `render` \| `template` \| `highlight` |
| `node_cook` | `path: str` | Force-cook a node. Required before `geo_info` if the node hasn't cooked yet |
| `node_layout` | `network_path: str` | Auto-layout all nodes in a network |
| `node_type_list` | `context: str` | List all node types in context: `sop\|obj\|dop\|rop\|lop\|top\|cop2\|vop\|shop\|chop` |
| `node_copy_paste` | `source_paths: list`, `network_path: str` | Copy nodes and paste into `network_path` |
| `network_box_create` | `network_path: str`, `name: str`, `color?: [r,g,b]` | Create a labeled network box. Color is floats 0–1 |
| `sticky_note_create` | `network_path: str`, `text: str`, `x: float`, `y: float` | Create a sticky note at position `(x, y)` |

### Parameters

| Tool | Parameters | Description |
|------|-----------|-------------|
| `parm_get` | `node_path: str`, `parm_name: str` | Get the evaluated value of a parameter or parameter tuple |
| `parm_set` | `node_path: str`, `parm_name: str`, `value` | Set a parameter. Use a list for vector params like `t` or `s` |
| `parm_set_expression` | `node_path: str`, `parm_name: str`, `expr: str`, `language?: str` | Set a channel expression. `language`: `'python'` (default) or `'hscript'` |
| `parm_get_all` | `node_path: str` | Get all parameters with their current evaluated values |
| `parm_revert` | `node_path: str`, `parm_name: str` | Revert a parameter to its default value |
| `parm_lock` | `node_path: str`, `parm_name: str`, `on: bool` | Lock or unlock a parameter |
| `parm_keyframe_set` | `node_path: str`, `parm_name: str`, `frame?: float`, `value?: float` | Set a keyframe. Defaults to current frame and current value |
| `parm_keyframe_delete` | `node_path: str`, `parm_name: str`, `frame: float` | Delete a keyframe at a specific frame number |
| `parm_keyframes_list` | `node_path: str`, `parm_name: str` | List all keyframes with frame, value, expression, slope |
| `parm_link` | `src_node: str`, `src_parm: str`, `dst_node: str`, `dst_parm: str` | Link `dst_node/dst_parm` to `src_node/src_parm` via `ch()` expression |

### Geometry (SOPs)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `geo_info` | `sop_path: str` | Get geometry stats: point/prim/vertex counts and attribute names |
| `geo_attributes` | `sop_path: str` | List all attributes with type, size, and default value |
| `geo_attribute_values` | `sop_path: str`, `attrib_name: str`, `max_count?: int` | Get the first `max_count` values of a point or prim attribute |
| `geo_groups` | `sop_path: str` | List all point/prim/vertex/edge groups with sizes |
| `geo_points` | `sop_path: str`, `max_count?: int` | Get point positions as `[x, y, z]` lists |
| `geo_bbox` | `sop_path: str` | Get bounding box: `min`, `max`, `size`, `center` as `[x,y,z]` lists |
| `geo_save` | `sop_path: str`, `file_path: str` | Export geometry to file (`.bgeo`, `.bgeo.sc`, `.obj`, `.fbx`, `.usd`) |
| `geo_load` | `parent_path: str`, `file_path: str` | Create a File SOP inside `parent_path` loading geometry from `file_path` |

### Object transforms

| Tool | Parameters | Description |
|------|-----------|-------------|
| `obj_transform_get` | `obj_path: str`, `space?: str` | Get a 4×4 transform matrix. `space`: `'world'` (default) or `'local'` |
| `obj_transform_set` | `obj_path: str`, `matrix4x4: list` | Set world transform from a 4×4 matrix (list of 4 rows of 4 floats) |
| `obj_translate` | `obj_path: str`, `tx: float`, `ty: float`, `tz: float` | Set translation parameters |
| `obj_rotate` | `obj_path: str`, `rx: float`, `ry: float`, `rz: float` | Set rotation parameters (degrees) |
| `obj_scale` | `obj_path: str`, `sx: float`, `sy: float`, `sz: float` | Set scale parameters |
| `obj_parent` | `child_path: str`, `parent_path?: str` | Parent child to parent. Pass `null` to unparent |

### Rendering (ROPs)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `rop_list` | `network_path?: str` | List all ROP nodes in a network (default: `/out`) |
| `rop_render` | `rop_path: str`, `frame_range?: [start,end]`, `step?: float` | Execute a render. **Blocking** — will timeout if render exceeds 30 s. For long renders use `pdg_cook` instead |
| `rop_render_status` | `rop_path: str` | Check whether a ROP is currently cooking |
| `rop_get_output` | `rop_path: str` | Get the render output path (tries Mantra, Karma, Redshift, Arnold, etc.) |
| `rop_set_output` | `rop_path: str`, `output_path: str` | Set the render output path |
| `rop_frame_range_override` | `rop_path: str`, `start: float`, `end: float` | Override the frame range on a ROP (enables `trange`, sets `f` parm) |

### Animation & time

| Tool | Parameters | Description |
|------|-----------|-------------|
| `time_get` | — | Get current frame, time in seconds, and FPS |
| `time_set` | `frame: float` | Jump to a specific frame number |
| `fps_get` | — | Get the scene FPS |
| `fps_set` | `fps: float` | Set the scene FPS (must be positive) |
| `frame_range_get` | — | Get the global playbar frame range (start, end) |
| `frame_range_set` | `start: float`, `end: float` | Set the global playbar frame range |
| `channel_list` | `node_path: str` | List all animated parameters (those with keyframes) on a node |
| `keyframe_list` | `node_path: str`, `parm_name: str` | List all keyframes with frame, value, expression, slope |

### Digital assets (HDAs)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `hda_list` | — | List all installed HDAs with node type, label, and version |
| `hda_info` | `hda_node_type: str` | Get HDA definition info: sections, label, version |
| `hda_install` | `hda_path: str` | Install an HDA file into the current session |
| `hda_uninstall` | `hda_node_type: str` | Uninstall an HDA definition |
| `hda_save` | `node_path: str`, `hda_file_path?: str` | Save the HDA definition of an HDA instance node to disk |
| `hda_create` | `node_paths: list`, `hda_name: str`, `hda_label: str`, `hda_file_path: str` | Convert a node into a new HDA |
| `hda_section_get` | `hda_node_type: str`, `section_name: str` | Get the text content of an HDA section. ⚠️ Sections like `PythonCook` contain executable Python |
| `hda_section_set` | `hda_node_type: str`, `section_name: str`, `content: str` | Set an HDA section's content. ⚠️ Writing to `PythonCook`/`OnLoaded`/`OnCreated`/`OnDeleted` injects executable Python |

### Dynamics (DOPs)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `dop_sim_enable` | `dop_net_path: str`, `on: bool` | Enable or disable a DOP simulation network |
| `dop_sim_reset` | `dop_net_path: str` | Reset a DOP simulation to frame 1 |
| `dop_object_list` | `dop_net_path: str` | List all DOP objects in a simulation network |
| `dop_object_info` | `dop_net_path: str`, `object_name: str` | Get the DOP data records attached to a simulation object |
| `dop_data_get` | `dop_net_path: str`, `object_name: str`, `data_name: str` | Get a specific DOP data record |

### Solaris / USD (LOPs)

Requires Houdini with USD support (`pxr` module). All tools return a clear error when USD is unavailable.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `lop_stage_info` | `lop_path: str` | Get USD stage info: root prim paths and up-axis |
| `lop_prim_list` | `lop_path: str`, `prim_path?: str` | List children of a USD prim (default: `/`) |
| `lop_prim_info` | `lop_path: str`, `prim_path: str` | Get USD prim type, attributes, and variant sets |
| `lop_save_usd` | `lop_path: str`, `file_path: str` | Export the USD stage to `.usd` / `.usda` / `.usdc` |
| `lop_variant_set` | `lop_path: str`, `prim_path: str`, `varset: str`, `variant: str` | Set a variant selection on a USD prim |
| `lop_load_masks` | `lop_path: str` | Get stage load mask configuration |

### PDG / TOPs

| Tool | Parameters | Description |
|------|-----------|-------------|
| `pdg_cook` | `top_net_path: str` | Start cooking a PDG/TOP network asynchronously. Use `pdg_status` to poll for completion |
| `pdg_dirty` | `top_net_path: str`, `node_name?: str` | Mark a TOP network or specific node as dirty |
| `pdg_cancel` | `top_net_path: str` | Cancel an active PDG cook |
| `pdg_status` | `top_net_path: str` | Get the current cook state of a TOP network |
| `pdg_output_list` | `top_net_path: str`, `node_name?: str` | List output file paths from PDG work items |

### Takes

| Tool | Parameters | Description |
|------|-----------|-------------|
| `take_list` | — | List all takes as a tree structure |
| `take_create` | `name: str`, `parent_name?: str` | Create a new take (child of `parent_name` or root) |
| `take_set_current` | `name: str` | Set the active take by name |
| `take_parm_include` | `node_path: str`, `parm_name: str` | Include a parameter in the current take |

### VEX / VOPs

| Tool | Parameters | Description |
|------|-----------|-------------|
| `vex_run` | `code: str`, `context?: str` | Execute VEX code via `hou.runVex()`. For reliable VEX execution prefer `vop_snippet_set` + `node_cook` |
| `vex_context_list` | — | List all available VEX contexts (`sop`, `pop`, `cop2`, `chop`, etc.) |
| `vop_network_list` | `search_path?: str` | Find all VOP networks in the scene tree |
| `vop_node_create` | `vop_net_path: str`, `node_type: str`, `name?: str` | Create a VOP node inside a VOP network |
| `vop_node_connect` | `from_path: str`, `from_port: str`, `to_path: str`, `to_port: str` | Connect VOP nodes by named port |
| `vop_code_generate` | `vop_net_path: str` | Retrieve the generated VEX code from a VOP network |
| `vop_snippet_set` | `snippet_node_path: str`, `code: str` | Set VEX snippet code on an Attribute Wrangle, VOP SOP, etc. |

### Utilities

| Tool | Parameters | Description |
|------|-----------|-------------|
| `run_hscript` | `command: str` | Execute an hscript command. Returns `stdout` and `stderr` |
| `eval_expression` | `expr: str` | Evaluate an hscript expression (e.g. `'$HIP'`, `'$F'`, `'strlen("hello")'`) |
| `expand_string` | `template: str` | Expand `$VARIABLES` and `` `hscript expressions` `` in a string |
| `find_file` | `filename: str` | Find a file by name in `$HOUDINI_PATH`. Returns the full path or `null` |
| `path_list` | — | List all directories in `$HOUDINI_PATH` |
| `env_get` | `var_name: str` | Get the value of a Houdini environment variable |
| `env_set` | `var_name: str`, `value: str` | Set a Houdini session environment variable |
| `file_references` | — | List all external file references in the current scene |
| `undo` | — | Undo the last undoable action |
| `redo` | — | Redo the last undone action |
| `update_mode_set` | `mode: str` | Set scene update mode: `'auto'` \| `'manual'` \| `'on_request'` |
| `viewport_screenshot` | `file_path?: str` | Capture the active viewport to a PNG file (default: `/tmp/mcp_screenshot.png`). Requires Houdini UI |
| `node_bundle_list` | — | List all node bundles with their names and node counts |

## Security notes

- The server binds to `127.0.0.1` only and enforces `Host`/`Origin` header validation
  to prevent DNS-rebinding attacks.
- `hda_section_set` can write executable Python into HDA sections — use with care.
- `HOUDINI_MCP_PROJECT_ROOT` restricts hip file paths to a directory sandbox.
- `run_python` (arbitrary Python execution) is intentionally excluded.
