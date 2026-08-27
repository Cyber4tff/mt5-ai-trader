"""Market data models for the MT5 AI Trader project.

Provides dataclass definitions for candle/OHLCV data, symbol specifications,
support/resistance levels, swing points, and market structure breaks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class CandleData:
    """Single OHLCV candle with spread information."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float
    spread: float


@dataclass
class SymbolSpec:
    """Specification and trading parameters for a symbol."""
    name: str
    bid: float
    ask: float
    spread: float
    point: float
    digits: int
    trade_allowed: bool
    volume_min: float
    volume_max: float
    volume_step: float
    tick_value: float
    tick_size: float
    volume_contract_size: float
    trade_mode: int
    filling_mode: int


@dataclass
class SRLevel:
    """A support or resistance price level with strength metadata."""
    price: float
    type: Literal["support", "resistance"]
    strength: int
    touches: int
    touch_times: List = field(default_factory=list)
    last_touch_time: Optional[float] = None
    zone_high: Optional[float] = None
    zone_low: Optional[float] = None


@dataclass
class SwingPoint:
    """A detected swing high or swing low on the chart."""
    price: float
    type: Literal["high", "low"]
    index: int
    strength: int


@dataclass
class StructureBreak:
    """A break of market structure (Break of Structure or Change of Character)."""
    type: Literal["BOS", "CHOCH"]
    direction: Literal["bullish", "bearish"]
    price: float
    time: float
    index: int
    from_level: Optional[float] = None
    to_level: Optional[float] = None
