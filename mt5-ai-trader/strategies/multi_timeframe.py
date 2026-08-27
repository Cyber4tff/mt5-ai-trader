"""Multi-timeframe analysis hierarchy for the MT5 AI Trader project.

Implements the top-down analysis approach:

    D1 → H4 → H1 → M15 → M5

Higher timeframes establish market bias.  Lower timeframes find
precise entry points.  The :class:`MultiTimeframeAnalyzer` orchestrates
analysis across all configured timeframes and computes a confluence
score that feeds into the AI decision layer.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from config.settings import settings
from models.enums import MarketBias, SignalType, TrendDirection
from models.market import SRLevel, StructureBreak, SymbolSpec
from models.signals import MarketAnalysis, TradeSignal
from strategies.base import BaseStrategy
from strategies.market_structure import MarketStructureAnalyzer
from strategies.support_resistance import SupportResistanceDetector
from utils.helpers import calculate_atr_value
from utils.logging import logger

__all__ = ["MultiTimeframeAnalyzer"]

# Map TrendDirection enum values to the string labels used by
# MarketStructureAnalyzer.detect_choch() which expects
# "bullish" / "bearish" / "ranging".
_TREND_TO_CHOCH_LABEL = {
    TrendDirection.UP: "bullish",
    TrendDirection.DOWN: "bearish",
    TrendDirection.RANGING: "ranging",
}


class MultiTimeframeAnalyzer:
    """Orchestrates analysis across multiple timeframes.

    Timeframe hierarchy (higher → lower):
        D1 → H4 → H1 → M15 → M5

    Higher TFs establish bias, lower TFs find entries.

    Parameters
    ----------
    strategy:
        A concrete :class:`BaseStrategy` subclass (e.g.
        :class:`NakedForexStrategy`) used for pattern-level signal
        generation on each timeframe.
    """

    def __init__(self, strategy: BaseStrategy) -> None:
        self.strategy = strategy
        self.structure_analyzer = MarketStructureAnalyzer()
        self.sr_detector = SupportResistanceDetector()
        self.timeframes: list[str] = settings.mtf_timeframes  # ['D1', 'H4', 'H1', 'M15', 'M5']

    # ------------------------------------------------------------------
    # Timeframe ordering helpers
    # ------------------------------------------------------------------

    def get_tf_rank(self, tf: str) -> float:
        """Return a numeric rank for *tf* (lower = higher timeframe).

        D1=0, H4=1, H1=2, M30=3.5, M15=3, M5=4, W1=-1.
        """
        tf_order = {
            "D1": 0, "H4": 1, "H1": 2, "M15": 3, "M5": 4,
            "M30": 3.5, "W1": -1,
        }
        return tf_order.get(tf.upper(), 99)

    def get_higher_timeframes(self, tf: str) -> list[str]:
        """Return all configured timeframes higher than *tf*."""
        rank = self.get_tf_rank(tf)
        return [t for t in self.timeframes if self.get_tf_rank(t) < rank]

    def get_lower_timeframes(self, tf: str) -> list[str]:
        """Return all configured timeframes lower than *tf*."""
        rank = self.get_tf_rank(tf)
        return [t for t in self.timeframes if self.get_tf_rank(t) > rank]

    # ------------------------------------------------------------------
    # Single-timeframe analysis
    # ------------------------------------------------------------------

    def analyze_timeframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        sr_levels: Optional[list] = None,
    ) -> MarketAnalysis:
        """Analyze a single timeframe and return a :class:`MarketAnalysis`.

        Steps:

        1. Get trend via the structure analyzer.
        2. Derive market bias.
        3. Calculate ATR and classify the volatility regime
           (high / normal / low based on ATR percentile).
        4. Detect BOS and CHOCH events.
        5. Find S/R levels (unless pre-computed).
        6. Run the strategy's pattern detection.
        7. Determine simple momentum (price vs 20-period SMA).

        Parameters
        ----------
        df:
            OHLCV DataFrame for the timeframe.
        symbol:
            Instrument symbol.
        timeframe:
            Timeframe string (e.g. ``"H1"``).
        sr_levels:
            Optional pre-computed S/R levels.

        Returns
        -------
        MarketAnalysis
        """
        trend = self.structure_analyzer.identify_trend(df)
        bias = self.structure_analyzer.get_market_bias(df)

        atr = calculate_atr_value(df, settings.naked_forex["atr_period"])

        # Volatility regime: compare recent ATR to historical ATR.
        atr_series = self.strategy.calculate_atr(df)
        atr_list = atr_series.dropna().tolist()
        vol_regime = "normal"
        if len(atr_list) >= 20:
            recent_avg = sum(atr_list[-5:]) / 5
            historical_avg = sum(atr_list[-20:]) / 20
            if historical_avg > 0:
                ratio = recent_avg / historical_avg
                if ratio > 1.5:
                    vol_regime = "high"
                elif ratio < 0.7:
                    vol_regime = "low"

        # ATR percentile: where the current ATR sits in its own history.
        atr_percentile = 50.0
        if len(atr_list) >= 20:
            atr_percentile = (
                sum(1 for a in atr_list if a < atr) / len(atr_list) * 100
            )

        # S/R levels.
        if sr_levels is None:
            sr_levels = self.sr_detector.detect_levels(df)

        # BOS / CHOCH.
        swing_highs, swing_lows = self.structure_analyzer.find_swing_points(df)
        structure_breaks = self.structure_analyzer.detect_bos(
            df, swing_highs, swing_lows
        )
        # detect_choch expects a string label ("bullish"/"bearish"/"ranging"),
        # not the TrendDirection enum value ("UP"/"DOWN"/"RANGING").
        choch_label = _TREND_TO_CHOCH_LABEL.get(trend, "ranging")
        structure_breaks += self.structure_analyzer.detect_choch(
            df, swing_highs, swing_lows, choch_label
        )

        # Strategy signals.
        signals = self.strategy.analyze(
            df, symbol, timeframe, sr_levels=sr_levels
        )

        # Simple momentum: is price above or below the 20-period SMA?
        sma20 = df["close"].tail(20).mean()
        current = df.iloc[-1]["close"]
        momentum = "bullish" if current > sma20 else "bearish"

        return MarketAnalysis(
            timeframe=timeframe,
            trend=trend,
            bias=bias,
            atr=atr,
            atr_percentile=atr_percentile,
            volatility_regime=vol_regime,
            structure_breaks=structure_breaks,
            sr_levels=sr_levels,
            momentum=momentum,
            signals=signals,
        )

    # ------------------------------------------------------------------
    # Multi-timeframe confluence
    # ------------------------------------------------------------------

    def compute_confluence(
        self, analyses: Dict[str, MarketAnalysis]
    ) -> dict:
        """Compute multi-timeframe confluence score.

        Returns a dictionary with:

        * ``direction`` – ``'bullish'``, ``'bearish'``, or ``'neutral'``
        * ``score`` – ``0.0`` to ``1.0`` (fraction of TFs agreeing)
        * ``higher_tf_bias`` – :class:`MarketBias` from the highest
          available timeframe
        * ``trend_alignment`` – ``True`` if *all* TFs agree
        * ``factors`` – human-readable list of per-TF bias labels
        * ``bullish_ratio`` / ``bearish_ratio`` – decimal fractions

        Parameters
        ----------
        analyses:
            Mapping of ``timeframe_string`` → :class:`MarketAnalysis`.

        Returns
        -------
        dict
        """
        if not analyses:
            return {
                "direction": "neutral",
                "score": 0.0,
                "higher_tf_bias": MarketBias.NEUTRAL,
                "trend_alignment": False,
                "factors": ["No data"],
                "bullish_ratio": 0.0,
                "bearish_ratio": 0.0,
            }

        # Sort by TF rank (D1 first).
        sorted_tfs = sorted(
            analyses.keys(), key=lambda t: self.get_tf_rank(t)
        )

        bullish_count = 0
        bearish_count = 0
        total = len(sorted_tfs)
        factors: List[str] = []

        for tf in sorted_tfs:
            analysis = analyses[tf]
            if analysis.bias == MarketBias.BULLISH:
                bullish_count += 1
                factors.append(f"{tf}: bullish bias")
            elif analysis.bias == MarketBias.BEARISH:
                bearish_count += 1
                factors.append(f"{tf}: bearish bias")
            else:
                factors.append(f"{tf}: neutral")

        # Higher TF bias (from D1, or next highest available).
        higher_tf_bias = MarketBias.NEUTRAL
        for tf in sorted_tfs:
            if analyses[tf].bias != MarketBias.NEUTRAL:
                higher_tf_bias = analyses[tf].bias
                break

        # Direction requires ≥60 % agreement.
        if bullish_count > bearish_count and bullish_count >= total * 0.6:
            direction = "bullish"
        elif bearish_count > bullish_count and bearish_count >= total * 0.6:
            direction = "bearish"
        else:
            direction = "neutral"

        # Score = fraction of TFs in the majority direction.
        score = (
            max(bullish_count, bearish_count) / total if total > 0 else 0
        )

        # Trend alignment: *all* timeframes must agree.
        trend_alignment = (bullish_count == total) or (bearish_count == total)

        return {
            "direction": direction,
            "score": score,
            "higher_tf_bias": higher_tf_bias,
            "trend_alignment": trend_alignment,
            "factors": factors,
            "bullish_ratio": bullish_count / total if total else 0,
            "bearish_ratio": bearish_count / total if total else 0,
        }
