@echo off
REM ===================================================================
REM  HOOKCUT starten (Windows) - einfach doppelklicken.
REM  Startet Backend (Port 8000) + Frontend (Port 5173) in zwei
REM  Fenstern und oeffnet danach den Browser.
REM
REM  Einmalig vorher noetig:
REM    - Python-Pakete:  pip install -r requirements.txt
REM    - ffmpeg installiert (ffmpeg -version muss funktionieren)
REM    - Frontend-Pakete: im Ordner web einmal  npm install
REM ===================================================================
cd /d "%~dp0"

start "HOOKCUT Backend"  cmd /k "%~dp0_backend.bat"
start "HOOKCUT Frontend" cmd /k "%~dp0_frontend.bat"

echo.
echo Backend und Frontend werden gestartet...
echo Browser oeffnet gleich automatisch (http://localhost:5173).
echo Zum Beenden einfach die beiden neuen Fenster schliessen.
echo.

timeout /t 8 >nul
start "" http://localhost:5173
