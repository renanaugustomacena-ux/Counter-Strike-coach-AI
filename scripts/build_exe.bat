@echo off
echo --- Building Macena Standalone Executable ---
echo Cleaning old builds...
rmdir /s /q dist
rmdir /s /q build

echo Building...
.\venv_win\Scripts\pyinstaller --noconsole --name Macena --icon=Programma_CS2_RENAN/PHOTO_GUI/icon.ico --add-data "Programma_CS2_RENAN/PHOTO_GUI;Programma_CS2_RENAN/PHOTO_GUI" --add-data "Programma_CS2_RENAN/apps;Programma_CS2_RENAN/apps" --add-data "Programma_CS2_RENAN/data;Programma_CS2_RENAN/data" --collect-all kivymd --collect-all kivy Programma_CS2_RENAN/main.py

echo.
echo Build Complete!
echo Check the 'dist/Macena' folder.
pause
