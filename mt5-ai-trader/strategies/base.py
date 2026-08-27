"""Abstract base strategy class for the MT5 AI Trader project.

Every concrete trading strategy (Naked Forex, multi-timeframe, etc.)
inherits from :class:`BaseStrategy` and implements the two core
abstract methods: :meth:`analyze` and :meth:`identify_trend`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

import pandas as pd

from models.enums import TrendDirection
from models.market import SymbolSpec
from models.signals import TradeSignal

if TYPE_CHECKING:
    pass

__all__ = ["BaseStrategy"]


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Concrete subclasses must override :meth:`analyze` and
    :meth:`identify_trend`.  Convenience wrappers for ATR
    calculations are provided so every strategy has consistent
    access to volatility data.
    """

    # Subclasses can override these to change default behaviour.
    name: str = "base"

    @abstractmethod
    def analyze(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        symbol_spec: SymbolSpec = None,
        sr_levels: list = None,
    ) -> list[TradeSignal]:
        """Analyze OHLCV data and return trade signals.

        Parameters
        ----------
        df:
            DataFrame with columns ``open``, ``high``, ``low``,
            ``close``, ``tick_volume`` (at minimum).
        symbol:
            The instrument symbol (e.g. ``"XAUUSD"``).
        timeframe:
            Timeframe string (e.g. ``"H1"``).
        symbol_spec:
            Optional :class:`~models.market.SymbolSpec` with
            broker contract details.
        sr_levels:
            Optional list of :class:`~models.market.SRLevel`
            objects to incorporate into the analysis.

        Returns
        -------
        list[TradeSignal]
            Zero or more trade signals produced by the strategy.
        """
        ...

    @abstractmethod
    def identify_trend(self, df: pd.DataFrame, lookback: int = 20) -> TrendDirection:
        """Determine the prevailing trend direction.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        lookback:
            Number of recent bars to consider.

        Returns
        -------
        TrendDirection
            ``UP``, ``DOWN``, or ``RANGING``.
        """
        ...

    # ------------------------------------------------------------------
    # Convenience helpers (not abstract – shared by all strategies)
    # ------------------------------------------------------------------

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute ATR series using the shared helper.

        Delegates to :func:`utils.helpers.calculate_atr`.
        """
        from utils.helpers import calculate_atr as _calc_atr

        return _calc_atr(df, period)

    def get_latest_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Return the most recent ATR value as a float.

        Delegates to :func:`utils.helpers.calculate_atr_value`.
        """
        from utils.helpers import calculate_atr_value

        return calculate_atr_value(df, period)
