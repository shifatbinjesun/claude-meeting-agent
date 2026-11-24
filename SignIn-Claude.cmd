@echo off
rem Opens Claude's dedicated Chrome profile (normal, not automated) so you can sign in the AI-labeled Google account.
"%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe" -m claude_agent signin
pause
