"""
Loaded by Houdini via the houdini456 package hook.
Ensures the project root is on sys.path. The shelf is defined in toolbar/houdini_mcp.shelf.
"""
import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

print("[houdini-mcp] Loaded. Use Shelf -> Houdini MCP -> Start MCP Server.")
