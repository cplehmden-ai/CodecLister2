#define MyAppName "CodecLister"
#define MyAppVersion GetEnv("CODECLISTER_VERSION")
#define MyAppExeName "CodecLister.exe"
#define MyAppSourceDir GetEnv("CODECLISTER_SOURCE_DIR")
#define MyAppOutputDir GetEnv("CODECLISTER_OUTPUT_DIR")

[Setup]
AppId={{5DDAC6CA-3B1D-4DB9-AFE2-CB1127FA055C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=CodecLister contributors
DefaultDirName={autopf}\CodecLister
DefaultGroupName=CodecLister
DisableProgramGroupPage=yes
OutputDir={#MyAppOutputDir}
OutputBaseFilename=CodecLister-Setup-{#MyAppVersion}-x64
SetupIconFile=src\codeclister\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#MyAppSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\CodecLister"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\CodecLister"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch CodecLister"; Flags: nowait postinstall skipifsilent