; Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
#define MyAppName "Statement Importer"
#define MyAppVersion "1.3.4"
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
OutputBaseFilename=StatementImporter-1.3.4-Setup-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=no
RestartApplications=no
Uninstallable=yes
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
Source: "..\dist\StatementImporter.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\QUICK_START.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\IMPLEMENTATION_REPORT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements-lock.txt"; DestDir: "{app}"; DestName: "DEPENDENCY_MANIFEST.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Quick Start"; Filename: "{app}\QUICK_START.txt"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{code:GetWingetPath}"; Parameters: "install --exact --id PostgreSQL.PostgreSQL.17 --source winget --silent --accept-package-agreements --accept-source-agreements"; Description: "Install PostgreSQL 17"; Tasks: postgres; Flags: waituntilterminated; Check: WingetAvailable
Filename: "{code:GetWingetPath}"; Parameters: "install --exact --id Microsoft.EdgeWebView2Runtime --source winget --silent --accept-package-agreements --accept-source-agreements"; Description: "Install Microsoft Edge WebView2 Runtime"; Tasks: webview; Flags: waituntilterminated; Check: WingetAvailable
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intentionally empty: PostgreSQL, imported data, backups, and per-user settings are preserved.

[Code]
var
  PrerequisitePage: TOutputMsgMemoWizardPage;

function StopRunningStatementImporter: Boolean;
var
  ResultCode: Integer;
  ExistingApp, TaskkillPath: String;
begin
  Result := True;
  ExistingApp := ExpandConstant('{app}\StatementImporter.exe');
  if FileExists(ExistingApp) then
  begin
    { Newer versions exit cleanly after receiving this request. }
    Exec(ExistingApp, '--shutdown', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(3000);

    { Older versions do not understand --shutdown. Target the existing per-user
      installation directly and avoid the generic Restart Manager flow. }
    TaskkillPath := ExpandConstant('{sys}\taskkill.exe');
    if FileExists(TaskkillPath) then
      Exec(TaskkillPath, '/IM StatementImporter.exe /T /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not StopRunningStatementImporter then
    Result := 'Statement Importer is still running. Close it from Task Manager, then choose Try again.';
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
