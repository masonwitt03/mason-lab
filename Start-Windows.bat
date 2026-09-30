@echo off
REM Double-click this file to start Mason Lab on Windows.
cd /d "%~dp0"
echo Installing / updating what Mason Lab needs (first time takes a minute)...
python -m pip install --quiet -r requirements.txt
if not exist config.yaml python -m mason_lab setup
echo.
echo Mason Lab is running. Leave this window open. Close it to stop.
python -m mason_lab run
pause
