; ============================================
; AI Agent Deck Manager - Inno Setup 安装脚本
; 版本: 2.1.0
; ============================================

#define MyAppName      "AI Agent Deck Manager"
#define MyAppNameCN    "AI 代理控制台"
#define MyAppVersion   "2.1.0"
#define MyAppPublisher "AI Agent Deck Team"
#define MyAppURL       "https://github.com/81823650800wzy-sketch/ai-agent-deck"
#define MyAppExeName   "AI_Deck_Manager.exe"
#define MyYear         "2026"

; ── 源路径（相对于本 .iss 文件）──
; PyInstaller 输出目录，先运行 build.bat 生成
#define DistDir  "..\dist\AI_Deck_Manager"

[Setup]
; 应用标识（GUID 安装后写入注册表，卸载时用）
AppId={{A7E3B2C1-4D5F-6E8A-9B0C-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=Copyright (C) {#MyYear} {#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription={#MyAppName} Installer

; 默认安装目录
DefaultDirName={autopf}\AI Agent Deck Manager
; 开始菜单组名
DefaultGroupName={#MyAppName}
; 许可协议（可选，如果存在 LICENSE 文件）
LicenseFile=..\LICENSE

; 输出设置
OutputDir=.\output
OutputBaseFilename=AI_Deck_Manager_Setup_{#MyAppVersion}
; Setup 图标（如果有的话取消注释并替换路径）
; SetupIconFile=..\app\resources\icon.ico

; 压缩
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4

; 外观
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Windows 最低版本
MinVersion=10.0

; 卸载信息
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 语言
ShowLanguageDialog=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english";          MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";     Description: "{cm:CreateDesktopIcon}";     GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; ── 主程序（PyInstaller 打包输出）──
Source: "{#DistDir}\*";          DestDir: "{app}";    Flags: ignoreversion recursesubdirs createallsubdirs

; ── 固件（确保包含最新版本）──
Source: "..\firmware\*";         DestDir: "{app}\firmware";  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ── 配置模板 ──
Source: "..\profiles\*";         DestDir: "{app}\profiles";  Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist uninsneveruninstall

; ── 文档 ──
Source: "..\README.md";          DestDir: "{app}";    Flags: ignoreversion skipifsourcedoesntexist
Source: "..\LICENSE";             DestDir: "{app}";    Flags: ignoreversion skipifsourcedoesntexist
Source: "..\FLASH_GUIDE.md";     DestDir: "{app}";    Flags: ignoreversion skipifsourcedoesntexist
Source: "..\CRASH_HANDLER.md";   DestDir: "{app}";    Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; 用户数据目录（卸载时保留）
Name: "{localappdata}\AI_Deck_Manager";  Flags: uninsneveruninstall
; 用户自定义配置目录
Name: "{app}\profiles";                   Flags: uninsneveruninstall

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}";                       Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\固件烧录指南";                         Filename: "{app}\FLASH_GUIDE.md";  Flags: createonlyiffileexists

; 桌面快捷方式（可选任务）
Name: "{autodesktop}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 快速启动栏（仅 Win7 及以下）
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; 安装完成后可选启动
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[Registry]
; 文件关联（可选）—— 将 .adeckprofile 关联到本程序
; Root: HKCR; Subkey: ".adeckprofile";                          ValueType: string; ValueName: ""; ValueData: "AIDeckProfile";  Flags: uninsdeletevalue
; Root: HKCR; Subkey: "AIDeckProfile";                          ValueType: string; ValueName: ""; ValueData: "AI Deck Profile"; Flags: uninsdeletekey
; Root: HKCR; Subkey: "AIDeckProfile\shell\open\command";       ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; Root: HKCR; Subkey: "AIDeckProfile\DefaultIcon";              ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"

; 开机自启动（可选，取消注释启用）
; Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AIDeckManager"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue

[Code]
// ── 安装前检查是否正在运行 ──
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // 检查旧版本是否在运行
  if FindWindowByClassName('QWidget') <> 0 then
  begin
    if MsgBox('检测到 AI Agent Deck Manager 正在运行。'#13#10'请先关闭程序后再继续安装。'#13#10#13#10'是否自动关闭并继续？',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 尝试结束进程
      Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// ── 卸载前检查是否正在运行 ──
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  if FindWindowByClassName('QWidget') <> 0 then
  begin
    if MsgBox('AI Agent Deck Manager 正在运行，需要先关闭才能卸载。'#13#10'是否自动关闭？',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// ── 安装完成提示 ──
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 创建用户数据目录
    CreateDir(ExpandConstant('{localappdata}\AI_Deck_Manager'));
  end;
end;
