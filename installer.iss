; Inno Setup script for Printwell
; Compile with Inno Setup 6+: iscc installer.iss

[Setup]
AppName=Printwell
AppVersion=1.0.1
AppPublisher=raparks@icloud.com
AppPublisherURL=https://github.com/parkscloud/Printwell
DefaultDirName={autopf}\Printwell
DefaultGroupName=Printwell
OutputDir=installer_output
OutputBaseFilename=PrintwellSetup
SetupIconFile=src\printwell\printwell.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
CloseApplications=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Printwell.exe
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Start Printwell with Windows"; GroupDescription: "Startup:"
Name: "fileassoc"; Description: "Associate .md files with Printwell"; GroupDescription: "File association:"

[Files]
Source: "dist\Printwell\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Printwell"; Filename: "{app}\Printwell.exe"; IconFilename: "{app}\Printwell.exe"
Name: "{group}\Uninstall Printwell"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Printwell"; Filename: "{app}\Printwell.exe"; IconFilename: "{app}\Printwell.exe"; Tasks: desktopicon
Name: "{commonstartup}\Printwell"; Filename: "{app}\Printwell.exe"; Tasks: startupicon

[Registry]
; File association: .md files
Root: HKLM; Subkey: "Software\Classes\.md"; ValueType: string; ValueName: ""; ValueData: "Printwell.MarkdownFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKLM; Subkey: "Software\Classes\Printwell.MarkdownFile"; ValueType: string; ValueName: ""; ValueData: "Markdown File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKLM; Subkey: "Software\Classes\Printwell.MarkdownFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Printwell.exe,0"; Tasks: fileassoc
Root: HKLM; Subkey: "Software\Classes\Printwell.MarkdownFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Printwell.exe"" ""%1"""; Tasks: fileassoc
; Also handle .markdown extension
Root: HKLM; Subkey: "Software\Classes\.markdown"; ValueType: string; ValueName: ""; ValueData: "Printwell.MarkdownFile"; Flags: uninsdeletevalue; Tasks: fileassoc

[Run]
Filename: "{app}\Printwell.exe"; Description: "Launch Printwell"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\Printwell"

[Code]
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill', '/F /IM Printwell.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
  Result := True;
end;
