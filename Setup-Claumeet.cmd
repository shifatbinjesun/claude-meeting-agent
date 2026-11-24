<# : Claumeet one-file setup and updater. Download this single file and double-click it.
@echo off
title Claumeet setup
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f='%~f0'; iex ((Get-Content -LiteralPath $f -Raw -Encoding UTF8) -replace '(?s)^.*?\n#>', '')"
if errorlevel 1 pause
exit /b
#>
# ---- PowerShell part (runs in this one process; your execution policy is not changed) ----
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Dest = Join-Path $env:USERPROFILE "ClaudeMeetingAgent"
$Zip = Join-Path $env:TEMP "claude-meeting-agent.zip"
$Tmp = Join-Path $env:TEMP ("claude-meeting-agent-" + [guid]::NewGuid())
Write-Host "Downloading Claumeet from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/shifatbinjesun/claude-meeting-agent/archive/refs/heads/main.zip" -OutFile $Zip
Expand-Archive -Path $Zip -DestinationPath $Tmp -Force
$src = Get-ChildItem $Tmp -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Path (Join-Path $src.FullName "*") -Destination $Dest -Recurse -Force
Remove-Item -Recurse -Force $Tmp, $Zip
Write-Host "Files ready in $Dest" -ForegroundColor Green
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dest "scripts\Install-Claumeet.ps1") -Yes -Launch
exit $LASTEXITCODE
