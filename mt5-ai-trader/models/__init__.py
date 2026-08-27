"""Models package for the MT5 AI Trader project.

Re-exports all public enums, dataclasses, and types from the submodules
so they can be imported directly as ``from models import ...``.
"""

from __future__ import annotations

from .enums import (
    MarketBias,
    PatternName,
    SignalType,
    Timeframe,
    TradeDirection,
    TrendDirection,
)
from .market import CandleData, SRLevel, StructureBreak, SwingPoint, SymbolSpec
from .signals import AIDecision, MarketAnalysis, TradeSignal

__all__ = [
    # enums
    "SignalType",
    "Timeframe",
    "MarketBias",
    "TradeDirection",
    "TrendDirection",
    "PatternName",
    # signals
    "TradeSignal",
    "AIDecision",
    "MarketAnalysis",
    # market
    "CandleData",
    "SymbolSpec",
    "SRLevel",
    "SwingPoint",
    "StructureBreak",
]
