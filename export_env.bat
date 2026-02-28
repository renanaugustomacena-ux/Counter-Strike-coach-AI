@echo off
echo Exporting environment to requirements.txt...
.\venv_win\Scripts\pip freeze > requirements.txt
echo Done.
pause
