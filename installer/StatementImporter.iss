; Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
#define MyAppName "Statement Importer"
#define MyAppVersion "1.6.0"
#define MyAppPublisher "Harsh"
#define MyAppExeName "StatementImporter.exe"

[Setup]
AppId={{6FE6C40A-01DA-44F2-9B87-502758B45746}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (c) 2026 Harsh. Made in India.
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Offline-first bank statement reconciliation for PostgreSQL. Created by Harsh. Made in India.
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\StatementImporter
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\dist
OutputBaseFilename=StatementImporter-1.6.0-Setup-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=no
RestartApplications=no
#ifdef TEST_BUILD
Uninstallable=no
CreateUninstallRegKey=no
#else
Uninstallable=yes
#endif
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=no
ChangesEnvironment=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "postgres"; Description: "Download and run PostgreSQL 17 installer with winget"; GroupDescription: "Missing prerequisites (internet required):"; Check: ShouldOfferPostgreSQL
Name: "webview"; Description: "Download Microsoft Edge WebView2 Runtime with winget"; GroupDescription: "Missing prerequisites (internet required):"; Check: ShouldOfferWebView2

[Files]
Source: "close-installed-app.ps1"; Flags: dontcopy
Source: "..\dist\StatementImporter.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\QUICK_START.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\IMPLEMENTATION_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements-lock.txt"; DestDir: "{app}"; DestName: "DEPENDENCY_MANIFEST.txt"; Flags: ignoreversion

[Icons]
#ifndef TEST_BUILD
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Quick Start"; Filename: "{app}\QUICK_START.txt"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
#endif

[Run]
Filename: "{code:GetWingetPath}"; Parameters: "install --exact --id PostgreSQL.PostgreSQL.17 --source winget --accept-package-agreements --accept-source-agreements"; Description: "Install PostgreSQL 17"; StatusMsg: "Installing database tools. Follow the PostgreSQL installer in the other window; download progress appears there."; Tasks: postgres; Flags: waituntilterminated; Check: WingetAvailable
Filename: "{code:GetWingetPath}"; Parameters: "install --exact --id Microsoft.EdgeWebView2Runtime --source winget --accept-package-agreements --accept-source-agreements"; Description: "Install Microsoft Edge WebView2 Runtime"; StatusMsg: "Installing the display runtime. Download and installation progress appear in the other window."; Tasks: webview; Flags: waituntilterminated; Check: WingetAvailable
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intentionally empty: PostgreSQL, imported data, backups, and per-user settings are preserved.

[Code]
var
  PrerequisitePage: TOutputMsgMemoWizardPage;
  UpgradeProgress: TOutputProgressWizardPage;
  CloseAttempt: Integer;

function CloseInstalledApp(Force: Boolean): String;
var
  ResultCode, Tick: Integer;
  ResultPath, Arguments, Status: String;
  StatusText: AnsiString;
begin
  Result := 'error';
  CloseAttempt := CloseAttempt + 1;
  ResultPath := ExpandConstant('{tmp}\close-result-') + IntToStr(CloseAttempt) + '.txt';
  if not FileExists(ExpandConstant('{tmp}\close-installed-app.ps1')) then
    ExtractTemporaryFile('close-installed-app.ps1');
  Arguments := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{tmp}\close-installed-app.ps1') + '" -Executable "' +
    ExpandConstant('{app}\StatementImporter.exe') + '" -ResultPath "' + ResultPath + '"';
  if Force then Arguments := Arguments + ' -Force';
  UpgradeProgress.Show;
  try
    if Force then Status := 'Closing the previous version with your permission'
    else Status := 'Asking the previous version to close';
    UpgradeProgress.SetText(Status, 'Checking that the application file is released...');
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      Arguments, '', SW_HIDE, ewNoWait, ResultCode) then exit;
    for Tick := 0 to 199 do
    begin
      UpgradeProgress.SetText(Status, 'Elapsed: ' + IntToStr(Tick div 10) +
        ' seconds. This check stops after 20 seconds.');
      UpgradeProgress.SetProgress(Tick, 200);
      if LoadStringFromFile(ResultPath, StatusText) and (Length(StatusText) > 0) then
      begin
        Result := String(StatusText);
        Log('Upgrade file-release check: ' + Result);
        exit;
      end;
      Sleep(100);
    end;
    Result := 'timeout';
    Log('Upgrade helper timed out; file replacement was blocked.');
  finally
    UpgradeProgress.Hide;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Status: String;
begin
  Result := '';
  if not FileExists(ExpandConstant('{app}\StatementImporter.exe')) then exit;
  Status := CloseInstalledApp(False);
  if Status = 'ready' then exit;
  if (Status = 'busy') and (not WizardSilent) then
    if MsgBox('The previous version is still running in the background.' + #13#10 + #13#10 +
      'Finish any import or backup first. May Setup close this installed copy now?' + #13#10 +
      'An unfinished operation may be interrupted.', mbConfirmation, MB_YESNO) = IDYES then
      Status := CloseInstalledApp(True);
  if Status <> 'ready' then
    Result := 'The previous application has not released its files. No files were replaced.' + #13#10 +
      'Finish any ongoing work and click Try again. If the old application has no window, ' +
      'restart Windows and run Setup again. You can cancel safely.';
end;

function HasPostgreSQL: Boolean;
begin
  Result :=
    RegKeyExists(HKLM64, 'SOFTWARE\PostgreSQL\Installations') or
    RegKeyExists(HKLM32, 'SOFTWARE\PostgreSQL\Installations') or
    DirExists(ExpandConstant('{pf}\PostgreSQL')) or
    DirExists(ExpandConstant('{pf64}\PostgreSQL'));
end;

function HasWebView2: Boolean;
begin
  Result :=
    DirExists(ExpandConstant('{pf32}\Microsoft\EdgeWebView\Application')) or
    DirExists(ExpandConstant('{localappdata}\Microsoft\EdgeWebView\Application'));
end;

function GetWingetPath(Param: String): String;
begin
  Result := ExpandConstant('{localappdata}\Microsoft\WindowsApps\winget.exe');
end;

function WingetAvailable: Boolean;
begin
  Result := FileExists(GetWingetPath(''));
end;

function ShouldOfferPostgreSQL: Boolean;
begin
  Result := (not HasPostgreSQL) and WingetAvailable;
end;

function ShouldOfferWebView2: Boolean;
begin
  Result := (not HasWebView2) and WingetAvailable;
end;

procedure InitializeWizard;
var
  Report: String;
begin
  UpgradeProgress := CreateOutputProgressPage('Preparing your update',
    'Closing the previous version and checking its files');
  Report := 'SYSTEM CHECK' + #13#10 + #13#10;
  if HasPostgreSQL then
    Report := Report + '[READY] PostgreSQL detected' + #13#10
  else
    Report := Report + '[ACTION] PostgreSQL was not detected' + #13#10;
  if HasWebView2 then
    Report := Report + '[READY] Microsoft Edge WebView2 detected' + #13#10
  else
    Report := Report + '[ACTION] Microsoft Edge WebView2 was not detected' + #13#10;
  if WingetAvailable then
    Report := Report + '[READY] winget is available for optional downloads' + #13#10
  else
    Report := Report + '[OFFLINE] winget is unavailable; install missing prerequisites manually' + #13#10;
  Report := Report + #13#10 +
    'The application and statement processing need no internet connection once prerequisites are present.' + #13#10 +
    'Uninstalling the application preserves PostgreSQL, imported data, backups, and settings.';
  PrerequisitePage := CreateOutputMsgMemoPage(
    wpWelcome, 'Prerequisite check', 'Local, offline-first installation',
    'Review this computer before installing.', Report);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = PrerequisitePage.ID) and ((not HasPostgreSQL) or (not HasWebView2)) then
    Result := MsgBox(
      'One or more prerequisites are missing. You can select optional downloads on the next page, install them manually, or continue and configure them later.' + #13#10 + #13#10 +
      'Continue setup?', mbConfirmation, MB_YESNO) = IDYES;
end;
