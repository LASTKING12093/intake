#define AppVersion GetEnv('INTAKE_VERSION')
#if AppVersion == ""
  #error INTAKE_VERSION must be set by scripts/release.ps1
#endif
[Setup]
AppId={{B78C267D-EB7A-4DF1-B80B-295417FA01E3}
AppName=INTAKE
AppVersion={#AppVersion}
AppVerName=INTAKE {#AppVersion}
AppPublisher=LASTKING12093
AppPublisherURL=https://github.com/LASTKING12093/intake
AppSupportURL=https://github.com/LASTKING12093/intake/issues
AppUpdatesURL=https://github.com/LASTKING12093/intake/releases
DefaultDirName={localappdata}\Programs\INTAKE
DefaultGroupName=INTAKE
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
WizardStyle=modern
SetupIconFile=..\app\resources\icon.ico
UninstallDisplayIcon={app}\INTAKE.exe
VersionInfoVersion={#AppVersion}.0
OutputDir=..\release
OutputBaseFilename=Intake-Setup-x64
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\INTAKE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\INTAKE"; Filename: "{app}\INTAKE.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\INTAKE"; Filename: "{app}\INTAKE.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\INTAKE.exe"; Description: "Launch INTAKE"; Flags: nowait postinstall skipifsilent
