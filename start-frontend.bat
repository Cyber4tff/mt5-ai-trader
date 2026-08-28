@echo off
title MT5 AI Trader - Next.js Frontend
echo ============================================
echo   MT5 AI Trader - Starting Frontend
echo ============================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed!
    echo Please install Node.js 20+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo [OK] Node.js found:
node --version
echo.

REM Navigate to the project folder
cd /d "%~dp0"

echo [INFO] Checking Node.js dependencies...
if not exist node_modules (
    echo [INFO] First time setup - installing dependencies (this may take a minute)...
    npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Generating Prisma client...
npx prisma generate

echo.
echo [INFO] Starting Next.js on port 3000...
echo [INFO] Open your browser and go to: http://localhost:3000
echo [INFO] Keep this window open while using the app.
echo [INFO] Press Ctrl+C to stop the server.
echo.

npx next dev --webpack -p 3000

pause