@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo MACENA CS2 ANALYZER - PRODUCTION BUILD AUTOMATION
echo =====================================================================

:: 1. Setup Environment: venv_win (scripts\Setup_Macena_CS2.ps1) or .venv
set "VENV=venv_win"
if not exist "%VENV%\Scripts\activate.bat" set "VENV=.venv"
if not exist "%VENV%\Scripts\activate.bat" (
    echo [!] No venv_win or .venv found. Run scripts\Setup_Macena_CS2.ps1 first.
    pause
    exit /b 1
)
echo [*] Activating Virtual Environment (%VENV%)...
call "%VENV%\Scripts\activate.bat"

:: 1.2 Pre-flight Validation
echo [*] Running Pre-flight Validation...
if not exist Programma_CS2_RENAN\tools\sync_integrity_manifest.py ( echo [!] Missing sync_integrity_manifest.py & pause & exit /b 1 )
if not exist tools\audit_binaries.py ( echo [!] Missing tools\audit_binaries.py & pause & exit /b 1 )
if not exist packaging\cs2_analyzer_win.spec ( echo [!] Missing packaging\cs2_analyzer_win.spec & pause & exit /b 1 )
if not exist tools\gen_version_iss.py ( echo [!] Missing tools\gen_version_iss.py & pause & exit /b 1 )

echo [*] Checking Python dependencies (Qt frontend, storage, torch, PyInstaller)...
python -c "import PySide6, sqlmodel, alembic, torch, PyInstaller" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Missing build dependencies in %VENV%: pip install -r requirements-lock-cpu.txt pyinstaller==6.17.0
    pause
    exit /b 1
)

:: 1.4 Factory models: whatever sits in models\global ships (see README.txt there)
if not exist Programma_CS2_RENAN\models\global\*.pt (
    echo [!] No .pt checkpoint in Programma_CS2_RENAN\models\global - the installer ships no factory model.
)

:: 1.5 Forensic Cleanup. The frozen tree is built into a SHORT folder: torch's
::     nested license files sit 182 characters below the dist root, and from a
::     long checkout path they pass Windows' 260-character limit (ISCC then
::     fails with "The system cannot find the path specified").
set "BUILD_ROOT=%TEMP%\mcb"
:: The deepest bundled file is 182 characters below <BUILD_ROOT>\dist\Macena_CS2_Analyzer,
:: so that folder must stay within 77 characters (260 - 182 - 1). Checked here
:: because a long-form TEMP with a longer user name silently breaks ISCC later.
set "MAX_DIST_ROOT=77"
python -c "import sys, os; p = os.path.join(sys.argv[1], 'dist', 'Macena_CS2_Analyzer'); print('[*] dist root: %%s (%%d chars, max %%s)' %% (p, len(p), sys.argv[2])); sys.exit(1 if len(p) > int(sys.argv[2]) else 0)" "%BUILD_ROOT%" "%MAX_DIST_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo [!] Build root too long for the bundled torch paths. Set TEMP to a short folder (e.g. C:\t) and retry.
    pause
    exit /b 1
)
echo [*] Cleaning previous build artifacts (%BUILD_ROOT%, dist\Macena_CS2_Installer_*.exe)...
if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%"
if exist build rmdir /s /q build
if not exist dist mkdir dist
del /q dist\Macena_CS2_Installer_*.exe 2>nul
mkdir "%BUILD_ROOT%"

echo [*] Synchronizing Database Schema...
"%VENV%\Scripts\alembic.exe" upgrade head
if %ERRORLEVEL% neq 0 (
    echo [!] Database migration failed! Build aborted.
    pause
    exit /b 1
)

:: 1.7 Generate Integrity Manifest (RASP)
echo [*] Generating Integrity Manifest for RASP...
python Programma_CS2_RENAN\tools\sync_integrity_manifest.py
if %ERRORLEVEL% neq 0 (
    echo [!] Manifest generation failed! Build aborted.
    pause
    exit /b 1
)

:: 1.8 Installer version from pyproject.toml (P10-02)
echo [*] Writing packaging\version.iss from pyproject.toml...
python tools\gen_version_iss.py
if %ERRORLEVEL% neq 0 (
    echo [!] version.iss generation failed! Build aborted.
    pause
    exit /b 1
)

:: 2. Run PyInstaller
echo [*] Building Executable (PyInstaller, packaging\cs2_analyzer_win.spec) into %BUILD_ROOT%...
python -m PyInstaller --noconfirm packaging\cs2_analyzer_win.spec --log-level WARN --distpath "%BUILD_ROOT%\dist" --workpath "%BUILD_ROOT%\build"
if %ERRORLEVEL% neq 0 (
    echo [!] Build failed! See the PyInstaller output above.
    pause
    exit /b 1
)
set "DIST_APP=%BUILD_ROOT%\dist\Macena_CS2_Analyzer"

:: 2.5 Master Binary Integrity Audit
echo [*] Executing Master Binary Security Audit...
python tools\audit_binaries.py "%DIST_APP%"
if %ERRORLEVEL% neq 0 (
    echo [!] Binary audit failed! Distribution is insecure.
    pause
    exit /b 1
)
echo [+] Security Chain locked for all bundled DLLs.

:: 2.7 Packaged selftest: the exe must run from a folder it cannot write to,
::     with its data root in a scratch LOCALAPPDATA (nothing touches this profile).
echo [*] Running the packaged selftest...
set "SELFTEST_HOME=%TEMP%\macena_selftest_%RANDOM%"
mkdir "%SELFTEST_HOME%"
icacls "%DIST_APP%" /deny "%USERNAME%:(OI)(CI)(W)" >nul
set "LOCALAPPDATA_BACKUP=%LOCALAPPDATA%"
set "LOCALAPPDATA=%SELFTEST_HOME%"
start /wait "" "%DIST_APP%\Macena_CS2_Analyzer.exe" --selftest
set "SELFTEST_RC=%ERRORLEVEL%"
set "LOCALAPPDATA=%LOCALAPPDATA_BACKUP%"
icacls "%DIST_APP%" /remove:d "%USERNAME%" >nul
if exist "%SELFTEST_HOME%\MacenaCS2Analyzer\selftest_report.json" type "%SELFTEST_HOME%\MacenaCS2Analyzer\selftest_report.json"
rmdir /s /q "%SELFTEST_HOME%"
if not "%SELFTEST_RC%"=="0" (
    echo [!] Packaged selftest failed (exit %SELFTEST_RC%). Build aborted.
    pause
    exit /b 1
)
echo [+] Packaged selftest passed.

:: 3. Compile Installer (optional if Inno Setup is installed)
::    Inno Setup installs per-user by default (%LOCALAPPDATA%\Programs), so look
::    there first, then the machine-wide locations.
echo [*] Checking for Inno Setup Compiler...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "!ISCC!" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "!ISCC!" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "!ISCC!" (
    echo [*] Compiling Windows Installer (sources from %BUILD_ROOT%\dist, output to dist\)...
    "!ISCC!" "/DDistDir=%BUILD_ROOT%\dist" packaging\windows_installer.iss
    if !ERRORLEVEL! equ 0 (
        echo [+] PROFESSIONAL INSTALLER CREATED: see dist\Macena_CS2_Installer_*.exe
    ) else (
        echo [!] Inno Setup compilation failed!
    )
) else (
    echo [!] Inno Setup (ISCC.exe) not found (looked under %%LOCALAPPDATA%%\Programs and Program Files).
    echo [!] Please install Inno Setup 6 or update the path in this script.
)
echo [i] Portable (unpacked) version available at: %DIST_APP%\

echo =====================================================================
echo BUILD PROCESS COMPLETE
echo =====================================================================
pause
