"""Comprehensive risk management for the MT5 AI Trader project.

This module enforces **all** risk controls before a trade is allowed:

1. Daily drawdown limit
2. Consecutive loss limit
3. Max open positions
4. Max trades per day
5. Spread limit
6. SL/TP validation
7. Risk/reward minimum
8. No trade without SL or TP
9. AI confidence threshold

The daily state is tracked from **realised** MT5 deal history, not
unrealised floating P&L, which fixes a common source of incorrect
drawdown calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from config.settings import settings
from models.enums import SignalType
from models.market import SymbolSpec
from models.signals import AIDecision
from mt5_connector.connector import MT5Connector
from utils.helpers import is_valid_sl_tp
from utils.logging import logger

from risk.position_sizer import PositionSizer


# =====================================================================
# Daily state tracker
# =====================================================================


@dataclass
class DailyState:
    """Tracks daily trading state for risk management.

    Reset automatically at the start of each new trading day.
    """

    date: date = field(default_factory=date.today)
    realized_pnl: float = 0.0
    trades_count: int = 0
    consecutive_losses: int = 0
    trades: list = field(default_factory=list)  # list of dicts with symbol, pnl, time


# =====================================================================
# Risk Manager
# =====================================================================


class RiskManager:
    """Comprehensive risk manager that gates every trade.

    Before any order is placed, :meth:`check_all` must return
    ``True``.  Every failed check is collected into a list of
    human-readable failure reasons so the caller can log exactly
    *why* a trade was rejected.

    Parameters
    ----------
    connector :
        Live :class:`MT5Connector` instance used to query deal
        history, current spread, and open positions.
    """

    def __init__(self, connector: MT5Connector) -> None:
        self.connector = connector
        self.position_sizer = PositionSizer()
        self.daily_state = DailyState()
        self._reset_if_new_day()

    # -----------------------------------------------------------------
    # Daily state management
    # -----------------------------------------------------------------

    def _reset_if_new_day(self) -> None:
        """Reset daily counters when the calendar date changes."""
        today = date.today()
        if self.daily_state.date != today:
            logger.info(
                "New trading day ({}). Resetting daily state. "
                "Yesterday: {} trades, P&L: ${:.2f}",
                today,
                self.daily_state.trades_count,
                self.daily_state.realized_pnl,
            )
            self.daily_state = DailyState(date=today)

    def update_from_history(self) -> None:
        """Update daily state from actual MT5 deal history.

        This fixes the original bug where daily loss was calculated
        from unrealised floating P&L instead of realised deals.
        """
        deals = self.connector.get_history_deals(days=1)
        if not deals:
            return

        total_pnl = 0.0
        trade_count = 0
        losses_in_row = 0
        max_consecutive = 0

        # Sort by time to process in chronological order.
        sorted_deals = sorted(deals, key=lambda d: d.get("time", datetime.min))

        for deal in sorted_deals:
            pnl = deal.get("profit", 0.0)
            if pnl == 0:
                continue
            total_pnl += pnl
            trade_count += 1

            if pnl < 0:
                losses_in_row += 1
                max_consecutive = max(max_consecutive, losses_in_row)
            else:
                losses_in_row = 0

        self.daily_state.realized_pnl = total_pnl
        self.daily_state.trades_count = trade_count
        self.daily_state.consecutive_losses = max_consecutive

    # -----------------------------------------------------------------
    # Master risk check
    # -----------------------------------------------------------------

    def check_all(
        self,
        symbol: str,
        decision: AIDecision,
        balance: float,
        open_positions_count: int,
    ) -> tuple[bool, List[str]]:
        """Run **all** risk checks and return the verdict.

        Parameters
        ----------
        symbol :
            The instrument to trade (e.g. ``"BTCUSD"``).
        decision :
            AI-generated decision with direction, confidence,
            SL, TP, risk/reward, and rejection reasons.
        balance :
            Current account balance.
        open_positions_count :
            Number of currently open positions.

        Returns
        -------
        tuple[bool, list[str]]
            ``(allowed, failures)`` — every check must pass for
            ``allowed`` to be ``True``.  ``failures`` contains
            human-readable reasons for each failed check.
        """
        self._reset_if_new_day()
        self.update_from_history()

        failures: List[str] = []

        # 1. NO_TRADE decision
        if decision.direction == SignalType.NO_TRADE:
            failures.append(f"AI decision is NO TRADE: {decision.rejection_reasons}")

        # 2. No stop-loss
        if decision.stop_loss is None:
            failures.append("No stop loss provided – trade rejected")

        # 3. No take-profit
        if decision.take_profit is None:
            failures.append("No take profit provided – trade rejected")

        # 4. Daily drawdown
        max_daily_loss = balance * settings.max_daily_drawdown_pct
        if self.daily_state.realized_pnl < -max_daily_loss:
            failures.append(
                f"Daily loss limit reached: ${self.daily_state.realized_pnl:.2f} "
                f"(max: -${max_daily_loss:.2f})"
            )

        # 5. Consecutive losses
        if self.daily_state.consecutive_losses >= settings.max_consecutive_losses:
            failures.append(
                f"Consecutive loss limit reached: {self.daily_state.consecutive_losses} "
                f"(max: {settings.max_consecutive_losses})"
            )

        # 6. Max open positions
        if open_positions_count >= settings.max_open_positions:
            failures.append(
                f"Max open positions reached: {open_positions_count} "
                f"(max: {settings.max_open_positions})"
            )

        # 7. Max trades per day
        if self.daily_state.trades_count >= settings.max_trades_per_day:
            failures.append(
                f"Max daily trades reached: {self.daily_state.trades_count} "
                f"(max: {settings.max_trades_per_day})"
            )

        # 8. Risk/reward (guard against None)
        if decision.risk_reward is not None and decision.risk_reward < settings.min_risk_reward:
            failures.append(
                f"R:R too low: {decision.risk_reward:.2f} "
                f"(min: {settings.min_risk_reward})"
            )
        elif decision.risk_reward is None:
            failures.append("R:R is missing – trade rejected")

        # 9. Confidence threshold
        if decision.confidence < settings.ai_confidence_threshold:
            failures.append(
                f"Confidence too low: {decision.confidence:.2f} "
                f"(min: {settings.ai_confidence_threshold})"
            )

        allowed = len(failures) == 0
        if not allowed:
            logger.warning("Risk check FAILED: {}", failures)
        else:
            logger.info(
                "Risk check PASSED for {} {}",
                symbol,
                decision.direction.value,
            )

        return allowed, failures

    # -----------------------------------------------------------------
    # Individual checks (can be called independently)
    # -----------------------------------------------------------------

    def check_spread(self, symbol: str) -> tuple[bool, str]:
        """Check whether the current spread is acceptable.

        Parameters
        ----------
        symbol :
            Instrument to check.

        Returns
        -------
        tuple[bool, str]
            ``(True, message)`` if spread is within limits,
            ``(False, reason)`` otherwise.
        """
        spread = self.connector.get_current_spread_points(symbol)
        if spread > settings.max_spread_points:
            return (
                False,
                f"Spread too high: {spread} pts (max: {settings.max_spread_points})",
            )
        return True, f"Spread OK: {spread} pts"

    def validate_sl_tp(
        self,
        entry: float,
        sl: float,
        tp: float,
        direction: SignalType,
        symbol_spec: Optional[SymbolSpec] = None,
    ) -> tuple[bool, str]:
        """Validate SL and TP placement relative to entry and direction.

        Parameters
        ----------
        entry :
            Planned entry price.
        sl :
            Stop-loss price.
        tp :
            Take-profit price.
        direction :
            Trade direction (``SignalType.BUY`` or ``SignalType.SELL``).
        symbol_spec :
            Symbol specification used to obtain the ``point`` value
            for rounding tolerance.  Falls back to ``0.00001`` if not
            provided.

        Returns
        -------
        tuple[bool, str]
            ``(True, "")`` when valid, ``(False, reason)`` otherwise.
        """
        point = symbol_spec.point if symbol_spec else 0.00001
        return is_valid_sl_tp(entry, sl, tp, direction.value, point)

    # -----------------------------------------------------------------
    # Position sizing
    # -----------------------------------------------------------------

    def calculate_position_size(
        self,
        balance: float,
        entry: float,
        sl: float,
        symbol_spec: SymbolSpec,
    ) -> float:
        """Calculate position size using correct broker specifications.

        Delegates to :class:`PositionSizer` with the configured
        ``risk_per_trade`` percentage from settings.

        Parameters
        ----------
        balance :
            Current account balance.
        entry :
            Planned entry price.
        sl :
            Stop-loss price.
        symbol_spec :
            Live symbol specification from MT5.

        Returns
        -------
        float
            Position size in lots.
        """
        return self.position_sizer.calculate(
            balance=balance,
            risk_percent=settings.risk_per_trade,
            entry=entry,
            sl=sl,
            symbol_spec=symbol_spec,
        )

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    def get_daily_summary(self) -> Dict:
        """Return a summary dict of today's risk state.

        Returns
        -------
        dict
            Keys: ``date``, ``realized_pnl``, ``trades_count``,
            ``consecutive_losses``, ``remaining_trades``,
            ``remaining_loss_limit``.
        """
        return {
            "date": str(self.daily_state.date),
            "realized_pnl": self.daily_state.realized_pnl,
            "trades_count": self.daily_state.trades_count,
            "consecutive_losses": self.daily_state.consecutive_losses,
            "remaining_trades": max(
                0, settings.max_trades_per_day - self.daily_state.trades_count
            ),
            "remaining_loss_limit": settings.max_daily_drawdown_pct * 100,
        }
