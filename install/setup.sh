#!/usr/bin/env bash
set -e
# Find hython
HYTHON=$(which hython 2>/dev/null || echo "/Applications/Houdini/Current/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython")
if [ ! -f "$HYTHON" ]; then
    echo "Error: hython not found. Set PATH or edit HYTHON in this script."
    exit 1
fi
echo "Using hython: $HYTHON"
$HYTHON -m pip install "mcp>=1.0.0" --upgrade
echo "Done. MCP SDK installed into Houdini Python."
