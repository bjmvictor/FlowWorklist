#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "FlowWorklist"

[Setup]
AppId={{A9E14F85-83C6-4F96-9839-8E2D7FC6901B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=FlowWorklist
DefaultDirName={autopf}\FlowWorklist
DefaultGroupName=FlowWorklist
OutputDir=..\..\dist
OutputBaseFilename=FlowWorklist-Setup-{#MyAppVersion}-Windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\FlowWorklist.exe
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\..\dist\FlowWorklist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "portable.mode"

[Dirs]
Name: "{commonappdata}\FlowWorklist"; Permissions: users-modify
Name: "{commonappdata}\FlowWorklist\logs"; Permissions: users-modify
Name: "{commonappdata}\FlowWorklist\service_logs"; Permissions: users-modify
Name: "{commonappdata}\FlowWorklist\mpps-actions"; Permissions: users-modify

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\Open FlowWorklist"; Filename: "http://127.0.0.1:5000"
Name: "{group}\FlowWorklist Data"; Filename: "{commonappdata}\FlowWorklist"
Name: "{commondesktop}\FlowWorklist"; Filename: "http://127.0.0.1:5000"; Tasks: desktopicon

[Run]
Filename: "{app}\FlowWorklistService.exe"; Parameters: "install"; Flags: runhidden waituntilterminated; Check: ServiceMissing
Filename: "{app}\FlowWorklistService.exe"; Parameters: "start"; Flags: runhidden waituntilterminated
Filename: "http://127.0.0.1:5000"; Description: "Open FlowWorklist"; Flags: postinstall shellexec skipifsilent nowait

[UninstallRun]
Filename: "{app}\FlowWorklistService.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopFlowWorklist"
Filename: "{app}\FlowWorklistService.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveFlowWorklist"

[Code]
function ServiceExists: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'query FlowWorklist', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function ServiceMissing: Boolean;
begin
  Result := not ServiceExists;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  WrapperPath: String;
begin
  Result := '';
  WrapperPath := ExpandConstant('{app}\FlowWorklistService.exe');
  if FileExists(WrapperPath) and ServiceExists then
    Exec(WrapperPath, 'stop', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
