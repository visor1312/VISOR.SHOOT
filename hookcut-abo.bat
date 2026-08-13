@echo off
REM HOOKCUT Premium von Hand verwalten - solange kein Zahlungsanbieter
REM angebunden ist (Rechnung per Ueberweisung, hier freischalten).
cd /d "%~dp0"

REM Windows-Store-Python (dort liegen deine pip-Pakete). Falls nicht
REM vorhanden, faellt es auf das normale "python" im PATH zurueck.
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"

:menue
cls
echo ============================================
echo   HOOKCUT Premium - Abos verwalten
echo ============================================
echo.
echo   1  Alle Abos anzeigen
echo   2  Premium freischalten (1 Monat)
echo   3  Premium freischalten (12 Monate)
echo   4  Premium unbefristet (eigenes Konto / Test)
echo   5  Premium beenden
echo   6  Beenden
echo.
set "WAHL="
set /p WAHL=Bitte Zahl eingeben und Enter:

if "%WAHL%"=="1" goto liste
if "%WAHL%"=="2" goto monat1
if "%WAHL%"=="3" goto monat12
if "%WAHL%"=="4" goto unbefristet
if "%WAHL%"=="5" goto nehmen
if "%WAHL%"=="6" goto ende
goto menue

:liste
echo.
"%PY%" -m backend.admin abo-liste
goto weiter

:monat1
echo.
"%PY%" -m backend.admin abo-geben --monate 1
goto weiter

:monat12
echo.
"%PY%" -m backend.admin abo-geben --monate 12
goto weiter

:unbefristet
echo.
"%PY%" -m backend.admin abo-geben --unbefristet
goto weiter

:nehmen
echo.
"%PY%" -m backend.admin abo-nehmen
goto weiter

:weiter
echo.
pause
goto menue

:ende
