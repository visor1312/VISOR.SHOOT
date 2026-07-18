@echo off
REM ===================================================================
REM  HOOKCUT-EDITOR starten (Windows) - einfach doppelklicken.
REM  Startet die Analyse (Port 8000) + den Video-Editor (Port 5173)
REM  in zwei Fenstern und oeffnet danach Chrome.
REM
REM  Einmalig vorher noetig:
REM    - Python-Pakete:  pip install -r requirements.txt
REM    - Editor-Pakete:  im Ordner editor einmal  npm install
REM
REM  WICHTIG: Der Editor braucht Chrome oder Edge (WebGPU).
REM ===================================================================
cd /d "%~dp0"

start "HOOKCUT Analyse" cmd /k "%~dp0_backend.bat"
start "HOOKCUT Editor"  cmd /k "cd /d %~dp0editor && echo === HOOKCUT Editor (Port 5173) === && call npm run dev"

echo.
echo Analyse und Editor werden gestartet...
echo Browser oeffnet gleich automatisch (http://localhost:5173).
echo Zum Beenden einfach die beiden neuen Fenster schliessen.
echo.

timeout /t 10 >nul
start "" http://localhost:5173
