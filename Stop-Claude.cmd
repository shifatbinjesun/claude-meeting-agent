@echo off
"%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe" -m claude_agent stop
timeout /t 3 >nul
