@echo off
title MT5 Trading Engine - Python Backend
echo ============================================
echo   MT5 AI Trading Engine - Starting Backend
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Navigate to the trading engine folder
cd /d "%~dp0mini-services\trading-engine"

echo [INFO] Checking Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies!
    pause
    exit /b 1
)

echo.
echo [INFO] Starting Trading Engine on port 8001...
echo [INFO] Keep this window open while using the app.
echo [INFO] Press Ctrl+C to stop the engine.
echo.

python -m uvicorn engine.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir engine

pause