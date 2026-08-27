#!/bin/bash
# Start the Cloud Trading Engine
cd /home/z/my-project/mini-services/trading-engine
exec python3 -m uvicorn engine.main:app --host 0.0.0.0 --port 8001 2>&1
