@echo off
title Claude Meet Agent
set "VPY=%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo Claude is not installed yet. Running the installer...
  call "%~dp0Install-Claude.cmd"
)
echo Starting Claude. Keep this window open while Claude is in meetings. Close it or run Stop-Claude to stop.
"%VPY%" -m claude_agent run
pause
