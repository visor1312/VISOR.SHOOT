@echo off
REM ===================================================================
REM  HOOKCUT Hintergrund-Render TESTEN (der wichtige Machbarkeits-Test)
REM
REM  Beweist, dass FreeCut ferngesteuert (ohne Editor-Fenster) ein
REM  fertiges, gestyltes 9:16-Video rendern kann - die Grundlage fuer
REM  die All-in-One-App.
REM
REM  ---- SO BENUTZEN ----
REM  1) Unten die zwei Pfade eintragen (Video + Song), Anfuehrungszeichen
REM     behalten. Rechtsklick auf eine Datei -> "Als Pfad kopieren".
REM  2) Diese Datei doppelklicken.
REM
REM  Voraussetzung (einmalig): im Ordner editor  ein  npm install
REM  Braucht Google Chrome (fuer den Hintergrund-Render).
REM ===================================================================

set "VIDEO=C:\Users\louis\Desktop\performance.mov"
set "SONG=C:\Users\louis\Desktop\song.mp3"
set "STYLE=vibrant"

cd /d "%~dp0"
set "WS=%~dp0render_test_ws"
set "OUT=%~dp0hookcut_test.mp4"

echo === Schritt 1/2: Analyse + Workspace bauen ===
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m backend.pipeline.render_pipeline "%VIDEO%" "%SONG%" "%WS%" --style %STYLE% --find-hook --render --out "%OUT%"

if errorlevel 1 (
    echo.
    echo FEHLER - bitte die Meldungen oben kopieren und mir schicken.
    pause
    exit /b 1
)

echo.
echo === FERTIG ===  Ergebnis: %OUT%
start "" "%OUT%"
pause
