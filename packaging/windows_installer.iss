; =====================================================================
; MACENA CS2 ANALYZER - INNO SETUP SCRIPT
; =====================================================================

[Setup]
AppId={{D3B3E1A2-5678-4CDE-9012-3456789ABCDE}
AppName=Macena CS2 Analyzer
; P10-02: Must match pyproject.toml [project].version on every release
AppVersion=1.0.0
AppPublisher=Macena
AppSupportURL=https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI
DefaultDirName={autopf}\Macena_CS2_Analyzer
DefaultGroupName=Macena CS2 Analyzer
AllowNoIcons=yes
; Output location
OutputDir=..\dist
OutputBaseFilename=Macena_CS2_Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DiskSpanning=yes
DiskClusterSize=512
; Minimum Windows version (Windows 10+)
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all files from the PyInstaller dist folder
Source: "..\dist\Macena_CS2_Analyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Bundle MSVC runtime installer (download vc_redist.x64.exe from Microsoft
; and place in packaging/ before building the installer)
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion dontcopy; Check: not VCRedistInstalled

[Icons]
Name: "{group}\Macena CS2 Analyzer"; Filename: "{app}\Macena_CS2_Analyzer.exe"
Name: "{group}\{cm:UninstallProgram,Macena CS2 Analyzer}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Macena CS2 Analyzer"; Filename: "{app}\Macena_CS2_Analyzer.exe"; Tasks: desktopicon

[Run]
; Install MSVC runtime silently if needed
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Runtime..."; Flags: waituntilterminated skipifdoesntexist
Filename: "{app}\Macena_CS2_Analyzer.exe"; Description: "{cm:LaunchProgram,Macena CS2 Analyzer}"; Flags: nowait postinstall skipifsilent

[Code]
function VCRedistInstalled: Boolean;
var
  Version: String;
begin
  { Check for MSVC 2015-2022 x64 runtime (required by PySide6 and Python) }
  Result := RegQueryStringValue(HKLM,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
    'Version', Version);
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if not VCRedistInstalled then
  begin
    if not FileExists(ExpandConstant('{src}\vc_redist.x64.exe')) then
    begin
      MsgBox(
        'This application requires the Microsoft Visual C++ Redistributable.' + #13#10 +
        #13#10 +
        'The installer will continue, but if the application fails to start, ' +
        'please download and install vc_redist.x64.exe from:' + #13#10 +
        'https://aka.ms/vs/17/release/vc_redist.x64.exe',
        mbInformation, MB_OK);
    end;
  end;
end;
