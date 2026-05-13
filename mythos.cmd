@echo off
python "%~dp0mythos_cli.py" %*
if errorlevel 1 ( echo. & pause )
