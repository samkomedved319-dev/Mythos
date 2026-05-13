@echo off
REM ============================================================
REM  Mythos: Sovereign Architect - CLI Launcher
REM  Place this file's directory in your PATH, then type: mythos
REM ============================================================
set "MYTHOS_DIR=%~dp0"
if not exist "%MYTHOS_DIR%mythos_cli.py" (
    echo [ERROR] mythos_cli.py not found in %MYTHOS_DIR%
    pause
    exit /b 1
)
python "%MYTHOS_DIR%mythos_cli.py" %*
if errorlevel 1 (
    echo.
    pause
)
