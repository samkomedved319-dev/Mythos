@echo off
title Mythos - Setup
cd /d "%~dp0"

echo ========================================
echo   Mythos Sovereign Architect - Setup
echo ========================================
echo.

REM ── 1. Install Python dependencies ──
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to install dependencies.
    echo     Make sure Python 3.10+ is installed and pip is in PATH.
    pause
    exit /b 1
)
echo   OK
echo.

REM ── 2. Build Ollama model ──
echo [2/4] Building Ollama model 'mythos'...
ollama create mythos -f Modelfile 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Could not build model. Make sure Ollama is running.
    echo     Download from: https://ollama.com
    echo     Then run: ollama create mythos -f Modelfile
    echo.
    echo     Continuing anyway...
) else (
    echo   OK
)
echo.

REM ── 3. Install the 'mythos' command ──
echo [3/4] Installing 'mythos' command...

set "BIN_DIR=%USERPROFILE%\.local\bin"

if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

copy /Y "%~dp0mythos.cmd" "%BIN_DIR%\mythos.cmd" >nul

echo   Installed to: %BIN_DIR%\mythos.cmd
echo.

REM ── 4. Check PATH ──
echo [4/4] Checking PATH...
echo %PATH% | findstr /C:"%BIN_DIR%" >nul
if %ERRORLEVEL% NEQ 0 (
    echo   [!] %BIN_DIR% is NOT in your PATH.
    echo.
    echo   To add it permanently:
    echo     1. Open Start -^> "Edit environment variables"
    echo     2. Add this to your User PATH:
    echo        %BIN_DIR%
    echo.
    echo   For this session, run:
    echo     set PATH=%%USERPROFILE%%\.local\bin;%%PATH%%
) else (
    echo   OK - %BIN_DIR% is in PATH
)
echo.

echo ========================================
echo  Setup complete!
echo ========================================
echo.
echo  Just type:  mythos
echo.
echo  First time? You'll be asked for an API token.
echo  Get one at: https://samkomedved319-dev.github.io/Mythos
echo.
echo  Press any key to start Mythos now...
pause >nul

REM Launch Mythos
python "%~dp0mythos_cli.py"
pause
