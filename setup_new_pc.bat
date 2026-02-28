@echo off
echo --- Macena CS2 Analyzer Setup ---
echo 1. Checking for Python...
python --version
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b
)

echo 2. Creating Virtual Environment (venv_win)...
python -m venv venv_win

echo 3. Upgrading pip...
.\venv_win\Scripts\python.exe -m pip install --upgrade pip

echo 4. Installing Dependencies...
.\venv_win\Scripts\pip install -r requirements.txt

echo.
echo Setup Complete! You can now run the app.
pause
