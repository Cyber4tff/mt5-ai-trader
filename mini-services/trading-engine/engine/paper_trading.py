from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from engine.data_fetcher import fetch_current_price, invalidate_cache
from engine.models import (
    PaperAccount,
    PaperPosition,
    PatternName,
    SignalType,
    TradingSession,
)
from engine.settings import settings


# ====================================================================
# Position Sizing
# ====================================================================


def calculate_position_size(
    session: TradingSession,
    symbol: str,
    entry_price: float,
    sl_price: float,
    direction: str,
) -> float:
    """Calculate lot size based on risk %, account balance, and SL distance.

    Simplified formula for paper trading:
        risk_amount = balance * risk_per_trade
        sl_distance = |entry - SL| in price units
        pip_value_per_lot = symbol's pip value
        lots = risk_amount / (sl_distance_in_pips * pip_value_per_lot)
    """
    spec = settings.SYMBOL_SPECS.get(symbol, {})
    pip_value = spec.get("pip_value", 10.0)
    lot_step = spec.get("trade_lot_step", 0.01)
    lot_min = spec.get("trade_lot_min", 0.01)
    lot_max = spec.get("trade_lot_max", 100.0)
    digits = spec.get("digits", 5)

    risk_amount = session.balance * settings.risk_per_trade
    sl_distance = abs(entry_price - sl_price)

    if sl_distance == 0:
        return lot_min

    # Convert SL distance to approximate pips
    point = spec.get("point", 0.00001)
    sl_pips = sl_distance / (point * 10) if point > 0 else sl_distance

    if sl_pips == 0:
        return lot_min

    lots = risk_amount / (sl_pips * pip_value)

    # Round down to lot step
    steps = int(lots / lot_step)
    lots = steps * lot_step

    # Clamp to min/max
    lots = max(lot_min, min(lots, lot_max))

    return round(lots, 2)


# ====================================================================
# Paper Trading Engine
# ====================================================================


class PaperTradingEngine:
    """Manages paper trading positions, P&L, and risk limits.

    All positions are virtual. Uses real market prices for P&L.
    """

    def __init__(self):
        self.sessions: Dict[str, TradingSession] = {}

    def create_session(
        self,
        broker: str = "Paper Trading",
        account_type: str = "paper",
        login: int = 0,
        password: str = "",
        balance: float = None,
        leverage: int = 100,
    ) -> TradingSession:
        """Create a new paper trading session."""
        if balance is None:
            balance = settings.default_balance

        session = TradingSession(
            broker=broker,
            account_type=account_type,
            login=login,
            password=password,
            balance=balance,
            leverage=leverage,
        )

        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[TradingSession]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def update_positions(self, session: TradingSession):
        """Update current prices for all open positions and check SL/TP hits."""
        if not session.positions:
            return

        for pos in list(session.positions):
            price = fetch_current_price(pos.symbol)
            if price is None:
                continue

            pos.current_price = price
            session.price_cache[pos.symbol] = price

            # Check SL/TP hits
            if pos.type == "BUY":
                if pos.sl > 0 and price <= pos.sl:
                    self._close_position(session, pos, price, "SL Hit")
                elif pos.tp > 0 and price >= pos.tp:
                    self._close_position(session, pos, price, "TP Hit")
            elif pos.type == "SELL":
                if pos.sl > 0 and price >= pos.sl:
                    self._close_position(session, pos, price, "SL Hit")
                elif pos.tp > 0 and price <= pos.tp:
                    self._close_position(session, pos, price, "TP Hit")

    def open_position(
        self,
        session: TradingSession,
        symbol: str,
        direction: str,
        entry: float,
        sl: float,
        tp: float,
        confidence: float = 0.7,
        reason: str = "",
    ) -> Optional[PaperPosition]:
        """Open a new paper position."""
        session.reset_daily_risk()

        # Risk checks
        if len(session.positions) >= settings.max_open_positions:
            return None
        if session.daily_risk.trades_count >= settings.max_trades_per_day:
            return None
        if session.daily_risk.consecutive_losses >= settings.max_consecutive_losses:
            return None
        if session.daily_risk.realized_pnl <= -session.initial_balance * settings.max_daily_drawdown_pct:
            return None

        # Get current price for entry
        current_price = fetch_current_price(symbol)
        if current_price is None:
            current_price = entry

        # Calculate position size
        volume = calculate_position_size(session, symbol, current_price, sl, direction)

        pos = PaperPosition(
            ticket=session.next_ticket,
            symbol=symbol,
            type=direction.upper(),
            volume=volume,
            open_price=current_price,
            current_price=current_price,
            sl=sl,
            tp=tp,
            open_time=datetime.utcnow().isoformat() + "Z",
            comment=reason[:50] if reason else f"AI {confidence:.0%}",
        )

        session.next_ticket += 1
        session.positions.append(pos)
        session.daily_risk.trades_count += 1

        # Deduct estimated margin from available balance conceptually
        session.price_cache[symbol] = current_price

        print(f"[PaperTrade] OPENED #{pos.ticket} {pos.type} {symbol} {volume} lots @ {current_price} SL={sl} TP={tp}")
        return pos

    def close_position_by_ticket(
        self, session: TradingSession, ticket: int
    ) -> Optional[Dict]:
        """Close a position by ticket number."""
        pos = None
        for p in session.positions:
            if p.ticket == ticket:
                pos = p
                break
        if pos is None:
            return None

        price = fetch_current_price(pos.symbol)
        if price is None:
            price = pos.current_price

        return self._close_position(session, pos, price, "Manual close")

    def _close_position(
        self,
        session: TradingSession,
        pos: PaperPosition,
        close_price: float,
        reason: str,
    ) -> Dict:
        """Internal: close a position and update P&L tracking."""
        # Calculate final P&L
        spec = settings.SYMBOL_SPECS.get(pos.symbol, {})
        tick_val = spec.get("tick_value", 1.0)
        point = spec.get("point", 0.00001)

        if point > 0:
            ticks_diff = (close_price - pos.open_price) / point
            if pos.type == "SELL":
                ticks_diff = -ticks_diff
            pnl = round(ticks_diff * tick_val * pos.volume, 2)
        else:
            pnl = 0.0

        # Update balance
        session.balance = round(session.balance + pnl, 2)

        # Update daily risk tracking
        session.daily_risk.realized_pnl = round(session.daily_risk.realized_pnl + pnl, 2)
        if pnl < 0:
            session.daily_risk.consecutive_losses += 1
        else:
            session.daily_risk.consecutive_losses = 0
        session.daily_risk.remaining_trades = max(0, settings.max_trades_per_day - session.daily_risk.trades_count)
        session.daily_risk.remaining_loss_limit = round(
            session.initial_balance * settings.max_daily_drawdown_pct + session.daily_risk.realized_pnl, 2
        )

        # Record closed trade
        closed = {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": pos.type,
            "volume": pos.volume,
            "open_price": pos.open_price,
            "close_price": close_price,
            "pnl": pnl,
            "reason": reason,
            "time": datetime.utcnow().isoformat() + "Z",
        }
        session.closed_today.append(closed)

        # Remove from positions
        session.positions = [p for p in session.positions if p.ticket != pos.ticket]

        print(f"[PaperTrade] CLOSED #{pos.ticket} {pos.type} {pos.symbol} P&L: ${pnl:+.2f} ({reason})")

        return closed

    def get_account_data(self, session: TradingSession) -> Dict:
        """Get full account data including positions."""
        self.update_positions(session)
        account = session.get_account()

        return {
            **account.to_dict(),
            "positions": [p.to_dict() for p in session.positions],
            "orders": [],
        }

    def get_risk_status(self, session: TradingSession) -> Dict:
        """Get daily risk status."""
        session.reset_daily_risk()
        return session.daily_risk.to_dict()
