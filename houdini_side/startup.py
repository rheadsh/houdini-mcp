"""
Loaded by Houdini via the houdini456 package hook.
Creates a shelf with Start/Stop MCP Server tools.
"""
import sys
import os

# Ensure project root is on sys.path (belt-and-suspenders alongside houdini_mcp.json pythonpath)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _create_shelf():
    import hou  # type: ignore[import-untyped]

    shelf_name = "houdini_mcp"
    try:
        shelf = hou.shelves.shelf(shelf_name)
    except Exception:
        shelf = None

    if shelf is None:
        shelf = hou.shelves.newShelf(name=shelf_name, label="Houdini MCP")

    start_script = (
        "from houdini_side.mcp_server import start_server\n"
        "start_server()\n"
    )
    stop_script = (
        "from houdini_side.mcp_server import stop_server\n"
        "stop_server()\n"
    )

    for tool_name, label, script in [
        ("houdini_mcp_start", "Start MCP Server", start_script),
        ("houdini_mcp_stop", "Stop MCP Server", stop_script),
    ]:
        try:
            existing = hou.shelves.tool(tool_name)
        except Exception:
            existing = None

        if existing is None:
            hou.shelves.newTool(
                name=tool_name,
                label=label,
                script=script,
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
