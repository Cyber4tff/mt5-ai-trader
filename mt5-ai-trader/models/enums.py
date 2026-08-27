"""Enumeration types for the MT5 AI Trader project.

Defines all core enums used across the trading pipeline, including signal
types, timeframes, market bias, trade directions, trend directions, and
chart pattern names.
"""

from __future__ import annotations

from enum import Enum


class SignalType(Enum):
    """Type of trading signal."""
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


class Timeframe(Enum):
    """MetaTrader 5 timeframe identifiers."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN = "MN"


class MarketBias(Enum):
    """Overall market sentiment or bias."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class TradeDirection(Enum):
    """Direction of a trade position."""
    LONG = "LONG"
    SHORT = "SHORT"


class TrendDirection(Enum):
    """Directional classification of a price trend."""
    UP = "UP"
    DOWN = "DOWN"
    RANGING = "RANGING"


class PatternName(Enum):
    """Recognised candlestick and chart pattern identifiers."""
    BIG_SHADOW_BULL = "BIG_SHADOW_BULL"
    BIG_SHADOW_BEAR = "BIG_SHADOW_BEAR"
    KANGAROO_TAIL_BULL = "KANGAROO_TAIL_BULL"
    KANGAROO_TAIL_BEAR = "KANGAROO_TAIL_BEAR"
    LAST_KISS_BULL = "LAST_KISS_BULL"
    LAST_KISS_BEAR = "LAST_KISS_BEAR"
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"
    DOUBLE_TOP = "DOUBLE_TOP"
    NONE = "NONE"
