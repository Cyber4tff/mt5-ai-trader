@echo off
title MT5 Trading Engine - Python Backend
echo ============================================
echo   MT5 AI Trading Engine - Starting Backend
echo ============================================
echo.

REM Locate Python interpreter (prefer Python 3.10 to avoid Application Control DLL restrictions)
set "PYTHON_EXE="

if exist "C:\Users\cyber\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=C:\Users\cyber\AppData\Local\Programs\Python\Python310\python.exe"
) else (
    py -3.10 --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=py -3.10"
    ) else (
        set "PYTHON_EXE=python"
    )
)

echo [OK] Using Python interpreter: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

REM Navigate to the trading engine folder
cd /d "%~dp0mini-services\trading-engine"

echo [INFO] Checking Python dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt
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

%PYTHON_EXE% -m uvicorn engine.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir engine

pause