@echo off
REM ===================================================================
REM  HOOKCUT im TESTMODUS starten: so, wie es sich online verhaelt.
REM
REM  Normalerweise kostet auf deinem eigenen Rechner nichts etwas -
REM  es sind ja deine Werkzeuge und deine Rechenzeit. Damit siehst du
REM  die Bezahlschranke aber auch nie. Dieses Skript schaltet sie fuer
REM  einen Start an, damit du pruefen kannst, was ein Kunde sieht.
REM
REM  Es aendert NICHTS an deinen Daten. Schliesst du die Fenster und
REM  startest wieder mit start-hookcut.bat, ist alles wie vorher.
REM ===================================================================
cd /d "%~dp0"

echo.
echo ============================================================
echo   TESTMODUS: Die Video-Werkzeuge kosten hier ein Abo.
echo ============================================================
echo.
echo   Dein eigenes Konto hat noch KEINS - du siehst also gleich
echo   genau das, was ein neuer Nutzer ohne Abo sieht:
echo.
echo     - "Wochen-Content" zeigt die Bezahlschranke
echo     - "Dashboard" zeigt die Bezahlschranke
echo     - in der Seitenleiste steht "Kostenlos"
echo     - der Knopf "Reel erstellen" fehlt
echo.
echo   Willst du danach wieder durchkommen: hookcut-abo.bat
echo   doppelklicken, Punkt 4 (unbefristet), deine E-Mail eingeben,
echo   dann im Browser neu laden.
echo.
echo ============================================================
echo.
pause

start "HOOKCUT Backend (Testmodus)" cmd /k "%~dp0_backend-premium.bat"
start "HOOKCUT Frontend"            cmd /k "%~dp0_frontend.bat"

echo Browser oeffnet gleich (http://localhost:5173).
echo Zum Beenden die beiden neuen Fenster schliessen.

timeout /t 8 >nul
start "" http://localhost:5173
