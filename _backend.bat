@echo off
REM Hilfsskript - wird von start-hookcut.bat aufgerufen.
REM Startet das FastAPI-Backend aus dem Projekt-Stammordner.
cd /d "%~dp0"

REM Windows-Store-Python (dort liegen deine pip-Pakete). Falls nicht
REM vorhanden, faellt es auf das normale "python" im PATH zurueck.
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"

echo === HOOKCUT Backend (Port 8000) ===
"%PY%" -m uvicorn backend.main:app --port 8000
