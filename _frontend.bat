@echo off
REM Hilfsskript - wird von start-hookcut.bat aufgerufen.
REM Startet den Vite-Dev-Server aus dem Ordner web.
cd /d "%~dp0web"

echo === HOOKCUT Frontend (Port 5173) ===
call npm run dev
