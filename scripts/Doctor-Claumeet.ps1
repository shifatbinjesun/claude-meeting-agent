<# Read-only health check. Changes nothing. #>
$AppHome = Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent"
$VPy = Join-Path $AppHome "venv\Scripts\python.exe"
if (-not (Test-Path $VPy)) { Write-Host "Not installed yet. Run Install-Claumeet.cmd first." -ForegroundColor Yellow; Read-Host; exit 1 }
& $VPy -m claude_agent doctor
Write-Host "`nSleep settings (Claumeet cannot join while the PC sleeps):" -ForegroundColor Cyan
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String "Current AC Power Setting Index|Current DC Power Setting Index"
Write-Host "(0x00000000 = never sleeps. Change in Settings > System > Power if you rely on scheduled joins.)"
Write-Host "`nLatest log lines:" -ForegroundColor Cyan
$log = Join-Path $AppHome "logs\agent.log"
if (Test-Path $log) { Get-Content $log -Tail 15 } else { Write-Host "(no log yet)" }
Read-Host "`nPress Enter to close"
