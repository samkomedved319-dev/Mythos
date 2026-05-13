@echo off
REM ============================================================
REM  Mythos: Sovereign Architect — CLI Launcher
REM  Usage: Add this directory to your PATH, then type "mythos"
REM ============================================================

set "MYTHOS_DIR=%~dp0"
python "%MYTHOS_DIR%mythos_cli.py" %*
