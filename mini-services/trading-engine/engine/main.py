from __future__ import annotations

import asyncio
import time
import traceback
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.analysis import (
    AIDecisionEngine,
    MarketStructureAnalyzer,
    MultiTimeframeAnalyzer,
    NakedForexStrategy,
    SupportResistanceDetector,
    calculate_atr_value,
)
from engine.data_fetcher import (
    fetch_candles,
    fetch_current_price,
    get_available_symbols,
    invalidate_cache,
)
from engine.models import (
    MarketAnalysis,
    MarketBias,
    PatternName,
    SignalType,
    TradingSession,
)
from engine.paper_trading import PaperTradingEngine
from engine.settings import settings

# ====================================================================
# FastAPI App
# ====================================================================

app = FastAPI(title="Cloud Trading Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals
trading_engine = PaperTradingEngine()
multi_tf = MultiTimeframeAnalyzer()
ai_engine = AIDecisionEngine()

# Background price updater task
_price_update_task: Optional[asyncio.Task] = None


# ====================================================================
# Request / Response Models
# ====================================================================


class ConnectRequest(BaseModel):
    broker: str = "paper"
    account_type: str = "paper"
    login: int = 0
    password: str = ""
    server: Optional[str] = None
    balance: float = 10000.0
    leverage: int = 100


class ScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    entry_timeframe: Optional[str] = None


class AutoTradeRequest(BaseModel):
    enabled: bool
    interval_minutes: int = 15


# ====================================================================
# Connection Endpoints
# ====================================================================


@app.post("/api/trading/connect")
async def connect(req: ConnectRequest):
    """Create a paper trading session."""
    try:
        broker_name = "Paper Trading"
        if req.broker and req.broker.lower() != "paper":
            # Map known broker names
            broker_map = {"exness": "Exness", "octafx": "OctaFX", "headway": "Headway"}
            broker_name = broker_map.get(req.broker.lower(), req.broker.title())

        session = trading_engine.create_session(
            broker=broker_name,
            account_type=req.account_type or "paper",
            login=req.login,
            password=req.password,
            balance=req.balance,
            leverage=req.leverage,
        )

        account = session.get_account()

        # Pre-fetch prices for default symbols
        for sym in settings.DEFAULT_SYMBOLS:
            price = fetch_current_price(sym)
            if price:
                session.price_cache[sym] = price

        return {
            "success": True,
            "session_id": session.session_id,
            "broker": session.broker,
            "server": session.server,
            "mode": "PAPER",
            "account": account.to_dict(),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trading/disconnect/{session_id}")
async def disconnect(session_id: str):
    trading_engine.remove_session(session_id)
    return {"success": True}


# ====================================================================
# Account Endpoints
# ====================================================================


@app.get("/api/trading/account/{session_id}")
async def get_account(session_id: str):
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return trading_engine.get_account_data(session)


@app.get("/api/trading/positions/{session_id}")
async def get_positions(session_id: str):
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "positions": [p.to_dict() for p in session.positions],
        "orders": [],
    }


# ====================================================================
# Scan / Analysis Endpoints
# ====================================================================


@app.post("/api/trading/scan/{session_id}")
async def scan(session_id: str, req: ScanRequest = None):
    """Run multi-timeframe analysis on symbols."""
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    symbols = req.symbols if req and req.symbols else settings.DEFAULT_SYMBOLS
    results = []

    for symbol in symbols:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _analyze_symbol, symbol, session
            )
            results.append(result)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "confluence": None,
                "decisions_count": 0,
                "actionable_signal": None,
                "errors": [str(e)],
                "risk_failures": None,
                "timeframes": {},
            })

    return {"results": results}


def _analyze_symbol(symbol: str, session: TradingSession) -> Dict:
    """Analyze a single symbol across all timeframes."""
    tf_data: Dict[str, pd.DataFrame] = {}
    analyses: Dict[str, MarketAnalysis] = {}
    timeframe_results: Dict = {}

    # Fetch candles for each timeframe
    for interval in settings.MTF_TIMEFRAMES:
        df = fetch_candles(symbol, interval)
        if df is not None:
            tf_data[interval] = df

    # Analyze each available timeframe
    for interval, df in tf_data.items():
        try:
            analysis = multi_tf.analyze_timeframe(df, symbol, interval)
            analyses[interval] = analysis

            # Map interval to display key (e.g. "1d" -> "D1")
            tf_display = {"1d": "D1", "4h": "H4", "1h": "H1", "15m": "M15", "5m": "M5"}.get(interval, interval.upper())
            bos_events = [b for b in analysis.structure_breaks if b.type == "BOS"]
            choch_events = [b for b in analysis.structure_breaks if b.type == "CHOCH"]

            timeframe_results[tf_display] = {
                "trend": analysis.trend.value,
                "bias": analysis.bias.value,
                "atr": round(analysis.atr, 5) if analysis.atr else 0,
                "volatility": analysis.volatility_regime or "normal",
                "momentum": analysis.momentum or "neutral",
                "bos": len(bos_events),
                "choch": len(choch_events),
                "signals_count": len(analysis.signals),
                "structure_breaks": len(bos_events) + len(choch_events),
                "sr_levels": len(analysis.sr_levels),
            }
        except Exception as e:
            tf_display = {"1d": "D1", "4h": "H4", "1h": "H1", "15m": "M15", "5m": "M5"}.get(interval, interval.upper())
            timeframe_results[tf_display] = {"error": str(e)}

    # Compute confluence across all timeframes
    confluence = multi_tf.compute_confluence(analyses)

    # Find best signal across all timeframes
    best_signal = None
    for tf, analysis in analyses.items():
        if analysis.signals:
            for sig in analysis.signals:
                if best_signal is None or sig.confidence > best_signal.confidence:
                    best_signal = sig

    # Run AI decision engine
    actionable = None
    risk_failures = None
    decisions_count = 0

    if best_signal and best_signal.signal_type != SignalType.NO_TRADE:
        decision = ai_engine.evaluate(best_signal, confluence, session)
        decisions_count = 1

        if decision["all_checks_passed"]:
            # Try to open the position
            direction = decision["direction"]
            pos = trading_engine.open_position(
                session=session,
                symbol=symbol,
                direction=direction,
                entry=best_signal.entry_price,
                sl=best_signal.stop_loss,
                tp=best_signal.take_profit,
                confidence=best_signal.confidence,
                reason=best_signal.reason,
            )

            if pos:
                actionable = {
                    "symbol": symbol,
                    "direction": direction,
                    "entry": pos.open_price,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "volume": pos.volume,
                    "confidence": best_signal.confidence,
                    "risk_reward": best_signal.risk_reward,
                    "confirmation_factors": decision["confirmation_factors"],
                    "confluence": {
                        "direction": confluence["direction"],
                        "score": confluence["score"],
                        "trend_alignment": confluence["trend_alignment"],
                        "factors": confluence["factors"],
                    },
                }
            else:
                risk_failures = ["Position could not be opened (risk limits)"]
        else:
            risk_failures = decision["rejection_reasons"]
            decisions_count = 1

    # Build confluence for response
    confluence_resp = None
    if confluence.get("factors") and confluence["factors"] != ["No data"]:
        confluence_resp = {
            "direction": confluence["direction"],
            "score": round(confluence["score"], 2),
            "trend_alignment": confluence["trend_alignment"],
            "factors": confluence["factors"],
            "higher_tf_bias": confluence["higher_tf_bias"].value,
            "bullish_ratio": round(confluence["bullish_ratio"], 2),
            "bearish_ratio": round(confluence["bearish_ratio"], 2),
        }

    return {
        "symbol": symbol,
        "confluence": confluence_resp,
        "decisions_count": decisions_count,
        "actionable": actionable,
        "errors": [],
        "risk_failures": risk_failures,
        "timeframes": timeframe_results,
    }


# ====================================================================
# Trading Endpoints
# ====================================================================


@app.post("/api/trading/close/{session_id}/{ticket}")
async def close_position(session_id: str, ticket: int):
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = trading_engine.close_position_by_ticket(session, ticket)
    if result is None:
        raise HTTPException(status_code=404, detail="Position not found")

    return {"success": True, "closed": result}


# ====================================================================
# Auto-Trade Endpoint
# ====================================================================


@app.post("/api/trading/auto-trade/{session_id}")
async def toggle_auto_trade(session_id: str, req: AutoTradeRequest):
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.auto_trade_enabled = req.enabled
    session.auto_trade_interval = req.interval_minutes
    session.auto_trade_last_scan = time.time() if req.enabled else None

    return {
        "success": True,
        "auto_trade": req.enabled,
        "interval_minutes": req.interval_minutes,
    }


# ====================================================================
# Risk & Status Endpoints
# ====================================================================


@app.get("/api/trading/risk-status/{session_id}")
async def get_risk_status(session_id: str):
    session = trading_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return trading_engine.get_risk_status(session)


@app.get("/api/trading/ai-status")
async def get_ai_status():
    """Return AI engine configuration and status."""
    return {
        "strategy": "Naked Forex + Market Structure",
        "patterns": [p.value for p in PatternName if p != PatternName.NONE],
        "structure_analysis": ["BOS", "CHOCH", "Swing Points", "Liquidity Sweeps"],
        "mtf_timeframes": ["D1", "H1", "M15"],
        "symbols_focus": settings.DEFAULT_SYMBOLS,
        "brokers": ["Paper Trading"],
        "confidence_threshold": settings.ai_confidence_threshold,
        "high_confidence": settings.ai_high_confidence,
        "risk_per_trade": settings.risk_per_trade,
        "max_daily_loss_pct": settings.max_daily_drawdown_pct,
        "max_consecutive_losses": settings.max_consecutive_losses,
        "max_open_positions": settings.max_open_positions,
        "max_trades_per_day": settings.max_trades_per_day,
        "max_spread_points": 0,  # No spread in paper trading
        "min_risk_reward": settings.min_risk_reward,
        "mode": "paper",
        "trailing_stop": False,
    }


@app.get("/api/trading/symbols")
async def get_symbols():
    """Return available symbols with current prices."""
    symbols_data = get_available_symbols()
    return {
        "symbols": [
            {"name": name, "price": data["price"]}
            for name, data in symbols_data.items()
        ]
    }


@app.get("/api/trading/health")
async def health():
    return {"status": "ok", "engine": "cloud", "version": "2.0.0"}


# ====================================================================
# Background Tasks
# ====================================================================


async def _background_price_updater():
    """Periodically update prices for all open positions."""
    while True:
        try:
            for session_id, session in list(trading_engine.sessions.items()):
                if session.positions:
                    trading_engine.update_positions(session)
        except Exception as e:
            print(f"[Background] Price update error: {e}")
        await asyncio.sleep(10)  # Update every 10 seconds


@app.on_event("startup")
async def startup():
    global _price_update_task
    _price_update_task = asyncio.create_task(_background_price_updater())
    print("[Engine] Cloud Trading Engine started on port 8001")
    print("[Engine] No MT5 dependency - uses real market data from Yahoo Finance")


@app.on_event("shutdown")
async def shutdown():
    if _price_update_task:
        _price_update_task.cancel()
