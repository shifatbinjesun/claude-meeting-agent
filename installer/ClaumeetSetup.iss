; Claumeet - Windows installer (Inno Setup 6). Per-user, no admin rights.
#define AppName "Claumeet"
#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{6E1C2B57-3C1E-4C3B-9F3A-2E7A9C1D0B11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=claude-meeting-agent contributors (open source)
AppPublisherURL=https://github.com/shifatbinjesun/claude-meeting-agent
DefaultDirName={localappdata}\Programs\ClaudeMeetingAgent
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ClaumeetSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=BEFORE.txt
InfoAfterFile=AFTER.txt
LicenseFile=..\LICENSE
UninstallDisplayName={#AppName}
CloseApplications=no

[Files]
Source: "..\src\*"; DestDir: "{app}\src"; Excludes: "__pycache__\*,*.pyc,*.egg-info\*"; Flags: recursesubdirs ignoreversion
Source: "..\config\*"; DestDir: "{app}\config"; Flags: recursesubdirs ignoreversion
Source: "..\prompts\*"; DestDir: "{app}\prompts"; Flags: recursesubdirs ignoreversion
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs ignoreversion
Source: "..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements-windows.lock"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Start-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Stop-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Doctor-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SignIn-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Claumeet Control Center"; Filename: "{app}\Start-Claumeet.cmd"; WorkingDir: "{app}"
Name: "{autoprograms}\Stop Claumeet"; Filename: "{app}\Stop-Claumeet.cmd"; WorkingDir: "{app}"
Name: "{autodesktop}\Claumeet Control Center"; Filename: "{app}\Start-Claumeet.cmd"; WorkingDir: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\Install-Claumeet.ps1"" -Yes -NoShortcut"; StatusMsg: "Setting up Python and Claumeet (this can take a few minutes)..."; Flags: waituntilterminated
Filename: "{app}\Start-Claumeet.cmd"; Description: "Open the Claumeet Control Center now"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\Uninstall-Claumeet.ps1"" -Quiet"; RunOnceId: "RemoveVenv"; Flags: runhidden waituntilterminated
