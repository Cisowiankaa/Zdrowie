#define MyAppName "Zdrowie"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Karolina Gleinert"
#define MyAppExeName "Zdrowie.exe"

[Setup]
AppId={{7DF9C1A2-93D6-4D27-A724-9F374E53D0D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Zdrowie
DefaultGroupName=Zdrowie
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Zdrowie-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Files]
Source: "dist\Zdrowie\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Zdrowie"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Zdrowie"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Dodatkowe skróty:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom Zdrowie"; Flags: nowait postinstall skipifsilent
