@echo off
REM ===================================================================
REM  Holt die neueste Version (git pull) und startet HOOKCUT neu.
REM  Einfach doppelklicken, wenn ich dir gesagt habe "git pull + neu
REM  starten". Nimmt dir beide Schritte ab.
REM ===================================================================
cd /d "%~dp0"

echo === Neueste Aenderungen werden geholt (git pull) ===
git pull
if errorlevel 1 (
    echo.
    echo FEHLER beim git pull - bitte Meldung oben pruefen.
    echo Fenster bleibt offen. Zum Schliessen eine Taste druecken.
    pause >nul
    exit /b 1
)

echo.
echo === Python-Pakete pruefen (neue Abhaengigkeiten nachinstallieren) ===
REM Windows-Store-Python (dort liegen deine pip-Pakete). Falls nicht
REM vorhanden, faellt es auf das normale "python" im PATH zurueck.
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m pip install -r requirements.txt
REM (npm-Pakete zieht _frontend.bat beim Start automatisch nach.)

echo.
echo === HOOKCUT wird gestartet ===
call "%~dp0start-hookcut.bat"
