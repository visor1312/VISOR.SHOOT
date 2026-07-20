@echo off
REM Erzeugt einen Einladungscode fuer die HOOKCUT-Registrierung.
REM Den Code auf der Registrierungs-Seite eingeben (gilt einmal).
cd /d "%~dp0"

REM Windows-Store-Python (dort liegen deine pip-Pakete). Falls nicht
REM vorhanden, faellt es auf das normale "python" im PATH zurueck.
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" -m backend.admin create-invite
pause
