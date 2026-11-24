@echo off
rem One-click installer. -ExecutionPolicy Bypass applies to this single PowerShell process only.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Claumeet.ps1" -Yes -Launch
if errorlevel 1 pause
