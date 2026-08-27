"""Strategies package for the MT5 AI Trader project.

Re-exports the public API from each sub-module so that consumers
can write:

    from strategies import (BaseStrategy, SupportResistanceDetector,
                            MarketStructureAnalyzer, NakedForexStrategy,
                            MultiTimeframeAnalyzer)
"""

from strategies.base import BaseStrategy
from strategies.market_structure import MarketStructureAnalyzer
from strategies.multi_timeframe import MultiTimeframeAnalyzer
from strategies.naked_forex import NakedForexStrategy
from strategies.support_resistance import SupportResistanceDetector

__all__ = [
    "BaseStrategy",
    "MarketStructureAnalyzer",
    "MultiTimeframeAnalyzer",
    "NakedForexStrategy",
    "SupportResistanceDetector",
]
