@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo MACENA CS2 ANALYZER - PRODUCTION BUILD AUTOMATION
echo =====================================================================

:: 1. Setup Environment
echo [*] Activating Virtual Environment...
if not exist venv_win (
    echo [!] venv_win not found! Run Setup_Macena_CS2.ps1 first.
    pause
    exit /b 1
)
call venv_win\Scripts\activate

:: 1.2 Pre-flight Validation
echo [*] Running Pre-flight Validation...
if not exist Programma_CS2_RENAN\tools\sync_integrity_manifest.py ( echo [!] Missing sync_integrity_manifest.py & pause & exit /b 1 )
if not exist tools\audit_binaries.py ( echo [!] Missing tools\audit_binaries.py & pause & exit /b 1 )
if not exist packaging\cs2_analyzer_win.spec ( echo [!] Missing packaging\cs2_analyzer_win.spec & pause & exit /b 1 )

echo [*] Checking Python dependencies...
python -c "import keyring, kivymd, sqlmodel, alembic" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Missing core dependencies in venv_win. Please run fix_environment.ps1.
    pause
    exit /b 1
)

:: 1.5 Forensic Cleanup & Pre-flight
echo [*] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [*] Synchronizing Database Schema...
venv_win\Scripts\alembic.exe upgrade head
if %ERRORLEVEL% neq 0 (
    echo [!] Database migration failed! Build aborted.
    pause
    exit /b 1
)

:: 1.7 Generate Integrity Manifest (RASP)
echo [*] Generating Integrity Manifest for RASP...
python Programma_CS2_RENAN/tools/sync_integrity_manifest.py
if %ERRORLEVEL% neq 0 (
    echo [!] Manifest generation failed! Build aborted.
    pause
    exit /b 1
)

:: 2. Run PyInstaller
:: 2. Run PyInstaller via Advanced Debugger
echo [*] Building Executable with Advanced Build Debugger...
python Programma_CS2_RENAN\tools\build_tools.py build
if %ERRORLEVEL% neq 0 (
    echo [!] Build failed! Check build_debug.log and build_report.json for details.
    pause
    exit /b 1
)

:: 2.5 Master Binary Integrity Audit (Step 9)
echo [*] Executing Master Binary Security Audit...
python tools/audit_binaries.py
if %ERRORLEVEL% neq 0 (
    echo [!] Binary audit failed! Distribution is insecure.
    pause
    exit /b 1
)
echo [+] Security Chain locked for all bundled DLLs.

:: 3. Compile Installer
 (optional if Inno Setup is installed and in PATH)
echo [*] Checking for Inno Setup Compiler...
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "!ISCC!" (
    echo [*] Compiling Windows Installer...
    "!ISCC!" packaging\windows_installer.iss
    if !ERRORLEVEL! equ 0 (
        echo [+] PROFESSIONAL INSTALLER CREATED: dist\Macena_CS2_Installer.exe
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
