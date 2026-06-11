# Contributing

Thanks for your interest in improving houdini-mcp!

## Development setup

You do **not** need Houdini to work on most of this project — the unit test
suite runs against a `hou` mock:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Integration tests run against a real Houdini session and require hython:

```bash
hython -m pytest tests/integration -v
```

## Project layout

- `houdini_side/mcp_server.py` — FastMCP HTTP server, runs as a daemon thread
  inside Houdini.
- `houdini_side/dispatcher.py` — routes `hou.*` calls to Houdini's main thread
  (`dispatch`) and defines the `ok`/`err` response envelope.
- `houdini_side/tools/` — one module per tool category. Each exposes
  `register(app)`; the implementation functions (`_tool_name`) are plain
  callables so they can be unit-tested without MCP.
- `houdini_side/tools/common.py` — shared helpers (`as_text`, `to_jsonable`,
  `resolve_output_path`, ...). Reuse these instead of duplicating logic.

## Guidelines

- Every `hou.*` call must run through `dispatch(work, label="tool_name")`.
- Mutating operations must be wrapped in `hou.undos.group("mcp: ...")`.
- File writes must go through `common.resolve_output_path` so
  `HOUDINI_MCP_PROJECT_ROOT` confinement applies.
- Tools that can execute arbitrary code (hscript, Python expressions, VEX,
  HDA sections) must say so with a `WARNING:` in their docstring — the
  docstring is the tool description an MCP client sees.
- Add unit tests for new tools (see existing `tests/test_*.py` for the
  mock-building style) and run `python -m pytest` before opening a PR.
