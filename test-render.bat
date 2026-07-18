@echo off
setlocal
REM ===================================================================
REM  HOOKCUT Hintergrund-Render TESTEN (Machbarkeits-Test)
REM
REM  Beweist, dass FreeCut ferngesteuert (ohne Editor-Fenster) ein
REM  fertiges, gestyltes 9:16-Video rendern kann.
REM
REM  Einfach doppelklicken und den Anweisungen folgen - kein Editieren!
REM  Voraussetzung: im Ordner editor einmal  npm install  + Google Chrome.
REM ===================================================================
cd /d "%~dp0"

echo ==============================================
echo   HOOKCUT Render-Test
echo ==============================================
echo.
echo Ziehe gleich die Dateien mit der Maus in DIESES Fenster
echo und druecke dann jeweils Enter.
echo.

set "VIDEO="
set /p "VIDEO=1) PERFORMANCE-VIDEO hierher ziehen, dann Enter: "
set "SONG="
set /p "SONG=2) SONG hierher ziehen, dann Enter: "

REM Von Drag-and-Drop mitgelieferte Anfuehrungszeichen entfernen:
set VIDEO=%VIDEO:"=%
set SONG=%SONG:"=%

if not exist "%VIDEO%" (
    echo.
    echo Konnte das Video nicht finden: "%VIDEO%"
    echo Bitte nochmal starten und die Datei ins Fenster ziehen.
    pause & exit /b 1
)
if not exist "%SONG%" (
    echo.
    echo Konnte den Song nicht finden: "%SONG%"
    echo Bitte nochmal starten und die Datei ins Fenster ziehen.
    pause & exit /b 1
)

set "STYLE=vibrant"
set "WS=%~dp0render_test_ws"
set "OUT=%~dp0hookcut_test.mp4"

echo.
echo Video: %VIDEO%
echo Song:  %SONG%
echo.
echo === Analyse + Hintergrund-Render (erster Lauf dauert ein paar Minuten) ===
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m backend.pipeline.render_pipeline "%VIDEO%" "%SONG%" "%WS%" --style %STYLE% --find-hook --render --out "%OUT%"

if errorlevel 1 (
    echo.
    echo FEHLER - bitte die Meldungen oben markieren, kopieren und mir schicken.
    pause & exit /b 1
)

echo.
echo === FERTIG ===  Ergebnis: %OUT%
start "" "%OUT%"
pause
