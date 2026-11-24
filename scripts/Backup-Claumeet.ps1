<#
  Encrypted backup of Claumeet's memory database and settings using Windows DPAPI (CurrentUser):
  only your Windows account on this PC can decrypt it. The Google browser profile and the API key
  are NOT included (sign in / paste the key again after a restore).
  Usage:  Backup-Claumeet.ps1            -> creates Backups\claude-<date>.cmabak
          Backup-Claumeet.ps1 -Restore <file>
#>
param([string]$Restore)
Add-Type -AssemblyName System.Security
Add-Type -AssemblyName System.IO.Compression.FileSystem
$AppHome = Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent"
$Out = Join-Path $AppHome "Backups"; New-Item -ItemType Directory -Force -Path $Out | Out-Null
$pidFile = Join-Path $AppHome "agent.pid"
if (Test-Path $pidFile) { Write-Host "Stop Claumeet first (Stop-Claumeet.cmd)." -ForegroundColor Yellow; exit 1 }
if ($Restore) {
  $bytes = [IO.File]::ReadAllBytes($Restore)
  $plain = [Security.Cryptography.ProtectedData]::Unprotect($bytes, $null, "CurrentUser")
  $zip = Join-Path $env:TEMP "claude-restore.zip"; [IO.File]::WriteAllBytes($zip, $plain)
  Expand-Archive -Path $zip -DestinationPath $AppHome -Force; Remove-Item $zip
  Write-Host "Restored into $AppHome" -ForegroundColor Green; exit 0
}
$stage = Join-Path $env:TEMP ("claude-bk-" + [guid]::NewGuid()); New-Item -ItemType Directory $stage | Out-Null
foreach ($f in "brain.sqlite3", "config.yaml", "owner.json") { $p = Join-Path $AppHome $f; if (Test-Path $p) { Copy-Item $p $stage } }
$zip = "$stage.zip"; [IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip)
$enc = [Security.Cryptography.ProtectedData]::Protect([IO.File]::ReadAllBytes($zip), $null, "CurrentUser")
$dest = Join-Path $Out ("claude-" + (Get-Date -Format "yyyyMMdd-HHmm") + ".cmabak"); [IO.File]::WriteAllBytes($dest, $enc)
Remove-Item -Recurse -Force $stage, $zip
Write-Host "Encrypted backup written: $dest" -ForegroundColor Green
