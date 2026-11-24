; Claumeet - Windows installer (Inno Setup 6). Per-user, no admin rights.
#define AppName "Claumeet"
#ifndef AppVersion
  #define AppVersion "0.3.2"
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
SetupIconFile=..\assets\claumeet.ico
WizardImageFile=art\wizard-large.bmp
WizardSmallImageFile=art\wizard-small.bmp
UninstallDisplayIcon={app}\claumeet.ico
VersionInfoDescription=Claumeet setup
VersionInfoProductName=Claumeet
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
Source: "..\assets\claumeet.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Start-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Stop-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Doctor-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SignIn-Claumeet.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Claumeet Control Center"; Filename: "{app}\Start-Claumeet.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\claumeet.ico"
Name: "{autoprograms}\Stop Claumeet"; Filename: "{app}\Stop-Claumeet.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\claumeet.ico"
Name: "{autodesktop}\Claumeet Control Center"; Filename: "{app}\Start-Claumeet.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\claumeet.ico"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\Install-Claumeet.ps1"" -Yes -NoShortcut"; StatusMsg: "Setting up Python and Claumeet (this can take a few minutes)..."; Flags: waituntilterminated
Filename: "{app}\Start-Claumeet.cmd"; Description: "Open the Claumeet Control Center now"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\Uninstall-Claumeet.ps1"" -Quiet"; RunOnceId: "RemoveVenv"; Flags: runhidden waituntilterminated

[Code]
{ Two short pages shown right after the files and Python packages are installed:
  1. Claumeet's own Google account (create one / sign it in through Google's normal page).
  2. A free Gemini API key, checked with one free request and stored only in Windows Credential Manager.
  Both can be skipped and finished later from the Control Center. The installer never sees a Google password. }
var
  GooglePage: TWizardPage;
  GoogleDone: TNewCheckBox;
  KeyPage: TInputQueryWizardPage;
  KeyStatus: TNewStaticText;

function SetEnvironmentVariable(lpName: string; lpValue: string): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function VenvPython: string;
begin
  Result := ExpandConstant('{localappdata}\ClaudeMeetAgent\venv\Scripts\python.exe');
end;

procedure OpenUrl(Url: string);
var
  Code: Integer;
begin
  ShellExec('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, Code);
end;

procedure SignupClick(Sender: TObject);
begin
  OpenUrl('https://accounts.google.com/signup');
end;

procedure AiStudioClick(Sender: TObject);
begin
  OpenUrl('https://aistudio.google.com/apikey');
end;

procedure SigninClick(Sender: TObject);
var
  Code: Integer;
begin
  if not FileExists(VenvPython) then begin
    MsgBox('Claumeet''s Python environment was not created, so this step can''t run yet. Finish the installer, then run Install-Claumeet.cmd again (see the log in %LOCALAPPDATA%\ClaudeMeetAgent\logs\install.log).', mbError, MB_OK);
    exit;
  end;
  if Exec(VenvPython, '-m claude_agent signin', '', SW_HIDE, ewNoWait, Code) then
    GoogleDone.Enabled := True;
end;

function AddText(Page: TWizardPage; Top: Integer; Height: Integer; Caption: string): TNewStaticText;
begin
  Result := TNewStaticText.Create(Page);
  Result.Parent := Page.Surface;
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Left := 0;
  Result.Top := Top;
  Result.Width := Page.SurfaceWidth;
  Result.Height := Height;
  Result.Caption := Caption;
end;

function AddButton(Page: TWizardPage; Top: Integer; Caption: string; Handler: TNotifyEvent): TNewButton;
begin
  Result := TNewButton.Create(Page);
  Result.Parent := Page.Surface;
  Result.Left := 0;
  Result.Top := Top;
  Result.Width := ScaleX(300);
  Result.Height := ScaleY(28);
  Result.Caption := Caption;
  Result.OnClick := Handler;
end;

procedure InitializeWizard;
var
  B: TNewButton;
begin
  GooglePage := CreateCustomPage(wpInfoAfter, 'Step 1 of 2: Claumeet''s Google account',
    'Claumeet joins meetings with its own Google account, never yours.');
  AddText(GooglePage, 0, ScaleY(62),
    'Use a separate, free Google account and give it a clear AI name such as "Claumeet (AI)", so everyone in the meeting can see it is an AI.' + #13#10 +
    'Already have one? Skip straight to "Sign it in".');
  AddButton(GooglePage, ScaleY(68), '1. Create a new Google account (opens Google)', @SignupClick);
  AddButton(GooglePage, ScaleY(102), '2. Sign it in to Claumeet''s Chrome window', @SigninClick);
  AddText(GooglePage, ScaleY(138), ScaleY(44),
    'Sign in on Google''s own page in the window that opens, then close that window. Claumeet never sees your password.');
  GoogleDone := TNewCheckBox.Create(GooglePage);
  GoogleDone.Parent := GooglePage.Surface;
  GoogleDone.Top := ScaleY(186);
  GoogleDone.Width := GooglePage.SurfaceWidth;
  GoogleDone.Height := ScaleY(20);
  GoogleDone.Caption := 'I have signed Claumeet''s Google account in';
  AddText(GooglePage, ScaleY(214), ScaleY(30), 'You can skip this and do it later from the Control Center''s setup checklist.');

  KeyPage := CreateInputQueryPage(GooglePage.ID, 'Step 2 of 2: Free Gemini API key',
    'Claumeet''s voice and brain run on Google Gemini''s free tier.',
    'How to get a free key (about 1 minute):' + #13#10 +
    '  1. Click "Open Google AI Studio" below and sign in with any Google account.' + #13#10 +
    '  2. Click "Create API key". Do NOT turn on billing: Claumeet only uses free models.' + #13#10 +
    '  3. Copy the key and paste it here. It is checked, then stored only in Windows Credential Manager.');
  KeyPage.Add('Gemini API key (leave empty to add it later):', True);
  B := AddButton(KeyPage, KeyPage.Edits[0].Top + KeyPage.Edits[0].Height + ScaleY(10), 'Open Google AI Studio (free key page)', @AiStudioClick);
  KeyStatus := AddText(KeyPage, B.Top + B.Height + ScaleY(10), ScaleY(48), '');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Code: Integer;
  Key: string;
begin
  Result := True;
  if (GooglePage <> nil) and (CurPageID = GooglePage.ID) then begin
    if GoogleDone.Checked and FileExists(VenvPython) then
      Exec(VenvPython, '-m claude_agent setup-mark google_signed_in', '', SW_HIDE, ewWaitUntilTerminated, Code);
  end else if (KeyPage <> nil) and (CurPageID = KeyPage.ID) then begin
    Key := Trim(KeyPage.Values[0]);
    if Key = '' then exit;
    if not FileExists(VenvPython) then begin
      MsgBox('Claumeet''s Python environment is missing, so the key can''t be saved yet. Add it later from the Control Center.', mbError, MB_OK);
      exit;
    end;
    KeyStatus.Caption := 'Checking the key with one free request...';
    WizardForm.Repaint;
    { Passed through this process's environment, never on a command line or on disk. }
    SetEnvironmentVariable('CLAUMEET_INSTALL_KEY', Key);
    if not Exec(VenvPython, '-m claude_agent set-key --from-env CLAUMEET_INSTALL_KEY', '', SW_HIDE, ewWaitUntilTerminated, Code) then
      Code := -1;
    SetEnvironmentVariable('CLAUMEET_INSTALL_KEY', '');
    if Code = 0 then begin
      KeyPage.Values[0] := '';
      KeyStatus.Caption := 'Key checked and saved. ';
    end else begin
      KeyStatus.Caption := 'That key didn''t work. Make sure you copied the whole key and that you are online, or leave the box empty and add it later.';
      Result := False;
    end;
  end;
end;
