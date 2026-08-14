@echo off
REM ===================================================================
REM  Holt die neueste Version (git pull) und startet selfsign neu.
REM  Einfach doppelklicken.
REM
REM  Diese Datei macht die Arbeit bewusst NICHT selbst, sondern uebergibt
REM  an _update.bat und beendet sich sofort. Grund: Windows haelt eine
REM  laufende .bat-Datei offen. Wuerde ein "git pull" genau diese Datei
REM  umbenennen, braeche der Vorgang mit "Permission denied" mittendrin
REM  ab - und der Ordner waere halb aktualisiert. _update.bat heisst
REM  neutral und wird nie umbenannt.
REM ===================================================================
cd /d "%~dp0"
start "selfsign Update" cmd /k "%~dp0_update.bat"
