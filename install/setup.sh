#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

find_hython() {
    if [ "${HYTHON:-}" ]; then
        printf '%s\n' "$HYTHON"
        return
    fi
    if command -v hython >/dev/null 2>&1; then
        command -v hython
        return
    fi
    for candidate in \
        "/Applications/Houdini/Current/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython" \
        "/opt/hfs*/bin/hython"; do
        for path in $candidate; do
            if [ -x "$path" ]; then
                printf '%s\n' "$path"
                return
            fi
        done
    done
}

HYTHON_BIN="$(find_hython || true)"
if [ -z "$HYTHON_BIN" ] || [ ! -x "$HYTHON_BIN" ]; then
    cat >&2 <<'EOF'
Error: hython not found.
  - Add Houdini's bin directory to PATH, or
  - Run "source /path/to/hfs/houdini_setup" on Linux, or
  - Set HYTHON=/absolute/path/to/hython before running this script.
EOF
    exit 1
fi

echo "Using hython: $HYTHON_BIN"
echo "Repo root: $REPO_ROOT"

# No --upgrade: avoid replacing packages bundled with Houdini's Python.
"$HYTHON_BIN" -m pip install -r "$REPO_ROOT/requirements.txt"

PREF_DIR="$("$HYTHON_BIN" -c 'import hou; print(hou.getenv("HOUDINI_USER_PREF_DIR") or "")')"
if [ -z "$PREF_DIR" ]; then
    cat >&2 <<'EOF'
Error: HOUDINI_USER_PREF_DIR could not be resolved from hython.
Start Houdini once for this user, or set HOUDINI_USER_PREF_DIR before running setup.
EOF
    exit 1
fi

PACKAGES_DIR="$PREF_DIR/packages"
PACKAGE_FILE="$PACKAGES_DIR/houdini_mcp.json"
mkdir -p "$PACKAGES_DIR"

cat > "$PACKAGE_FILE" <<EOF
{
    "name": "houdini-mcp",
    "path": "$REPO_ROOT/houdini_side",
    "env": [
        { "HOUDINI_MCP_PORT": { "value": "9876" } },
        { "HOUDINI_MCP_DISPATCH_TIMEOUT": { "value": "30" } },
        { "HOUDINI_MCP_ROOT": { "value": "$REPO_ROOT" } },
        { "PYTHONPATH": { "value": "$REPO_ROOT", "method": "prepend" } }
    ]
}
EOF

echo "Installed Houdini package: $PACKAGE_FILE"
echo "Done. Restart Houdini, then use Shelf -> Houdini MCP -> Start MCP Server."
