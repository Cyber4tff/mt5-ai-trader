from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent to path so imports work when running ``python app/main.py``
sys.path.insert(0, str(Path(__file__).parent.parent))

from mt5_connector.connector import MT5Connector
from engine.trading_engine import TradingEngine
from config.settings import settings
from utils.logging import setup_logging, logger

# Setup logging
setup_logging(settings.log_level, settings.log_file)

app = FastAPI(
    title='MT5 AI Trader - Naked Forex Engine',
    description='AI-powered MT5 trading with multi-timeframe analysis, Naked Forex strategies, and strict risk management.',
    version='2.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ====================================================================
# Session Manager
# ====================================================================


class SessionManager:
    """Manages MT5 connections and trading engines per session.

    FIX: Replaces the original global mutable dict.
    Each session now has its own connector, engine, and auto-trade task.
    """

    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._auto_tasks: Dict[str, asyncio.Task] = {}

    def create_session(self, session_id: str, connector: MT5Connector) -> None:
        engine = TradingEngine(connector)
        self._sessions[session_id] = {
            'connector': connector,
            'engine': engine,
            'created_at': datetime.now(),
        }

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def get_connector(self, session_id: str) -> Optional[MT5Connector]:
        session = self.get_session(session_id)
        return session['connector'] if session else None

    def get_engine(self, session_id: str) -> Optional[TradingEngine]:
        session = self.get_session(session_id)
        return session['engine'] if session else None

    def remove_session(self, session_id: str) -> None:
        self.cancel_auto_trade(session_id)
        session = self._sessions.pop(session_id, None)
        if session:
            session['connector'].disconnect()

    def set_auto_task(self, session_id: str, task: asyncio.Task) -> None:
        self.cancel_auto_trade(session_id)  # Cancel existing first
        self._auto_tasks[session_id] = task

    def cancel_auto_trade(self, session_id: str) -> None:
        task = self._auto_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())


session_manager = SessionManager()


# ====================================================================
# Request / Response Models
# ====================================================================


class BrokerCredentials(BaseModel):
    broker: str = 'exness'
    account_type: str = 'demo'
    login: int
    password: str
    server: Optional[str] = None


class TradeRequest(BaseModel):
    symbol: str = 'XAUUSD'
    order_type: str = Field(default='BUY', pattern='^(BUY|SELL)$')
    volume: float = Field(default=0.01, gt=0)
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = 'AI Naked Forex'


class ScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    entry_timeframe: str = Field(default='H1', pattern='^(M5|M15|M30|H1|H4|D1)$')


class ModifyRequest(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None


class AutoTradeRequest(BaseModel):
    enabled: bool = True
    interval_minutes: int = Field(default=15, ge=1, le=240)
    symbols: Optional[List[str]] = None


# ====================================================================
# Connection Endpoints
# ====================================================================


@app.post('/connect')
async def connect_mt5(creds: BrokerCredentials):
    if creds.broker not in settings.brokers:
        raise HTTPException(
            400,
            f'Broker {creds.broker} not supported. Use: {list(settings.brokers.keys())}',
        )

    conn = MT5Connector(broker=creds.broker, account_type=creds.account_type)
    success = conn.connect(
        login=creds.login,
        password=creds.password,
        server=creds.server,
    )
    if not success:
        raise HTTPException(
            400,
            'Failed to connect to MT5. Check credentials, server name, and ensure MT5 terminal is running.',
        )

    session_id = f'{creds.broker}_{creds.login}_{datetime.now().strftime("%H%M%S")}'
    session_manager.create_session(session_id, conn)

    account = conn.get_account_info()
    logger.info(
        'New session {} connected. Balance: {}',
        session_id,
        account.balance if account else 'N/A',
    )

    return {
        'success': True,
        'session_id': session_id,
        'broker': creds.broker,
        'server': account.server if account else 'unknown',
        'mode': settings.trading_mode,
        'account': {
            'balance': account.balance if account else 0,
            'equity': account.equity if account else 0,
            'leverage': account.leverage if account else 0,
            'margin_level': round(account.margin_level, 2) if account else 0,
            'free_margin': account.free_margin if account else 0,
        },
    }


@app.post('/disconnect/{session_id}')
async def disconnect_mt5(session_id: str):
    if not session_manager.get_session(session_id):
        raise HTTPException(404, 'Session not found')
    session_manager.remove_session(session_id)
    logger.info('Session {} disconnected', session_id)
    return {'success': True, 'message': 'Disconnected from MT5'}


@app.get('/sessions')
async def list_sessions():
    sessions = session_manager.list_sessions()
    return {'sessions': sessions, 'count': len(sessions)}


# ====================================================================
# Account Endpoints
# ====================================================================


@app.get('/account/{session_id}')
async def get_account(session_id: str):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')
    info = conn.get_account_info()
    if not info:
        raise HTTPException(500, 'Failed to get account info')
    positions = conn.get_positions()
    orders = conn.get_orders()
    return {
        'session_id': session_id,
        'balance': info.balance,
        'equity': info.equity,
        'margin': info.margin,
        'free_margin': info.free_margin,
        'leverage': info.leverage,
        'profit': info.profit,
        'margin_level': round(info.margin_level, 2),
        'open_positions': len(positions),
        'pending_orders': len(orders),
        'positions': positions,
        'orders': orders,
    }


# ====================================================================
# Symbol Info
# ====================================================================


@app.get('/symbol/{session_id}/{symbol}')
async def get_symbol_info(session_id: str, symbol: str):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')
    info = conn.get_symbol_spec(symbol)
    if not info:
        raise HTTPException(404, f'Symbol {symbol} not found')
    return {
        'name': info.name,
        'bid': info.bid,
        'ask': info.ask,
        'spread': info.spread,
        'point': info.point,
        'digits': info.digits,
        'trade_allowed': info.trade_allowed,
        'volume_min': info.volume_min,
        'volume_max': info.volume_max,
        'volume_step': info.volume_step,
        'tick_value': info.tick_value,
        'tick_size': info.tick_size,
        'volume_contract_size': info.volume_contract_size,
    }


# ====================================================================
# Scanning / Analysis
# ====================================================================


@app.post('/scan/{session_id}')
async def scan_markets(session_id: str, request: ScanRequest):
    """FIX: session_id is now a path parameter, not a broken query param."""
    engine = session_manager.get_engine(session_id)
    if not engine:
        raise HTTPException(404, 'Session not found')

    symbols = request.symbols or settings.trading_symbols
    results = engine.scan_all(symbols)

    # Format response
    formatted = []
    for r in results:
        entry: Dict[str, Any] = {
            'symbol': r['symbol'],
            'confluence': r.get('confluence'),
            'decisions_count': len(r.get('decisions', [])),
            'actionable': r.get('actionable') is not None,
            'errors': r.get('errors', []),
        }
        if r.get('actionable'):
            entry['actionable_signal'] = r['actionable']
        if r.get('risk_failures'):
            entry['risk_failures'] = r['risk_failures']
        # Include per-timeframe analysis summary
        analyses = r.get('analyses', {})
        entry['timeframes'] = {}
        for tf, analysis in analyses.items():
            entry['timeframes'][tf] = {
                'trend': analysis.trend.value,
                'bias': analysis.bias.value,
                'atr': round(analysis.atr, 5) if analysis.atr else None,
                'volatility': analysis.volatility_regime,
                'signals_count': len(analysis.signals),
                'structure_breaks': len(analysis.structure_breaks),
                'sr_levels': len(analysis.sr_levels),
            }
        formatted.append(entry)

    logger.info('Scan completed: {} symbols scanned', len(formatted))
    return {'results': formatted, 'scan_time': datetime.now().isoformat()}


# ====================================================================
# Manual Trading
# ====================================================================


@app.post('/trade/{session_id}')
async def place_trade(session_id: str, trade: TradeRequest):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')

    if trade.symbol not in settings.trading_symbols:
        raise HTTPException(
            400,
            f'Symbol {trade.symbol} not in allowed list: {settings.trading_symbols}',
        )

    # MANDATORY: Stop loss
    if trade.sl is None:
        raise HTTPException(400, 'Stop loss is MANDATORY. Trade rejected.')

    # MANDATORY: Take profit
    if trade.tp is None:
        raise HTTPException(400, 'Take profit is MANDATORY. Trade rejected.')

    # Check max concurrent trades
    positions = conn.get_positions()
    if len(positions) >= settings.max_open_positions:
        raise HTTPException(
            400,
            f'Max concurrent trades ({settings.max_open_positions}) reached',
        )

    # Check spread
    spread = conn.get_current_spread_points(trade.symbol)
    if spread > settings.max_spread_points:
        raise HTTPException(
            400,
            f'Spread too high: {spread} pts (max: {settings.max_spread_points})',
        )

    result = conn.place_market_order(
        symbol=trade.symbol,
        order_type=trade.order_type,
        volume=trade.volume,
        sl=trade.sl,
        tp=trade.tp,
        comment=trade.comment,
    )

    if not result.success:
        raise HTTPException(400, result.error)

    logger.info(
        'Manual trade: {} {} @ {} (Ticket: {})',
        trade.symbol, trade.order_type, result.price, result.ticket,
    )
    return {
        'success': True,
        'ticket': result.ticket,
        'price': result.price,
        'symbol': trade.symbol,
        'type': trade.order_type,
        'volume': trade.volume,
    }


@app.post('/close/{session_id}/{ticket:int}')
async def close_trade(session_id: str, ticket: int):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')
    result = conn.close_position(ticket)
    if not result.success:
        raise HTTPException(400, result.error)
    return {'success': True, 'ticket': ticket, 'closed_price': result.price}


@app.post('/modify/{session_id}/{ticket:int}')
async def modify_trade(session_id: str, ticket: int, mod: ModifyRequest):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')
    result = conn.modify_position(ticket, sl=mod.sl, tp=mod.tp)
    if not result.success:
        raise HTTPException(400, result.error)
    return {'success': True, 'ticket': ticket, 'new_sl': mod.sl, 'new_tp': mod.tp}


@app.get('/positions/{session_id}')
async def get_positions(session_id: str):
    conn = session_manager.get_connector(session_id)
    if not conn:
        raise HTTPException(404, 'Session not found')
    return {'positions': conn.get_positions(), 'orders': conn.get_orders()}


# ====================================================================
# Auto Trading
# ====================================================================


async def _auto_trade_loop(session_id: str, interval_minutes: int, symbols: List[str]):
    """Auto-trade loop for a specific session."""
    engine = session_manager.get_engine(session_id)
    if not engine:
        return

    logger.info(
        'Auto-trade loop started for {} (interval: {}min)',
        session_id, interval_minutes,
    )

    while True:
        try:
            if not engine.connector.is_connected():
                logger.warning(
                    '{}: MT5 disconnected, attempting reconnect...',
                    session_id,
                )
                await asyncio.sleep(60)
                continue

            results = engine.scan_all(symbols)
            for r in results:
                if r.get('actionable'):
                    trade_result = engine.execute_trade(r['actionable'])
                    r['trade_result'] = trade_result
                    if trade_result.get('success'):
                        logger.info(
                            'Auto-trade executed: {} {}',
                            trade_result['symbol'], trade_result['direction'],
                        )

            await asyncio.sleep(interval_minutes * 60)

        except asyncio.CancelledError:
            logger.info('Auto-trade loop cancelled for {}', session_id)
            break
        except Exception as e:
            logger.error('Auto-trade error for {}: {}', session_id, e)
            await asyncio.sleep(60)


@app.post('/auto-trade/{session_id}')
async def toggle_auto_trade(session_id: str, request: AutoTradeRequest):
    if not session_manager.get_session(session_id):
        raise HTTPException(404, 'Session not found')

    symbols = request.symbols or settings.trading_symbols

    if request.enabled:
        task = asyncio.create_task(
            _auto_trade_loop(session_id, request.interval_minutes, symbols)
        )
        session_manager.set_auto_task(session_id, task)
        logger.info('Auto-trade enabled for {}', session_id)
        return {
            'success': True,
            'auto_trade': True,
            'interval': request.interval_minutes,
            'symbols': symbols,
        }
    else:
        session_manager.cancel_auto_trade(session_id)
        logger.info('Auto-trade disabled for {}', session_id)
        return {'success': True, 'auto_trade': False}


# ====================================================================
# Risk & Status
# ====================================================================


@app.get('/risk-status/{session_id}')
async def risk_status(session_id: str):
    engine = session_manager.get_engine(session_id)
    if not engine:
        raise HTTPException(404, 'Session not found')
    return engine.risk_manager.get_daily_summary()


@app.get('/ai-status')
async def ai_status():
    return {
        'strategy': 'Naked Forex Price Action + Market Structure',
        'patterns': ['Big Shadow', 'Kangaroo Tail', 'Last Kiss', 'Double Hit'],
        'structure_analysis': ['BOS', 'CHOCH', 'Liquidity Sweeps', 'Swing Points'],
        'mtf_timeframes': settings.mtf_timeframes,
        'symbols_focus': settings.trading_symbols,
        'brokers': list(settings.brokers.keys()),
        'confidence_threshold': settings.ai_confidence_threshold,
        'high_confidence': settings.ai_high_confidence,
        'risk_per_trade': settings.risk_per_trade,
        'max_daily_loss_pct': settings.max_daily_drawdown_pct,
        'max_consecutive_losses': settings.max_consecutive_losses,
        'max_open_positions': settings.max_open_positions,
        'max_trades_per_day': settings.max_trades_per_day,
        'max_spread_points': settings.max_spread_points,
        'min_risk_reward': settings.min_risk_reward,
        'mode': settings.trading_mode,
        'trailing_stop': settings.trailing_stop_enabled,
    }


# ====================================================================
# WebSocket
# ====================================================================


@app.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            conn = session_manager.get_connector(session_id)
            if conn and conn.is_connected():
                account = conn.get_account_info()
                positions = conn.get_positions()
                await websocket.send_json({
                    'type': 'update',
                    'timestamp': datetime.now().isoformat(),
                    'account': {
                        'balance': account.balance if account else 0,
                        'equity': account.equity if account else 0,
                        'profit': account.profit if account else 0,
                        'margin_level': round(account.margin_level, 2) if account else 0,
                    },
                    'positions': positions,
                })
            else:
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Session not found or disconnected',
                })
                break
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info('WebSocket disconnected: {}', session_id)


# ====================================================================
# Shutdown
# ====================================================================


@app.on_event('shutdown')
async def shutdown_event():
    for sid in session_manager.list_sessions():
        session_manager.remove_session(sid)
    logger.info('All sessions closed. Shutdown complete.')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
