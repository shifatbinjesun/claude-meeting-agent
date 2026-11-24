<#
  Claumeet - Windows installer (per-user, no admin, reversible).
  Run by double-clicking Install-Claumeet.cmd (uses -ExecutionPolicy Bypass for this one process only;
  your machine's execution policy is NOT changed).

  What it does:
    1. Checks Windows, Python 3.12 and Google Chrome (offers official winget installs if missing; asks first).
    2. Creates a private virtual environment in %LOCALAPPDATA%\ClaudeMeetAgent\venv.
    3. Installs pinned, hash-verified dependencies from requirements-windows.lock.
    4. Optionally creates Desktop/Start Menu shortcuts.
  It never installs drivers, changes audio defaults, disables security features or joins meetings.
#>
param([switch]$Yes, [switch]$Launch, [switch]$NoShortcut)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$AppHome = Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent"
$Venv = Join-Path $AppHome "venv"

function Say($m, $c = "Gray") { Write-Host $m -ForegroundColor $c }
function Ask($q) { if ($Yes) { return $true }; $a = Read-Host "$q [y/N]"; return $a -match '^(y|yes)$' }
function Fail($m) { Say "`n!! $m" Red; Say "Send a screenshot of this window to get help."; if (-not $env:CI) { Read-Host "Press Enter to close" }; exit 1 }
# Log everything so problems can be diagnosed without screenshots.
New-Item -ItemType Directory -Force -Path (Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent\logs") | Out-Null
try { Start-Transcript -Path (Join-Path $env:LOCALAPPDATA "ClaudeMeetAgent\logs\install.log") -Force | Out-Null } catch {}

Say "`n=== Claumeet installer ===" Cyan
Say "Repository: $Repo"
Say "Data folder: $AppHome"
New-Item -ItemType Directory -Force -Path $AppHome | Out-Null

# --- Windows / hardware summary (read-only) ---
$os = Get-CimInstance Win32_OperatingSystem
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ramGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Say "Windows: $($os.Caption) build $($os.BuildNumber)"
Say "CPU: $cpu"
Say "RAM: $ramGB GB"
if ($ramGB -lt 7.5) { Say "Warning: less than 8 GB RAM. Close heavy apps during meetings." Yellow }

# --- Python ---
function Find-Python {
  foreach ($cand in @("py -3.12", "python")) {
    try {
      $parts = $cand.Split(" ")
      $v = & $parts[0] $parts[1..9] -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v -eq '3.12') { return $cand }   # lockfile is compiled for 3.12
    } catch {}
  }
  return $null
}
$py = Find-Python
if (-not $py) {
  Say "Python 3.12 was not found (the pinned lockfile targets 3.12; other versions are ignored)." Yellow
  if (Ask "Install Python 3.12 for your user only with winget (official Microsoft package manager)?") {
    winget install --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
    $py = Find-Python
  }
  if (-not $py) { Fail "Install Python 3.12 from https://www.python.org/downloads/windows/ then run this installer again." }
}
Say "Python: $py" Green

# --- Chrome ---
$chromePaths = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
                 "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
                 "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
$chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) {
  Say "Google Chrome was not found." Yellow
  if (Ask "Install Google Chrome with winget? (may ask for administrator approval)") {
    winget install --id Google.Chrome --accept-package-agreements --accept-source-agreements
    $chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
  }
  if (-not $chrome) { Say "Continuing without Chrome; Playwright's bundled Chromium will be downloaded instead." Yellow }
}
if ($chrome) { Say "Chrome: $chrome" Green }

# --- venv + dependencies ---
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
  Say "Creating virtual environment..."
  $parts = $py.Split(" ")
  & $parts[0] $parts[1..9] -m venv $Venv
  if ($LASTEXITCODE -ne 0) { Fail "Could not create the virtual environment." }
}
$VPy = Join-Path $Venv "Scripts\python.exe"
Say "Installing pinned dependencies (hash-checked)..."
& $VPy -m pip install --upgrade --quiet pip
& $VPy -m pip install --quiet --require-hashes -r (Join-Path $Repo "requirements-windows.lock")
if ($LASTEXITCODE -ne 0) { Fail "Dependency install failed. Check your internet connection and run again." }
& $VPy -m pip install --quiet --no-deps -e $Repo
if ($LASTEXITCODE -ne 0) { Fail "Installing Claumeet failed." }
if (-not $chrome) {
  Say "Downloading Playwright Chromium (official Playwright CDN)..."
  & $VPy -m playwright install chromium
}
Set-Content -Path (Join-Path $AppHome "repo.txt") -Value $Repo -Encoding ASCII

# --- shortcuts ---
$legacy = Join-Path ([Environment]::GetFolderPath("Desktop")) "Claude Control Center.lnk"   # pre-rename shortcut
if (Test-Path $legacy) { Remove-Item $legacy -Force }
if (-not $NoShortcut -and (Ask "Create a Desktop shortcut 'Claumeet Control Center'?")) {
  $ws = New-Object -ComObject WScript.Shell
  $lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Claumeet Control Center.lnk"))
  $lnk.TargetPath = Join-Path $Repo "Start-Claumeet.cmd"
  $lnk.WorkingDirectory = $Repo
  $lnk.Description = "Start Claumeet and open the Control Center"
  $lnk.Save()
  Say "Shortcut created." Green
}

Say "`nRunning health check..." Cyan
& $VPy -m claude_agent doctor
if ($Launch) {
  Say "`nInstalled! Starting Claumeet... the Control Center opens in your browser and walks you through setup." Green
  Start-Process -FilePath (Join-Path $Repo "Start-Claumeet.cmd") -WorkingDirectory $Repo
  Start-Sleep -Seconds 3
  exit 0
}
Say "`nInstalled. Next steps:" Green
Say "  1. Double-click Start-Claumeet.cmd (or the Desktop shortcut)."
Say "  2. The Control Center opens and its setup wizard guides you: sign in Claumeet's Google account, paste your free Gemini key, test."
if (-not $Yes) { Read-Host "Press Enter to close" }
