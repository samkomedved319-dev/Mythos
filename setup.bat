@echo off
title Mythos Setup
cd /d "%~dp0"

echo ========================================
echo   Mythos Sovereign Architect - Setup
echo ========================================
echo.

REM -- 1. Dependencies --
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo   OK
echo.

REM -- 2. Ollama model --
echo [2/3] Building Ollama model 'mythos'...
ollama create mythos -f Modelfile 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama not running or not found.
echo   1. Install Ollama from https://ollama.com
    echo   2. Run: ollama serve
    echo   3. Then run this setup again
    pause
    exit /b 1
)
echo   OK
echo.

REM -- 3. Install mythos command --
echo [3/3] Installing 'mythos' command...
set "BIN_DIR=%USERPROFILE%\.local\bin"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

REM Create mythos.cmd that finds the repo
set "MYTHOS_DIR=%~dp0"
(
echo @echo off
echo set "MYTHOS_DIR=%~dp0"
echo if not exist "%%MYTHOS_DIR%%mythos_cli.py" (
echo     echo [ERROR] mythos_cli.py not found
echo     pause
echo     exit /b 1
echo )
echo python "%%MYTHOS_DIR%%mythos_cli.py" %%*
echo if errorlevel 1 (
echo     echo.
echo     pause
echo )
) > "%BIN_DIR%\mythos.cmd"

echo   Installed to: %BIN_DIR%\mythos.cmd
echo.

REM -- Verify PATH --
echo %PATH% | findstr /C:"%BIN_DIR%" >nul
if %ERRORLEVEL% NEQ 0 (
echo  [NOTE] %BIN_DIR% is NOT in your PATH.
    echo  For this session, run:
    echo    set PATH=%%USERPROFILE%%\.local\bin;%%PATH%%
    echo.
    echo  To add permanently, edit your User PATH environment variable.
) else (
    echo   PATH OK
)
echo.

echo ========================================
echo  Setup complete!
echo ========================================
echo.
echo  Just type:  mythos
echo.
echo  First time? Get your API token at:
echo    https://samkomedved319-dev.github.io/Mythos
echo.
echo  Press any key to start Mythos now...
pause >nul

python "%~dp0mythos_cli.py"
pause
