@echo off
REM ============================================================
REM  Mythos: Sovereign Architect - CLI Launcher
REM  Place this file's directory in your PATH, then type: mythos
REM ============================================================

REM Find this script's own directory
set "MYTHOS_DIR=%~dp0"

REM Strip trailing backslash if present
if "%MYTHOS_DIR:~-1%"=="\" set "MYTHOS_DIR=%MYTHOS_DIR:~0,-1%"

REM Check if python exists
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check if the script exists
if not exist "%MYTHOS_DIR%\mythos_cli.py" (
    echo [ERROR] mythos_cli.py not found in %MYTHOS_DIR%
    pause
    exit /b 1
)

REM Run Mythos
python "%MYTHOS_DIR%\mythos_cli.py" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    pause
)
