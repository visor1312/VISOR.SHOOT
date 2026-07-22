@echo off
REM Hilfsskript - wird von start-hookcut.bat aufgerufen.
REM Startet den Vite-Dev-Server aus dem Ordner web.
cd /d "%~dp0web"

REM Sicherstellen, dass alle npm-Pakete da sind. Holt nach einem Update
REM automatisch neue Abhaengigkeiten nach (z.B. react-router-dom) - ohne
REM diesen Schritt bricht der Start mit "Failed to resolve import" ab.
REM Bei bereits vollstaendiger Installation ist es nur ein kurzer Check.
echo === Frontend-Pakete pruefen (npm install) ===
call npm install
if errorlevel 1 (
    echo.
    echo FEHLER bei npm install - bitte Meldung oben pruefen.
    pause
    exit /b 1
)

echo === HOOKCUT Frontend (Port 5173) ===
call npm run dev
