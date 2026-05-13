@echo off
set NO_COLOR=1
python "%~dp0mythos_cli.py" %*
if errorlevel 1 ( echo. & pause )
