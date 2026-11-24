@echo off
title Claumeet
set "VPY=%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo Claumeet is not installed yet. Running the installer...
  call "%~dp0Install-Claumeet.cmd"
)
echo Starting Claumeet. Keep this window open while Claumeet is in meetings. Close it or run Stop-Claumeet to stop.
"%VPY%" -m claude_agent run
pause
