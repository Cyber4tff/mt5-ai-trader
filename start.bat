@echo off
title MT5 AI Trader - Launch All
echo ============================================
echo   MT5 AI Trader - Full System Launcher
echo ============================================
echo.
echo This will open TWO windows:
echo   Window 1: Python Trading Engine (port 8001)
echo   Window 2: Next.js Frontend (port 3000)
echo.
echo Make sure MT5 desktop is also open and logged in!
echo.
pause

REM Start the Python backend in a new window
start "MT5 Trading Engine" cmd /c ""%~dp0start-backend.bat""

REM Wait 5 seconds for the backend to start
timeout /t 5 /nobreak >nul

REM Start the Next.js frontend in a new window
start "MT5 AI Trader Frontend" cmd /c ""%~dp0start-frontend.bat""

echo.
echo [DONE] Both services are starting in separate windows.
echo.
echo Next steps:
echo   1. Wait about 15-20 seconds for everything to load
echo   2. Open your browser to: http://localhost:3000
echo   3. Make sure MT5 desktop is running and logged in
echo   4. The system will auto-detect MT5 and enable trading
