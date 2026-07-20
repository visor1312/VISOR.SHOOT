@echo off
REM Notfall-Reset: setzt das Passwort eines HOOKCUT-Kontos neu (nur lokal
REM am Rechner moeglich - es gibt bewusst keinen "Passwort vergessen"-Link,
REM solange HOOKCUT nicht online gehostet wird).
cd /d "%~dp0"

REM Windows-Store-Python (dort liegen deine pip-Pakete). Falls nicht
REM vorhanden, faellt es auf das normale "python" im PATH zurueck.
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" -m backend.admin reset-password
pause
