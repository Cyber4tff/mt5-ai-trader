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

# Try to import MetaTrader5 (Windows only, requires MT5 desktop app)
MT5_AVAILABLE = False
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    print("[Engine] MetaTrader5 library loaded successfully")
except ImportError:
    print("[Engine] MetaTrader5 library not available - MT5 direct connect disabled")

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


class MT5ConnectRequest(BaseModel):
    login: int
    password: str
    server: str


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
    _disconnect_mt5()
    return {"success": True}


# ── MT5 Direct Connection ─────────────────────────────────────────

_mt5_connected = False
_mt5_account_info = None


def _connect_mt5(login: int, password: str, server: str) -> dict:
    """Connect to MT5 terminal and return account info."""
    global _mt5_connected, _mt5_account_info

    if not MT5_AVAILABLE:
        return {
            "success": False,
            "error": "MT5 library not available on this server. MetaTrader5 requires Windows with the MT5 desktop application installed.",
            "mt5_available": False,
        }

    try:
        if not mt5.initialize():
            return {"success": False, "error": f"MT5 initialize failed: {mt5.last_error()}", "mt5_available": True}

        authorized = mt5.login(login, password, server)
        if not authorized:
            error_code = mt5.last_error()
            mt5.shutdown()
            error_messages = {
                1: "No connection with trade server",
                2: "Invalid authorization",
                3: "Invalid password",
                10: "No connection with trade server",
            }
            msg = error_messages.get(error_code, f"Login failed (error {error_code})")
            return {"success": False, "error": msg, "mt5_available": True, "error_code": error_code}

        _mt5_connected = True
        account = mt5.account_info()
        _mt5_account_info = account

        return {
            "success": True,
            "mt5_available": True,
            "account": {
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.margin_free,
                "leverage": account.leverage,
                "profit": account.profit,
                "margin_level": account.margin_level if account.margin > 0 else 0,
                "login": account.login,
                "name": account.name,
                "server": account.server,
                "currency": account.currency,
            },
        }
    except Exception as e:
        _mt5_connected = False
        return {"success": False, "error": str(e), "mt5_available": True}


def _disconnect_mt5():
    """Disconnect from MT5."""
    global _mt5_connected, _mt5_account_info
    if MT5_AVAILABLE and _mt5_connected:
        try:
            mt5.shutdown()
        except Exception:
            pass
    _mt5_connected = False
    _mt5_account_info = None


def _get_mt5_account() -> dict:
    """Get current MT5 account info."""
    global _mt5_account_info
    if not MT5_AVAILABLE or not _mt5_connected:
        return {"success": False, "error": "Not connected to MT5"}

    try:
        account = mt5.account_info()
        if account is None:
            return {"success": False, "error": "Failed to get account info"}
        _mt5_account_info = account

        return {
            "success": True,
            "account": {
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.margin_free,
                "leverage": account.leverage,
                "profit": account.profit,
                "margin_level": account.margin_level if account.margin > 0 else 0,
                "login": account.login,
                "name": account.name,
                "server": account.server,
                "currency": account.currency,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_mt5_positions() -> dict:
    """Get current MT5 positions."""
    if not MT5_AVAILABLE or not _mt5_connected:
        return {"success": False, "error": "Not connected to MT5"}

    try:
        positions = mt5.positions_get()
        if positions is None:
            return {"success": True, "positions": [], "orders": []}

        return {
            "success": True,
            "positions": [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": p.profit,
                    "swap": p.swap,
                    "comment": p.comment,
                    "time": str(p.time),
                }
                for p in positions
            ],
            "orders": [],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/trading/mt5-connect")
async def mt5_connect(req: MT5ConnectRequest):
    """Connect to a real MT5 account and return account info."""
    result = _connect_mt5(req.login, req.password, req.server)
    return result


@app.get("/api/trading/mt5-account")
async def mt5_account():
    """Get current MT5 account info (balance, equity, etc.)."""
    return _get_mt5_account()


@app.get("/api/trading/mt5-positions")
async def mt5_positions():
    """Get current MT5 open positions."""
    return _get_mt5_positions()


@app.post("/api/trading/mt5-disconnect")
async def mt5_disconnect():
    _disconnect_mt5()
    return {"success": True}


@app.get("/api/trading/mt5-status")
async def mt5_status():
    """Check if MT5 is connected and available."""
    return {
        "mt5_available": MT5_AVAILABLE,
        "connected": _mt5_connected,
        "account_login": _mt5_account_info.login if _mt5_account_info else None,
        "server": _mt5_account_info.server if _mt5_account_info else None,
    }


class MT5TradeRequest(BaseModel):
    symbol: str
    direction: str  # "BUY" or "SELL"
    volume: float
    sl: float
    tp: float
    comment: Optional[str] = "AI Cloud Trader"


class MT5CloseRequest(BaseModel):
    ticket: int


# ====================================================================
# MT5 Trade Execution
# ====================================================================


def _execute_mt5_trade(symbol: str, direction: str, volume: float, sl: float, tp: float, comment: str) -> dict:
    """Execute a market order on MT5."""
    global _mt5_connected

    if not MT5_AVAILABLE:
        return {
            "success": False,
            "error": "MT5 library not available on this server. Trade execution requires Windows with the MT5 desktop application installed.",
            "mt5_available": False,
        }

    if not _mt5_connected:
        return {"success": False, "error": "Not connected to MT5. Please reconnect."}

    try:
        # Get symbol info for tick and volume constraints
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"success": False, "error": f"Symbol {symbol} not found on broker"}

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return {"success": False, "error": f"Cannot select symbol {symbol}"}
            symbol_info = mt5.symbol_info(symbol)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "error": f"Cannot get tick data for {symbol}"}

        # Normalize volume to broker's step size
        volume_step = symbol_info.volume_step
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max

        volume = round(round(volume / volume_step) * volume_step, 8)
        volume = max(min_lot, min(max_lot, volume))

        # Determine order type and price
        if direction.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif direction.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            return {"success": False, "error": f"Invalid direction: {direction}. Use BUY or SELL."}

        # Determine filling mode
        filling_type = symbol_info.filling_mode
        if filling_type == 1:
            type_filling = mt5.ORDER_FILLING_FOK
        elif filling_type == 2:
            type_filling = mt5.ORDER_FILLING_IOC
        else:
            type_filling = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": comment or "AI Cloud Trader",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }

        print(f"[MT5 Trade] Sending: {symbol} {direction} {volume} lots @ {price} SL={sl} TP={tp}")
        result = mt5.order_send(request)

        if result is None:
            error_code = mt5.last_error()
            error_msg = _mt5_error_message(error_code)
            return {"success": False, "error": f"Order send failed: {error_msg}", "error_code": error_code}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = _mt5_error_message(result.retcode)
            return {
                "success": False,
                "error": error_msg,
                "retcode": result.retcode,
                "deal": result.deal,
                "order": result.order,
            }

        # Get the opened position
        position = None
        if result.deal > 0:
            positions = mt5.positions_get(ticket=result.order)
            if positions and len(positions) > 0:
                p = positions[0]
                position = {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": 0.0,
                    "swap": 0.0,
                    "comment": p.comment,
                    "time": str(p.time),
                }

        print(f"[MT5 Trade] SUCCESS: Deal #{result.deal} Order #{result.order} {symbol} {direction} {volume} @ {price}")

        return {
            "success": True,
            "deal": result.deal,
            "order": result.order,
            "price": result.price,
            "volume": result.volume,
            "comment": result.comment,
            "position": position,
        }

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def _close_mt5_position(ticket: int) -> dict:
    """Close an MT5 position by ticket."""
    if not MT5_AVAILABLE or not _mt5_connected:
        return {"success": False, "error": "Not connected to MT5"}

    try:
        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position #{ticket} not found"}

        pos = positions[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return {"success": False, "error": f"Cannot get tick for {pos.symbol}"}

        # Close with opposite direction
        if pos.type == 0:  # BUY
            close_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:  # SELL
            close_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        symbol_info = mt5.symbol_info(pos.symbol)
        filling_type = symbol_info.filling_mode
        if filling_type == 1:
            type_filling = mt5.ORDER_FILLING_FOK
        elif filling_type == 2:
            type_filling = mt5.ORDER_FILLING_IOC
        else:
            type_filling = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Close AI Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }

        print(f"[MT5 Close] Closing position #{ticket} {pos.symbol} {pos.volume} lots @ {price}")
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_code = result.retcode if result else mt5.last_error()
            return {"success": False, "error": _mt5_error_message(error_code), "retcode": error_code}

        print(f"[MT5 Close] SUCCESS: Deal #{result.deal} closed position #{ticket}")
        return {
            "success": True,
            "deal": result.deal,
            "order": result.order,
            "price": result.price,
            "profit": pos.profit,
        }

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def _mt5_error_message(code: int) -> str:
    """Map MT5 error codes to human-readable messages."""
    messages = {
        10004: "Requote",
        10006: "Request rejected",
        10007: "Request canceled by trader",
        10008: "Order placed",
        10009: "Request executed",
        10010: "Request partially executed",
        10011: "Request processing error",
        10012: "Request timed out",
        10013: "Invalid request",
        10014: "Invalid volume",
        10015: "Invalid price",
        10016: "Invalid stops",
        10017: "Trade disabled",
        10018: "Market closed",
        10019: "Not enough money",
        10020: "Prices changed",
        10021: "No quotes to process request",
        10022: "Invalid order expiration",
        10023: "Order state changed",
        10024: "Too many requests",
        10025: "No changes in request",
        10026: "Autotrading disabled by server",
        10027: "Autotrading disabled by client",
        10028: "Request locked for processing",
        10029: "Order or position frozen",
        10030: "Invalid order filling",
        10031: "No connection with trade server",
        10032: "Operation allowed only for live accounts",
        10033: "Pending orders limit reached",
        10034: "Volume limit for symbol reached",
        10035: "Incorrect or prohibited order type",
        10036: "Position with specified ID already closed",
        10038: "Close volume exceeds current position volume",
        10039: "Close order already exists",
        10040: "Positions limit reached",
        10041: "Pending order activation rejected",
        10042: "Only long positions allowed",
        10043: "Only short positions allowed",
        10044: "Only position close allowed",
        10045: "Position close allowed only by FIFO rule",
    }
    return messages.get(code, f"MT5 error {code}")


@app.post("/api/trading/mt5-trade")
async def mt5_trade(req: MT5TradeRequest):
    """Place a market order on MT5."""
    result = _execute_mt5_trade(
        symbol=req.symbol,
        direction=req.direction,
        volume=req.volume,
        sl=req.sl,
        tp=req.tp,
        comment=req.comment,
    )
    return result


@app.post("/api/trading/mt5-close-position")
async def mt5_close_position(req: MT5CloseRequest):
    """Close an MT5 position by ticket number."""
    result = _close_mt5_position(req.ticket)
    return result


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
        "brokers": ["Paper Trading", "OctaFX", "Exness", "Headway"],
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
