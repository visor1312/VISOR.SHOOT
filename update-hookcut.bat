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
echo === HOOKCUT wird gestartet ===
call "%~dp0start-hookcut.bat"
