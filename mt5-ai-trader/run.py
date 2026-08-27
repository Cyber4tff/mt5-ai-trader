"""
API Server Launcher

Starts the FastAPI server for MT5 AI Trader.

Usage:
    python run.py
    TRADING_MODE=demo python run.py
    PORT=9000 python run.py
"""
import uvicorn
from config.settings import settings
from utils.logging import setup_logging

setup_logging(settings.log_level, settings.log_file)

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"  MT5 AI Trader v2.0")
    print(f"  Mode: {settings.trading_mode.upper()}")
    print(f"  Server: http://{settings.host}:{settings.port}")
    print(f"  Docs:   http://{settings.host}:{settings.port}/docs")
    print(f"  Symbols: {', '.join(settings.trading_symbols)}")
    print(f"  Risk per trade: {settings.risk_per_trade*100}%")
    print(f"  Max daily loss: {settings.max_daily_drawdown_pct*100}%")
    print(f"{'='*60}\n")

    uvicorn.run(
        'app.main:app',
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
