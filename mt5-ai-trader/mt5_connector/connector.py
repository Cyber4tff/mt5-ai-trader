"""MT5 connector – low-level bridge to the MetaTrader 5 terminal.

This module provides :class:`MT5Connector`, :class:`AccountInfo`,
:class:`TradeResult`, and re-exports :class:`~models.market.SymbolSpec`.

All contract specifications (point, tick_value, tick_size,
volume_contract_size, etc.) are fetched from the MT5 terminal at
runtime – nothing is hardcoded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import MetaTrader5 as mt5
import pandas as pd

from config.settings import settings
from models.market import SymbolSpec
from utils.helpers import get_filling_mode, normalize_price, normalize_volume
from utils.logging import logger


# ====================================================================
# Data classes
# ====================================================================


@dataclass
class AccountInfo:
    """Snapshot of the currently logged-in MT5 account."""

    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: int
    profit: float
    margin_level: float
    currency: str
    login: int
    server: str
    name: str


@dataclass
class TradeResult:
    """Result of an order request sent to MT5."""

    success: bool
    ticket: Optional[int] = None
    error: Optional[str] = None
    price: Optional[float] = None
    request_dict: Optional[dict] = field(default=None, repr=False)


# Re-export SymbolSpec so consumers can do ``from mt5_connector import SymbolSpec``
__all__ = [
    "MT5Connector",
    "AccountInfo",
    "TradeResult",
    "SymbolSpec",
]


# ====================================================================
# Timeframe mapping
# ====================================================================

_TIMEFRAME_MAP: Dict[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN": mt5.TIMEFRAME_MN1,
}


# ====================================================================
# MT5Connector
# ====================================================================


class MT5Connector:
    """High-level wrapper around the MetaTrader5 Python API.

    Parameters
    ----------
    broker : str
        Key into :pydata:`settings.brokers` (default ``"exness"``).
    account_type : str
        Sub-key under the broker entry (``"demo"`` or ``"real"``).
    """

    def __init__(self, broker: str = "exness", account_type: str = "demo") -> None:
        self.broker = broker
        self.account_type = account_type
        self.broker_config = settings.brokers.get(broker, {})
        self.connected: bool = False
        self._account_info: Optional[AccountInfo] = None

    # ----------------------------------------------------------------
    # Connection lifecycle
    # ----------------------------------------------------------------

    def connect(
        self,
        login: int,
        password: str,
        server: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> bool:
        """Initialise the MT5 library and log in with retry logic.

        Parameters
        ----------
        login :
            Account number.
        password :
            Trading password.
        server :
            Broker server name.  If *None*, derived from
            ``settings.brokers[self.broker][self.account_type]``.
        max_retries :
            Maximum login attempts.
        retry_delay :
            Seconds to sleep between retries.

        Returns
        -------
        bool
            ``True`` if successfully connected.
        """
        if server is None:
            servers = self.broker_config.get("servers", {})
            server = servers.get(self.account_type)
            if server is None:
                logger.error(
                    "No server configured for broker=%s account_type=%s",
                    self.broker,
                    self.account_type,
                )
                return False

        mt5_path = settings.mt5_path or None

        # If MT5 is already initialised, shut it down first so we can
        # re-initialise with a (potentially different) path.
        if mt5.initialize():
            logger.info("MT5 already initialised – shutting down before re-init")
            mt5.shutdown()

        if not mt5.initialize(path=mt5_path):
            logger.error("mt5.initialize() failed: {}", mt5.last_error())
            return False

        # Retry loop for login.
        for attempt in range(1, max_retries + 1):
            logger.info(
                "Login attempt {}/{} – login={} server={}",
                attempt,
                max_retries,
                login,
                server,
            )
            authorized = mt5.login(login=int(login), password=password, server=server)
            if authorized:
                self.connected = True
                self._account_info = self.get_account_info()
                logger.info(
                    "Logged in successfully to {} (account {})",
                    server,
                    login,
                )
                return True

            logger.warning(
                "Login attempt {}/{} failed: {}",
                attempt,
                max_retries,
                mt5.last_error(),
            )
            if attempt < max_retries:
                logger.info("Retrying in {} seconds…", retry_delay)
                time.sleep(retry_delay)

        # All retries exhausted.
        logger.error("All {} login attempts failed.", max_retries)
        mt5.shutdown()
        return False

    def disconnect(self) -> None:
        """Shut down the MT5 connection."""
        mt5.shutdown()
        self.connected = False
        self._account_info = None
        logger.info("Disconnected from MT5")

    def reconnect(
        self,
        login: int,
        password: str,
        server: Optional[str] = None,
    ) -> bool:
        """Disconnect and then connect again (with retry)."""
        self.disconnect()
        return self.connect(login=login, password=password, server=server)

    def is_connected(self) -> bool:
        """Return ``True`` if the terminal is reachable *and* we are logged in."""
        return self.connected and mt5.terminal_info() is not None

    # ----------------------------------------------------------------
    # Account information
    # ----------------------------------------------------------------

    def get_account_info(self) -> Optional[AccountInfo]:
        """Fetch current account information from MT5.

        Returns ``None`` if not connected or if MT5 returns no data.
        """
        if not self.is_connected():
            logger.warning("get_account_info() called but not connected")
            return None

        info = mt5.account_info()
        if info is None:
            logger.error("mt5.account_info() returned None: {}", mt5.last_error())
            return None

        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            leverage=info.leverage,
            profit=info.profit,
            margin_level=info.margin_level,
            currency=info.currency,
            login=info.login,
            server=info.server,
            name=info.name,
        )

    # ----------------------------------------------------------------
    # Symbol specification
    # ----------------------------------------------------------------

    def get_symbol_spec(self, symbol: str) -> Optional[SymbolSpec]:
        """Build a :class:`SymbolSpec` entirely from live MT5 data.

        If ``mt5.symbol_info()`` is ``None`` (symbol not found in
        Market Watch), a warning is logged and ``None`` is returned.
        """
        if not self.is_connected():
            logger.warning("get_symbol_spec() called but not connected")
            return None

        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            # Fallback: try tick-level info to at least log something useful.
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                logger.warning(
                    "symbol_info('%s') returned None but tick data is available. "
                    "The symbol may not be in Market Watch.",
                    symbol,
                )
            else:
                logger.warning(
                    "symbol_info('%s') and symbol_info_tick('%s') both returned None.",
                    symbol,
                    symbol,
                )
            return None

        # Current tick for live bid/ask.
        tick = mt5.symbol_info_tick(symbol)
        bid = tick.bid if tick else sym_info.bid
        ask = tick.ask if tick else sym_info.ask

        filling_mode = get_filling_mode(sym_info)

        return SymbolSpec(
            name=sym_info.name,
            bid=bid,
            ask=ask,
            spread=sym_info.spread,
            point=sym_info.point,
            digits=sym_info.digits,
            trade_allowed=bool(sym_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED),
            volume_min=sym_info.volume_min,
            volume_max=sym_info.volume_max,
            volume_step=sym_info.volume_step,
            tick_value=sym_info.tick_value,
            tick_size=sym_info.tick_size,
            volume_contract_size=sym_info.volume_contract_size,
            trade_mode=sym_info.trade_mode,
            filling_mode=filling_mode,
        )

    # ----------------------------------------------------------------
    # OHLCV data
    # ----------------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "H1",
        bars: int = 500,
    ) -> Optional[pd.DataFrame]:
        """Retrieve OHLCV bars and return them as a DataFrame.

        Parameters
        ----------
        symbol :
            Instrument name (e.g. ``"BTCUSD"``).
        timeframe :
            One of ``M1 M5 M15 M30 H1 H4 D1 W1 MN``.
        bars :
            Number of bars to fetch.

        Returns
        -------
        pd.DataFrame | None
            DataFrame with a ``datetime`` index and columns:
            ``open, high, low, close, tick_volume, spread``.
            Returns ``None`` on failure.
        """
        tf = _TIMEFRAME_MAP.get(timeframe.upper())
        if tf is None:
            logger.error("Unknown timeframe '{}'. Valid: {}", timeframe, list(_TIMEFRAME_MAP))
            return None

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None or len(rates) == 0:
            logger.error(
                "copy_rates_from_pos('%s', %s, 0, %s) failed: {}",
                symbol,
                timeframe,
                bars,
                mt5.last_error(),
            )
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        # Keep only the columns we want.
        df = df[["open", "high", "low", "close", "tick_volume", "spread"]]
        return df

    # ----------------------------------------------------------------
    # Spread
    # ----------------------------------------------------------------

    def get_current_spread_points(self, symbol: str) -> int:
        """Return the current spread in points for *symbol*.

        Returns ``999_999`` if the information is not available.
        """
        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            return 999_999
        return int(sym_info.spread)

    # ----------------------------------------------------------------
    # Order placement
    # ----------------------------------------------------------------

    def place_market_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
        deviation: int = 20,
    ) -> TradeResult:
        """Place a market order (BUY or SELL).

        All prices and volumes are normalised against live symbol
        specifications – nothing is hardcoded.

        Parameters
        ----------
        symbol :
            Instrument to trade.
        order_type :
            ``"BUY"`` or ``"SELL"`` (case-insensitive).
        volume :
            Desired lot size (will be normalised).
        sl, tp :
            Stop-loss / take-profit prices (optional).
        comment :
            Order comment string.
        deviation :
            Maximum slippage in points.

        Returns
        -------
        TradeResult
            Details of the order outcome.
        """
        # --- 1. Get live symbol spec ---
        spec = self.get_symbol_spec(symbol)
        if spec is None:
            return TradeResult(
                success=False,
                error=f"Cannot retrieve symbol spec for '{symbol}'",
            )

        # --- 2. Determine filling mode from raw MT5 symbol_info ---
        sym_info_raw = mt5.symbol_info(symbol)
        filling_mode = get_filling_mode(sym_info_raw) if sym_info_raw else mt5.ORDER_FILLING_RETURN

        # --- 3. Normalise volume ---
        norm_volume = normalize_volume(
            volume=volume,
            volume_step=spec.volume_step,
            volume_min=spec.volume_min,
            volume_max=spec.volume_max,
        )

        # --- 4. Determine order direction constant and entry price ---
        order_type_upper = order_type.upper().strip()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return TradeResult(
                success=False,
                error=f"Cannot get tick data for '{symbol}'",
            )

        if order_type_upper == "BUY":
            mt5_order_type = mt5.ORDER_TYPE_BUY
            price = normalize_price(tick.ask, spec.digits)
        elif order_type_upper == "SELL":
            mt5_order_type = mt5.ORDER_TYPE_SELL
            price = normalize_price(tick.bid, spec.digits)
        else:
            return TradeResult(
                success=False,
                error=f"Invalid order_type '{order_type}'. Must be BUY or SELL.",
            )

        # --- 5. Normalise SL / TP ---
        norm_sl = normalize_price(sl, spec.digits) if sl is not None else 0.0
        norm_tp = normalize_price(tp, spec.digits) if tp is not None else 0.0

        # --- 6. Build the request dict ---
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": norm_volume,
            "type": mt5_order_type,
            "price": price,
            "deviation": deviation,
            "magic": settings.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
            "sl": norm_sl,
            "tp": norm_tp,
        }

        logger.info(
            "Sending {} {} @ {}  vol={}  SL={}  TP={}  filling={}",
            order_type_upper,
            symbol,
            price,
            norm_volume,
            norm_sl if sl is not None else "None",
            norm_tp if tp is not None else "None",
            filling_mode,
        )

        # --- 7. Send the order ---
        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            logger.error("order_send returned None: {}", err)
            return TradeResult(
                success=False,
                error=f"order_send returned None: {err}",
                request_dict=request,
            )

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                "Order FAILED – retcode={} comment='{}' deal={}",
                result.retcode,
                result.comment,
                result.deal,
            )
            return TradeResult(
                success=False,
                ticket=result.order,
                error=f"retcode={result.retcode}: {result.comment}",
                price=result.price,
                request_dict=request,
            )

        logger.info(
            "Order FILLED – ticket={} deal={} price={} vol={}",
            result.order,
            result.deal,
            result.price,
            result.volume,
        )
        return TradeResult(
            success=True,
            ticket=result.order,
            price=result.price,
            request_dict=request,
        )

    # ----------------------------------------------------------------
    # Position management
    # ----------------------------------------------------------------

    def close_position(self, ticket: int) -> TradeResult:
        """Close an open position by its ticket number.

        Parameters
        ----------
        ticket :
            Position ticket to close.

        Returns
        -------
        TradeResult
            Outcome of the close request.
        """
        positions = mt5.positions_get(ticket=ticket)
        if positions is None or len(positions) == 0:
            return TradeResult(
                success=False,
                error=f"Position ticket {ticket} not found",
            )

        pos = positions[0]
        symbol = pos.symbol

        # Determine the opposite order type.
        if pos.type == mt5.POSITION_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
        else:
            close_type = mt5.ORDER_TYPE_BUY

        # Get symbol spec for filling mode and price.
        spec = self.get_symbol_spec(symbol)
        if spec is None:
            return TradeResult(
                success=False,
                error=f"Cannot retrieve spec for '{symbol}' to close position {ticket}",
            )

        sym_info_raw = mt5.symbol_info(symbol)
        filling_mode = get_filling_mode(sym_info_raw) if sym_info_raw else mt5.ORDER_FILLING_RETURN

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return TradeResult(
                success=False,
                error=f"Cannot get tick for '{symbol}'",
            )

        price = (
            normalize_price(tick.bid, spec.digits)
            if close_type == mt5.ORDER_TYPE_SELL
            else normalize_price(tick.ask, spec.digits)
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": settings.magic_number,
            "comment": "close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        logger.info("Closing position {} – {} {} @ {}", ticket, close_type, symbol, price)

        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            logger.error("Close order_send returned None: {}", err)
            return TradeResult(success=False, error=str(err), request_dict=request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                "Close FAILED – retcode={} comment='{}'",
                result.retcode,
                result.comment,
            )
            return TradeResult(
                success=False,
                ticket=result.order,
                error=f"retcode={result.retcode}: {result.comment}",
                price=result.price,
                request_dict=request,
            )

        logger.info("Position {} closed – ticket={} price={}", ticket, result.order, result.price)
        return TradeResult(
            success=True,
            ticket=result.order,
            price=result.price,
            request_dict=request,
        )

    def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> TradeResult:
        """Modify SL/TP of an open position.

        Parameters
        ----------
        ticket :
            Position ticket to modify.
        sl :
            New stop-loss price (``None`` = leave unchanged).
        tp :
            New take-profit price (``None`` = leave unchanged).

        Returns
        -------
        TradeResult
            Outcome of the modify request.
        """
        positions = mt5.positions_get(ticket=ticket)
        if positions is None or len(positions) == 0:
            return TradeResult(
                success=False,
                error=f"Position ticket {ticket} not found",
            )

        pos = positions[0]
        symbol = pos.symbol

        spec = self.get_symbol_spec(symbol)
        if spec is None:
            return TradeResult(
                success=False,
                error=f"Cannot retrieve spec for '{symbol}' to modify position {ticket}",
            )

        # Normalise provided prices; keep existing if None.
        norm_sl = normalize_price(sl, spec.digits) if sl is not None else pos.sl
        norm_tp = normalize_price(tp, spec.digits) if tp is not None else pos.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": norm_sl,
            "tp": norm_tp,
        }

        logger.info(
            "Modifying position {} – SL={} TP={}",
            ticket,
            norm_sl,
            norm_tp,
        )

        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            logger.error("Modify order_send returned None: {}", err)
            return TradeResult(success=False, error=str(err), request_dict=request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                "Modify FAILED – retcode={} comment='{}'",
                result.retcode,
                result.comment,
            )
            return TradeResult(
                success=False,
                ticket=ticket,
                error=f"retcode={result.retcode}: {result.comment}",
                request_dict=request,
            )

        logger.info("Position {} modified successfully – SL={} TP={}", ticket, norm_sl, norm_tp)
        return TradeResult(
            success=True,
            ticket=ticket,
            request_dict=request,
        )

    # ----------------------------------------------------------------
    # Position / order queries
    # ----------------------------------------------------------------

    def get_positions(self) -> List[Dict]:
        """Return all open positions as a list of dicts."""
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return []

        result = []
        for pos in positions:
            result.append(
                {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "comment": pos.comment,
                    "magic": pos.magic,
                    "time": pos.time,
                    "time_update": pos.time_update,
                    "identifier": pos.identifier,
                }
            )
        return result

    def get_orders(self) -> List[Dict]:
        """Return all pending orders as a list of dicts."""
        orders = mt5.orders_get()
        if orders is None or len(orders) == 0:
            return []

        result = []
        for order in orders:
            result.append(
                {
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": order.type,
                    "volume": order.volume_initial,
                    "price": order.price_current,
                    "sl": order.sl,
                    "tp": order.tp,
                    "comment": order.comment,
                    "magic": order.magic,
                    "time_setup": order.time_setup,
                    "time_expiration": order.time_expiration,
                }
            )
        return result

    def get_positions_by_symbol(self, symbol: str) -> List[Dict]:
        """Filter open positions to those matching *symbol*."""
        return [p for p in self.get_positions() if p["symbol"] == symbol]

    # ----------------------------------------------------------------
    # History
    # ----------------------------------------------------------------

    def get_history_deals(self, days: int = 1) -> List[Dict]:
        """Retrieve deal history for the last *days* days.

        Useful for daily P&L tracking.

        Parameters
        ----------
        days :
            Look-back window in days.

        Returns
        -------
        list[dict]
            List of deal dictionaries.
        """
        date_from = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(date_from, datetime.now())

        if deals is None or len(deals) == 0:
            return []

        result = []
        for deal in deals:
            result.append(
                {
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "symbol": deal.symbol,
                    "type": deal.type,
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "commission": deal.commission,
                    "swap": deal.swap,
                    "comment": deal.comment,
                    "magic": deal.magic,
                    "time": deal.time,
                    "position_id": deal.position_id,
                    "entry": deal.entry,
                }
            )
        return result
