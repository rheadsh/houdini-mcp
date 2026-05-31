#Requires -Version 5.0
<#
.SYNOPSIS
    houdini-mcp setup for Windows (PowerShell)

.DESCRIPTION
    Finds hython.exe, installs the MCP SDK into Houdini's Python environment,
    and prints next steps for package installation.

.EXAMPLE
    # From the houdini-mcp repo root:
    powershell -ExecutionPolicy Bypass -File install\setup.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- 1. Find hython ---
$hython = $null

# Check PATH first
$inPath = Get-Command hython -ErrorAction SilentlyContinue
if ($inPath) {
    $hython = $inPath.Source
}

# Search common Houdini installation directories
if (-not $hython) {
    $searchRoots = @(
        "C:\Program Files\Side Effects Software",
        "C:\Program Files (x86)\Side Effects Software"
    )
    foreach ($root in $searchRoots) {
        if (Test-Path $root) {
            $candidate = Get-ChildItem -Path $root -Filter "hython.exe" -Recurse -ErrorAction SilentlyContinue |
                         Sort-Object -Property FullName -Descending |  # newest version first
                         Select-Object -First 1
            if ($candidate) {
                $hython = $candidate.FullName
                break
            }
        }
    }
}

if (-not $hython) {
    Write-Error @"
hython.exe not found.
  - Add Houdini's bin\ directory to PATH, or
  - Set `$env:HYTHON to the full path of hython.exe before running this script.
  Expected location: C:\Program Files\Side Effects Software\Houdini X.X.XXX\bin\hython.exe
"@
    exit 1
}

Write-Host "Using hython: $hython"

# --- 2. Install MCP SDK ---
& $hython -m pip install "mcp>=1.0.0" --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed (exit code $LASTEXITCODE)."
    exit 1
}

Write-Host ""
Write-Host "Done. MCP SDK installed into Houdini Python." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Copy install\houdini_mcp_windows.json to:"
Write-Host "       $env:HOUDINI_USER_PREF_DIR\packages\houdini_mcp.json"
Write-Host "  2. Edit the file and set HOUDINI_MCP_ROOT to the absolute path of this repo"
Write-Host "  3. Restart Houdini"
