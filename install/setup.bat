@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: houdini-mcp setup for Windows (Command Prompt)
:: Run from the houdini-mcp repo root:
::   install\setup.bat
:: ============================================================

:: --- 1. Find hython ---
where hython >nul 2>&1
if %ERRORLEVEL% == 0 (
    set "HYTHON=hython"
    goto :found
)

:: Try common Houdini installation paths
for /d %%V in (
    "C:\Program Files\Side Effects Software\Houdini*"
) do (
    if exist "%%V\bin\hython.exe" (
        set "HYTHON=%%V\bin\hython.exe"
        goto :found
    )
)

echo Error: hython not found.
echo   - Add Houdini's bin directory to PATH, or
echo   - Edit HYTHON in this script to point to hython.exe
echo   - Default search path: C:\Program Files\Side Effects Software\Houdini*\bin\hython.exe
exit /b 1

:found
echo Using hython: %HYTHON%

:: --- 2. Install MCP SDK ---
"%HYTHON%" -m pip install "mcp>=1.0.0" --upgrade
if %ERRORLEVEL% neq 0 (
    echo Error: pip install failed.
    exit /b 1
)

echo.
echo Done. MCP SDK installed into Houdini Python.
echo.
echo Next steps:
echo   1. Copy install\houdini_mcp_windows.json to %%HOUDINI_USER_PREF_DIR%%\packages\houdini_mcp.json
echo   2. Edit the file and set HOUDINI_MCP_ROOT to the absolute path of this repo
echo   3. Restart Houdini
endlocal
