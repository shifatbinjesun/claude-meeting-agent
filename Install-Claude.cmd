@echo off
rem One-click installer. -ExecutionPolicy Bypass applies to this single PowerShell process only.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Claude.ps1"
