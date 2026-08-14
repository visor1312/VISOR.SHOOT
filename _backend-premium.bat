@echo off
REM Hilfsskript - wird von hookcut-premium-test.bat aufgerufen.
REM Wie _backend.bat, aber mit den Schaltern, die ONLINE gelten:
REM   HOOKCUT_PREMIUM_REQUIRED=1  -> die Werkzeuge kosten ein Abo
REM Alles andere (Datenbank, Projekte, Konten) bleibt gleich - es ist
REM derselbe HOOKCUT, nur mit angezogener Bezahlschranke.
cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"

set "HOOKCUT_PREMIUM_REQUIRED=1"

echo === HOOKCUT Backend (Port 8000) - TESTMODUS: Werkzeuge kosten ein Abo ===
"%PY%" -m uvicorn backend.main:app --port 8000
