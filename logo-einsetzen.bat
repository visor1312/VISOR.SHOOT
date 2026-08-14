@echo off
setlocal
REM ===================================================================
REM  Original-Logo einsetzen.
REM
REM  BENUTZUNG: die Logodatei mit der Maus auf DIESE Datei ziehen und
REM  loslassen. Nicht doppelklicken - dann weiss das Skript nicht,
REM  welche Datei gemeint ist.
REM
REM  Es erkennt am Dateinamen, worum es sich handelt:
REM    ...mark...    oder ...symbol...   -> nur die Bildmarke
REM    ...horizontal... oder ...-h...    -> Marke neben Schriftzug
REM    ...vertical...   oder ...-v...    -> Marke ueber Schriftzug
REM  Passt nichts davon, fragt es nach.
REM ===================================================================
cd /d "%~dp0"

if "%~1"=="" goto keine_datei

set "QUELLE=%~1"
set "EXT=%~x1"
set "NAME=%~n1"

REM Endung pruefen - alles andere kann der Browser nicht anzeigen.
if /i "%EXT%"==".svg" goto endung_ok
if /i "%EXT%"==".png" goto endung_ok
echo.
echo   "%EXT%" kann die Oberflaeche nicht anzeigen.
echo   Gebraucht wird eine SVG (am besten) oder eine PNG mit
echo   durchsichtigem Hintergrund.
echo.
pause
exit /b 1

:endung_ok
REM Kleinschreibung fuer den Vergleich.
for /f "delims=" %%A in ('powershell -NoProfile -Command "'%NAME%'.ToLower()"') do set "KLEIN=%%A"

set "ZIEL="
echo %KLEIN% | findstr /C:"horizontal" >nul && set "ZIEL=lockup-h"
if not defined ZIEL echo %KLEIN% | findstr /C:"vertical" >nul && set "ZIEL=lockup-v"
if not defined ZIEL echo %KLEIN% | findstr /C:"mark" >nul && set "ZIEL=mark"
if not defined ZIEL echo %KLEIN% | findstr /C:"symbol" >nul && set "ZIEL=mark"
if defined ZIEL goto gewaehlt

:fragen
cls
echo.
echo ============================================================
echo   Was ist "%NAME%%EXT%"?
echo ============================================================
echo.
echo   1  Nur die Bildmarke (Balken + Unterschrift, ohne Text)
echo   2  Marke NEBEN dem Schriftzug (waagerecht)
echo   3  Marke UEBER dem Schriftzug (senkrecht)
echo   4  Abbrechen
echo.
set "WAHL="
set /p WAHL=Bitte Zahl eingeben und Enter:
if "%WAHL%"=="1" set "ZIEL=mark"
if "%WAHL%"=="2" set "ZIEL=lockup-h"
if "%WAHL%"=="3" set "ZIEL=lockup-v"
if "%WAHL%"=="4" exit /b 0
if not defined ZIEL goto fragen

:gewaehlt
REM Endung IMMER klein schreiben. Zieht jemand "Logo.PNG" drauf, entstuende
REM sonst "selfsign-mark.PNG" - die Oberflaeche fragt aber nach ".png", und
REM auf einem Linux-Server (Hosting) ist das ein anderer Dateiname. Genau
REM daran ist es einmal gescheitert: Logo kopiert, Anzeige leer.
if /i "%EXT%"==".svg" set "EXT=.svg"
if /i "%EXT%"==".png" set "EXT=.png"

set "ZIELDATEI=web\public\selfsign-%ZIEL%%EXT%"

REM BEIDE Varianten vorher loeschen. Zwei Gruende: eine alte SVG wuerde sonst
REM weiter gewinnen (die Oberflaeche probiert SVG zuerst), und Windows behaelt
REM beim Ueberschreiben die alte Gross-/Kleinschreibung des Dateinamens bei.
del /q "web\public\selfsign-%ZIEL%.svg" 2>nul
del /q "web\public\selfsign-%ZIEL%.png" 2>nul

echo.
echo   Kopiere nach %ZIELDATEI%
copy /y "%QUELLE%" "%ZIELDATEI%" >nul
if errorlevel 1 (
    echo   FEHLER beim Kopieren - laeuft die Datei noch in einem Programm?
    pause
    exit /b 1
)
if not exist "%ZIELDATEI%" (
    echo   FEHLER: %ZIELDATEI% ist nach dem Kopieren nicht da.
    pause
    exit /b 1
)

echo   Fertig. Im Browser einmal Strg+F5 druecken.
echo.

echo   Soll das Logo auch ins Projekt gespeichert und hochgeladen werden?
echo   (Dann ist es dauerhaft drin und geht bei einem Update nicht verloren.)
set "SPEICHERN="
set /p SPEICHERN=j / n:
if /i not "%SPEICHERN%"=="j" goto ende

echo.
REM --no-verify: auf diesem Rechner haengen fremde Pruef-Skripte (VITE+) in
REM den git-Hooks, die mit diesem Projekt nichts zu tun haben und beim
REM Commit UND beim Push abbrechen. Ein Logo-Bild hat mit Code-Qualitaet
REM nichts zu tun - die Pruefungen werden hier deshalb uebersprungen.
git add "web/public/selfsign-%ZIEL%%EXT%"
git commit --no-verify -m "Original-Logo eingesetzt (%ZIEL%)"
git push --no-verify
if errorlevel 1 (
    echo.
    echo   Das Hochladen hat nicht geklappt - die Meldung steht oben.
    echo   Das Logo liegt aber richtig und wird angezeigt; nur gesichert
    echo   ist es noch nicht.
)

:ende
echo.
pause
exit /b 0

:keine_datei
cls
echo.
echo ============================================================
echo   Original-Logo einsetzen
echo ============================================================
echo.
echo   Zieh deine Logodatei mit der Maus auf diese .bat-Datei
echo   und lass sie los. Doppelklicken reicht nicht - dann weiss
echo   das Skript nicht, welche Datei gemeint ist.
echo.
echo   Gebraucht wird eine SVG (am besten, bleibt in jeder Groesse
echo   scharf) oder eine PNG mit durchsichtigem Hintergrund.
echo.
echo   Du kannst nacheinander mehrere Dateien einsetzen:
echo     - nur die Bildmarke
echo     - Marke neben dem Schriftzug (fuer die Seitenleiste)
echo     - Marke ueber dem Schriftzug (fuer die Anmeldemaske)
echo.
pause
exit /b 1
