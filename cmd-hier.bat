@echo off
REM ===================================================================
REM  Oeffnet ein cmd-Fenster GENAU in diesem Projektordner.
REM  Einfach doppelklicken - dann bist du direkt im richtigen Ordner
REM  und kannst z.B. tippen:
REM
REM     git pull            (neueste Aenderungen holen)
REM     start-hookcut.bat   (HOOKCUT starten)
REM
REM  So landest du nie mehr aus Versehen in C:\Windows\system32.
REM ===================================================================
cd /d "%~dp0"
echo ==============================================
echo   HOOKCUT-Projektordner:
echo   %CD%
echo ==============================================
echo.
echo   Haeufige Befehle:
echo     git pull            - neueste Aenderungen holen
echo     start-hookcut.bat   - HOOKCUT starten
echo.
cmd /k
