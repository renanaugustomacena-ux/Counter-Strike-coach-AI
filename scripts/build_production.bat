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

:: 1.5 Forensic Cleanup
echo [*] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

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
echo [*] Building Executable (PyInstaller, packaging\cs2_analyzer_win.spec)...
python -m PyInstaller --noconfirm packaging\cs2_analyzer_win.spec --log-level WARN
if %ERRORLEVEL% neq 0 (
    echo [!] Build failed! See the PyInstaller output above.
    pause
    exit /b 1
)

:: 2.5 Master Binary Integrity Audit
echo [*] Executing Master Binary Security Audit...
python tools\audit_binaries.py
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
icacls "dist\Macena_CS2_Analyzer" /deny "%USERNAME%:(OI)(CI)(W)" >nul
set "LOCALAPPDATA_BACKUP=%LOCALAPPDATA%"
set "LOCALAPPDATA=%SELFTEST_HOME%"
start /wait "" "dist\Macena_CS2_Analyzer\Macena_CS2_Analyzer.exe" --selftest
set "SELFTEST_RC=%ERRORLEVEL%"
set "LOCALAPPDATA=%LOCALAPPDATA_BACKUP%"
icacls "dist\Macena_CS2_Analyzer" /remove:d "%USERNAME%" >nul
if exist "%SELFTEST_HOME%\MacenaCS2Analyzer\selftest_report.json" type "%SELFTEST_HOME%\MacenaCS2Analyzer\selftest_report.json"
rmdir /s /q "%SELFTEST_HOME%"
if not "%SELFTEST_RC%"=="0" (
    echo [!] Packaged selftest failed (exit %SELFTEST_RC%). Build aborted.
    pause
    exit /b 1
)
echo [+] Packaged selftest passed.

:: 3. Compile Installer (optional if Inno Setup is installed)
echo [*] Checking for Inno Setup Compiler...
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "!ISCC!" (
    echo [*] Compiling Windows Installer...
    "!ISCC!" packaging\windows_installer.iss
    if !ERRORLEVEL! equ 0 (
        echo [+] PROFESSIONAL INSTALLER CREATED: see dist\Macena_CS2_Installer_*.exe
    ) else (
        echo [!] Inno Setup compilation failed!
    )
) else (
    echo [!] Inno Setup (ISCC.exe) not found at !ISCC!
    echo [!] Please install Inno Setup 6 or update the path in this script.
    echo [!] Portable version available at: dist\Macena_CS2_Analyzer\
)

echo =====================================================================
echo BUILD PROCESS COMPLETE
echo =====================================================================
pause
