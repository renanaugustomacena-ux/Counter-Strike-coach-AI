; =====================================================================
; MACENA CS2 ANALYZER - INNO SETUP SCRIPT
; =====================================================================
; version.iss is generated from pyproject.toml by tools/gen_version_iss.py
; (scripts/build_production.bat runs it before compiling), so the installer
; version can never drift from the package version (P10-02).
#include "version.iss"
; DistDir: the PyInstaller output folder holding Macena_CS2_Analyzer\. torch's
; nested license files sit 182 characters below that folder, so from a long
; checkout path they pass Windows' 260-character limit and ISCC aborts with
; "The system cannot find the path specified". scripts\build_production.bat
; builds into a short folder and passes it as /DDistDir=...; the default is
; the repository's dist\ for short checkout paths.
#ifndef DistDir
#define DistDir "..\dist"
#endif

[Setup]
AppId={{D3B3E1A2-5678-4CDE-9012-3456789ABCDE}
AppName=Macena CS2 Analyzer
AppVersion={#AppVersion}
AppVerName=Macena CS2 Analyzer {#AppVersion}
AppPublisher=Macena
AppSupportURL=https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI
DefaultDirName={autopf}\Macena_CS2_Analyzer
DefaultGroupName=Macena CS2 Analyzer
UninstallDisplayIcon={app}\Macena_CS2_Analyzer.exe
AllowNoIcons=yes
; 64-bit only: the torch and PySide6 wheels are x64; install into the 64-bit
; Program Files, never the 32-bit view.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Per-machine by default, per-user on request. The app never writes beside
; its executable: data lives under %LOCALAPPDATA%\MacenaCS2Analyzer or the
; folder chosen in the setup wizard (DOCTRINE D-52).
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Output location
OutputDir=..\dist
OutputBaseFilename=Macena_CS2_Installer_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; One self-contained exe (the first compile with DiskSpanning=yes shipped a
; separate 457 MB "-1.bin" slice a user could forget to copy).
DiskSpanning=no
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
Source: "{#DistDir}\Macena_CS2_Analyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; MSVC runtime installer: optional. Download vc_redist.x64.exe from Microsoft
; and place it in packaging/ before compiling; without it the installer still
; builds and InitializeSetup tells the user where to get the runtime. It needs
; elevation, so it runs only in an administrative install (a per-user install
; cannot elevate: the first smoke stalled on it for seven minutes).
#ifexist "vc_redist.x64.exe"
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion dontcopy; Check: IsAdminInstallMode and not VCRedistInstalled
#endif

[Icons]
Name: "{group}\Macena CS2 Analyzer"; Filename: "{app}\Macena_CS2_Analyzer.exe"
Name: "{group}\{cm:UninstallProgram,Macena CS2 Analyzer}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Macena CS2 Analyzer"; Filename: "{app}\Macena_CS2_Analyzer.exe"; Tasks: desktopicon

[Run]
#ifexist "vc_redist.x64.exe"
; Install MSVC runtime silently if needed (administrative installs only)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Runtime..."; Flags: waituntilterminated skipifdoesntexist; Check: IsAdminInstallMode and not VCRedistInstalled
#endif
Filename: "{app}\Macena_CS2_Analyzer.exe"; Description: "{cm:LaunchProgram,Macena CS2 Analyzer}"; Flags: nowait postinstall skipifsilent

[Code]
function VCRedistInstalled: Boolean;
var
  Version: String;
begin
  { Check for MSVC 2015-2022 x64 runtime (required by PySide6 and Python).
    Both registry views: the runtime registers under the 64-bit key and the
    WOW6432Node mirror, and the first smoke on a machine with v14.51 installed
    still ran the redistributable. }
  Result := RegQueryStringValue(HKLM64,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
    'Version', Version)
    or RegQueryStringValue(HKLM32,
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
        'This application requires the Microsoft Visual C++ Redistributable.' + #13#10 + #13#10 +
        'The installer will continue, but if the application fails to start, ' +
        'please download and install vc_redist.x64.exe from:' + #13#10 +
        'https://aka.ms/vs/17/release/vc_redist.x64.exe',
        mbInformation, MB_OK);
    end;
  end;
end;

// The user's data (database, analyzed demos, trained models, logs) lives
// outside the install folder. Uninstalling the program must never delete it
// silently: ask, default to keeping it. (Line comments on purpose: a brace
// comment cannot mention the app constant, its closing brace ends the comment.)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\MacenaCS2Analyzer');
    if DirExists(DataDir) then
    begin
      if MsgBox('Remove your Macena data folder as well?' + #13#10 +
                DataDir + #13#10 + #13#10 +
                'It holds your database, analyzed demos, trained models and logs. ' +
                'Choose No to keep them for a future installation.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
