param([switch]$Quiet)
<# Removes the virtual environment and shortcuts. Asks before deleting memory, browser profile and the API key. #>
$AppHome = Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent"
$VPy = Join-Path $AppHome "venv\Scripts\python.exe"
if (Test-Path (Join-Path $AppHome "agent.pid")) { & $VPy -m claude_agent stop }
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Claumeet Control Center.lnk"
if (Test-Path $lnk) { Remove-Item $lnk }
if (Test-Path (Join-Path $AppHome "venv")) { Remove-Item -Recurse -Force (Join-Path $AppHome "venv"); Write-Host "Removed virtual environment." }
if ($Quiet) { Write-Host "Removed the Python environment. Your memory/settings stay in $AppHome (delete that folder to erase them)."; exit 0 }
$a = Read-Host "Also delete the Gemini API key from Windows Credential Manager? [y/N]"
if ($a -match '^(y|yes)$') { cmdkey /delete:"gemini_api_key@ClaudeMeetAgent" 2>$null | Out-Null; Write-Host "If a key remains, remove 'ClaudeMeetAgent' in Credential Manager > Windows Credentials." }
$a = Read-Host "Delete ALL Claumeet data (memory, settings, logs, Claumeet's Google sign-in profile)? This cannot be undone. [y/N]"
if ($a -match '^(y|yes)$') { Remove-Item -Recurse -Force $AppHome; Write-Host "All local data deleted. (Copies already processed by Google are governed by Google's terms.)" }
Write-Host "Uninstall finished. You can delete the repository folder yourself." -ForegroundColor Green
Read-Host "Press Enter to close"
