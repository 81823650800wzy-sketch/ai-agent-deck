; AI Agent Deck Manager - Inno Setup 安装脚本
; 编译工具: Inno Setup 6 (https://jrsoftware.org/isinfo.php)

#define MyAppName "AI Agent Deck"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "AI Agent Deck Team"
#define MyAppURL "https://github.com/81823650800wzy-sketch/ai-agent-deck"
#define MyAppExeName "AI_Deck_Manager.exe"
#define MyAppSourceDir "..\Manager\dist\AI_Deck_Manager"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=..\Manager\LICENSE
OutputDir=..\dist
OutputBaseFilename=AI_Deck_Manager_Setup_{#MyAppVersion}
SetupIconFile=..\Manager\app\resources\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associatefiles"; Description: "关联 .adp 文件 (AI Agent Deck Profile)"; GroupDescription: "文件关联:"; Flags: unchecked

[Files]
; 主程序
Source: "{#MyAppSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Profile 示例文件
Source: "..\Manager\profiles\*.json"; DestDir: "{app}\profiles"; Flags: ignoreversion

; 固件文件（如果存在）
Source: "..\Manager\firmware\*"; DestDir: "{app}\firmware"; Flags: ignoreversion skipifsourcedoesntexist

; 文档
Source: "..\Manager\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\Manager\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{localappdata}\AI-Deck-Manager"; Flags: uninsalwaysuninstall
Name: "{localappdata}\AI-Deck-Manager\logs"; Flags: uninsalwaysuninstall
Name: "{localappdata}\AI-Deck-Manager\crashes"; Flags: uninsalwaysuninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; 文件关联 (.adp)
Root: HKA; Subkey: "Software\Classes\.adp"; ValueType: string; ValueName: ""; ValueData: "AIDeckProfile"; Flags: uninsdeletevalue; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\.adp\OpenWithProgids"; ValueType: string; ValueName: "AIDeckProfile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\AIDeckProfile"; ValueType: string; ValueName: ""; ValueData: "AI Agent Deck Profile"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\AIDeckProfile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatefiles
Root: HKA; Subkey: "Software\Classes\AIDeckProfile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatefiles

; 环境变量（添加到 PATH，用于命令行工具）
Root: HKA; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\AI-Deck-Manager"
Type: filesandordirs; Name: "{app}"

[Code]
// 检查是否已安装旧版本
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) then begin
    if (IsUpgrade()) then
      UnInstallOldVersion();
  end;
end;
