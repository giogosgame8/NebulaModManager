[Setup]
AppId={{8E4F77B2-9C14-4C93-A1E7-5F3B82D19A20}
AppName=Nebula Steam Mod Manager
AppVersion=1.0.0
AppPublisher=Nebula Mods
DefaultDirName={autopf}\NebulaModManager
DefaultGroupName=Nebula Mod Manager
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=NebulaModManager_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Enable true one-click automatic installation upon double-clicking the .exe
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Bundles the executable, Python runtime, UI assets, and UnRAR binary
Source: "dist\NebulaModManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Nebula Mod Manager"; Filename: "{app}\NebulaModManager.exe"
Name: "{autodesktop}\Nebula Mod Manager"; Filename: "{app}\NebulaModManager.exe"

[Run]
; Automatically launch the Mod Manager once installation finishes
Filename: "{app}\NebulaModManager.exe"; Description: "{cm:LaunchProgram,Nebula Mod Manager}"; Flags: nowait postinstall skipifsilent