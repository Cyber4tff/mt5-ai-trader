@echo off
title MT5 AI Auto-Trader 24/7 Daemon
echo ========================================================
echo   MT5 AI Auto-Trader - 24/7 Global Cloud Service
echo ========================================================
echo.

cd /d "C:\Users\cyber\Downloads\workspace-7db3e6fa-84fd-4d6a-b1f2-baa7f227a64f"

echo [1/2] Starting Python Trading Engine on port 8001...
start "Trading Engine (Port 8001)" /min cmd /k "cd mini-services\trading-engine & python -m uvicorn engine.main:app --host 0.0.0.0 --port 8001 --reload"

echo [2/2] Starting 24/7 Global Tunnel Bridge (Cloudflare)...
start "Global Tunnel Bridge" /min cmd /k "npx cloudflared tunnel --url http://127.0.0.1:8001"

echo.
echo ========================================================
echo SUCCESS: 24/7 Auto-Trading Engine and Web Bridge are live!
echo.
echo iPad Web Terminal URL:
echo https://m5-ai-trader-jj14zddui-cybers-projects-b64e1b20.vercel.app
echo ========================================================\
