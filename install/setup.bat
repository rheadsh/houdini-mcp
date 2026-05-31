@echo off
setlocal

REM Production installer wrapper for Windows Command Prompt.
REM PowerShell owns the implementation so JSON/path handling stays reliable.

set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup.ps1"
if %ERRORLEVEL% neq 0 (
    exit /b %ERRORLEVEL%
)

endlocal
