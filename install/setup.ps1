#Requires -Version 5.0
<#
.SYNOPSIS
    Production-ready houdini-mcp setup for Windows.

.DESCRIPTION
    Finds hython.exe, installs runtime dependencies into Houdini's Python,
    resolves HOUDINI_USER_PREF_DIR, and writes the Houdini package descriptor
    with the current repository path.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\setup.ps1

.EXAMPLE
    $env:HYTHON = "C:\Program Files\Side Effects Software\Houdini 21.0.000\bin\hython.exe"
    powershell -ExecutionPolicy Bypass -File install\setup.ps1
#>

param(
    [string]$Hython = $env:HYTHON,
    [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-Hython {
    param([string]$Requested)

    if ($Requested) {
        if (Test-Path $Requested) {
            return (Resolve-Path $Requested).Path
        }
        throw "HYTHON path does not exist: $Requested"
    }

    $inPath = Get-Command hython -ErrorAction SilentlyContinue
    if ($inPath) {
        return $inPath.Source
    }

    $searchRoots = @(
        "C:\Program Files\Side Effects Software",
        "C:\Program Files (x86)\Side Effects Software"
    )
    foreach ($root in $searchRoots) {
        if (-not (Test-Path $root)) {
            continue
        }
        $candidate = Get-ChildItem -Path $root -Filter "hython.exe" -Recurse -ErrorAction SilentlyContinue |
            Sort-Object -Property FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    throw @"
hython.exe not found.
  - Add Houdini's bin directory to PATH, or
  - Set `$env:HYTHON to the full path of hython.exe before running this script.
"@
}

function Convert-ToForwardSlashPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $RepoRoot) {
    $RepoRoot = Resolve-Path (Join-Path $scriptDir "..")
}
$RepoRoot = (Resolve-Path $RepoRoot).Path
$repoRootJson = Convert-ToForwardSlashPath $RepoRoot

$hythonPath = Resolve-Hython $Hython
Write-Host "Using hython: $hythonPath"
Write-Host "Repo root: $RepoRoot"

$requirements = Join-Path $RepoRoot "requirements.txt"
if (-not (Test-Path $requirements)) {
    throw "Runtime requirements file not found: $requirements"
}

# No --upgrade: avoid replacing packages bundled with Houdini's Python.
& $hythonPath -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed with exit code $LASTEXITCODE"
}

$prefDirRaw = & $hythonPath -c "import hou; print(hou.getenv('HOUDINI_USER_PREF_DIR') or '')"
$prefDir = (($prefDirRaw | Select-Object -First 1) -as [string]).Trim()
if ($LASTEXITCODE -ne 0 -or -not $prefDir) {
    throw "HOUDINI_USER_PREF_DIR could not be resolved from hython. Start Houdini once for this user, then rerun setup."
}

$packagesDir = Join-Path $prefDir "packages"
New-Item -ItemType Directory -Path $packagesDir -Force | Out-Null

$packageFile = Join-Path $packagesDir "houdini_mcp.json"
$package = [ordered]@{
    name = "houdini-mcp"
    path = "$repoRootJson/houdini_side"
    env = @(
        @{ HOUDINI_MCP_PORT = @{ value = "9876" } }
        @{ HOUDINI_MCP_DISPATCH_TIMEOUT = @{ value = "30" } }
        @{ HOUDINI_MCP_ROOT = @{ value = $repoRootJson } }
        @{ PYTHONPATH = @{ value = $repoRootJson; method = "prepend" } }
    )
}

$package | ConvertTo-Json -Depth 8 | Set-Content -Path $packageFile -Encoding UTF8

Write-Host ""
Write-Host "Installed Houdini package: $packageFile" -ForegroundColor Green
Write-Host "Done. Restart Houdini, then use Shelf -> Houdini MCP -> Start MCP Server."
