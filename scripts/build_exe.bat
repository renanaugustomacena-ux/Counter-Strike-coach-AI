@echo off
REM W3 (replace-not-delete): the old script PyInstalled the DELETED Kivy
REM main.py with --collect-all kivy. The PySide6 build lives in
REM packaging/cs2_analyzer_win.spec via the production script.
echo --- Macena build: delegating to the current PySide6 pipeline ---
call "%~dp0build_production.bat" %*
