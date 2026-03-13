# ================================================================================
# MACENA CS2 ANALYZER - CLINICAL INSTALLATION SETUP (v1.0)
# ================================================================================

$ErrorActionPreference = "Continue"
Write-Host "Starting Macena CS2 Analyzer Setup..." -ForegroundColor Cyan

# 1. Environment Verification
Write-Host "[*] Verifying Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[+] Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[!] Python not found. Please install Python 3.10 or 3.12 from python.org" -ForegroundColor Red
    exit
}

# 2. Virtual Environment Creation
if (-Not (Test-Path "venv_win")) {
    Write-Host "[*] Creating clinical virtual environment..." -ForegroundColor Yellow
    python -m venv venv_win
    Write-Host "[+] Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "[+] Virtual environment already exists." -ForegroundColor Green
}

# 3. Dependency Installation
Write-Host "[*] Installing synchronized dependency set..." -ForegroundColor Yellow
$pipPath = ".\venv_win\Scripts\pip.exe"

# Specialized PyTorch CPU Installation for Stability
Write-Host "[*] Installing PyTorch (CPU optimized - Force Refresh)..." -ForegroundColor Cyan
& $pipPath install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Standard Requirements
Write-Host "[*] Installing standard requirements..." -ForegroundColor Cyan
& $pipPath install -r requirements.txt

# 4. Database Initialization
Write-Host "[*] Initializing local knowledge base..." -ForegroundColor Yellow
$pythonPath = ".\venv_win\Scripts\python.exe"
& $pythonPath -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database(); print('Database Ready.')"

# 5. Playwright Setup
Write-Host "[*] Finalizing browser components..." -ForegroundColor Yellow
& $pipPath install playwright
& $pythonPath -m playwright install chromium

Write-Host "`n" + "="*60 -ForegroundColor Cyan
Write-Host "INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "To start the application, run: .\venv_win\Scripts\python.exe Programma_CS2_RENAN/main.py" -ForegroundColor Yellow
Write-Host "="*60 -ForegroundColor Cyan
