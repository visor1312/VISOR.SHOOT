@echo off
REM ===================================================================
REM  Die eigentliche Update-Arbeit. Wird von update-selfsign.bat
REM  gestartet - bitte nicht direkt doppelklicken.
REM
REM  WARUM eine eigene Datei: Windows haelt eine laufende .bat-Datei
REM  offen. Wuerde "git pull" genau die Datei umbenennen oder loeschen,
REM  die gerade laeuft, bricht der Vorgang mit "Permission denied"
REM  mittendrin ab. Genau das ist beim Umbenennen von
REM  update-hookcut.bat -> update-selfsign.bat passiert.
REM  Diese Datei heisst deshalb neutral und wird nie umbenannt; die
REM  sichtbare update-selfsign.bat beendet sich, BEVOR der Pull laeuft.
REM ===================================================================
cd /d "%~dp0"

echo.
echo === Neueste Aenderungen werden geholt (git pull) ===
echo Zweig:
git rev-parse --abbrev-ref HEAD
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

echo.
echo === Oberflaechen-Pakete pruefen (npm) ===
REM Hier stand frueher nur der Kommentar, _frontend.bat ziehe die npm-Pakete
REM beim Start automatisch nach. Das stimmte nicht: _frontend.bat ruft
REM "npm run dev" auf, und das installiert nichts. Kaeme eine neue
REM Oberflaechen-Bibliothek dazu, braeche der Start mit "Cannot find module".
REM Deshalb jetzt ausdruecklich. Ist alles aktuell, dauert es zwei Sekunden.
pushd "%~dp0web"
call npm install
popd

echo.
echo === selfsign wird gestartet ===
call "%~dp0start-selfsign.bat"
