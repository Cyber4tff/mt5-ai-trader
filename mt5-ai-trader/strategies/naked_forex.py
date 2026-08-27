"""Naked Forex price-action strategy for the MT5 AI Trader project.

Implements the four core Naked Forex patterns:

* **Big Shadow** – Engulfing candle whose body fully engulfs the
  previous candle's body and whose range is significantly larger.
* **Kangaroo Tail** – Pin bar with a long tail (wick) and a small
  body relative to the total range.
* **Last Kiss** – Price breaks through a S/R level, then returns to
  "kiss" it before reversing decisively.
* **Double Hit** – Price tests the same level twice (double top /
  double bottom) within an ATR-based tolerance.

Key fixes over the original implementation
-------------------------------------------

1. **Trend filter was inverted.**  The original blocked trades that
   aligned with the trend and only allowed counter-trend trades in
   ranging markets.  This version *allows* with-trend signals and
   *rejects* counter-trend signals (except in ranging markets when
   the pattern is strong enough).

2. **S/R detection used scipy.**  Replaced with the project's own
   :class:`strategies.support_resistance.SupportResistanceDetector`
   which uses pure numpy.

3. **Position sizing was broken.**  This module produces *signals only*;
   position sizing is delegated to the ``risk/position_sizer`` module.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from config.settings import settings
from models.enums import PatternName, SignalType, TrendDirection
from models.market import SRLevel
from models.signals import TradeSignal
from strategies.base import BaseStrategy
from strategies.market_structure import MarketStructureAnalyzer
from strategies.support_resistance import SupportResistanceDetector
from utils.helpers import calculate_atr_value
from utils.logging import logger

__all__ = ["NakedForexStrategy"]


class NakedForexStrategy(BaseStrategy):
    """Naked Forex price-action strategy.

    Detects Big Shadow, Kangaroo Tail, Last Kiss, and Double Hit
    patterns.  All signals are filtered against the prevailing
    trend (identified via swing-point analysis) and validated
    against detected support/resistance levels.
    """

    name: str = "naked_forex"

    def __init__(self) -> None:
        super().__init__()
        self.config = settings.naked_forex
        self.sr_detector = SupportResistanceDetector(
            lookback=self.config["support_resistance_lookback"],
            atr_tolerance_mult=self.config.get("sr_touch_tolerance_atr_mult", 0.3),
        )
        self.structure_analyzer = MarketStructureAnalyzer()

    # ------------------------------------------------------------------
    # Trend identification (delegates to MarketStructureAnalyzer)
    # ------------------------------------------------------------------

    def identify_trend(self, df: pd.DataFrame, lookback: Optional[int] = None) -> TrendDirection:
        """Determine the prevailing trend direction.

        Delegates to :class:`MarketStructureAnalyzer` for swing-point
        based HH/HL/LH/LL classification.
        """
        if lookback is None:
            lookback = self.config["trend_lookback"]
        return self.structure_analyzer.identify_trend(df.tail(lookback))

    # ------------------------------------------------------------------
    # Room-to-left check
    # ------------------------------------------------------------------

    def _has_room_to_left(
        self, df: pd.DataFrame, idx: int, min_candles: Optional[int] = None, max_candles: Optional[int] = None
    ) -> bool:
        """Check that there is empty space to the left of the candle.

        "Room to the left" means no similarly-sized candle bodies
        appear in the window left of *idx*.  This is a core Naked
        Forex concept that filters out patterns occurring inside
        congestion.
        """
        if min_candles is None:
            min_candles = self.config["room_to_left"]
        if max_candles is None:
            max_candles = self.config["max_room_to_left"]
        if idx < min_candles:
            return False

        left = df.iloc[max(0, idx - max_candles) : idx]
        if len(left) == 0:
            return False

        curr_range = float(df.iloc[idx]["high"] - df.iloc[idx]["low"])
        if curr_range == 0:
            return False

        # Count candles whose body is > 70% of the current candle's range.
        similar_bodies = ((abs(left["close"] - left["open"]) / curr_range) > 0.7).sum()
        return int(similar_bodies) == 0

    # ------------------------------------------------------------------
    # Pattern: Big Shadow
    # ------------------------------------------------------------------

    def is_big_shadow(self, df: pd.DataFrame, idx: int) -> tuple[bool, str]:
        """Detect a Big Shadow (engulfing) pattern at *idx*.

        A Big Shadow requires:

        1. The current candle's body **fully engulfs** the previous
           candle's body (open-to-close range).
        2. The current candle's range is >= ``prev_range * engulfing_multiplier``.
        3. The body/range ratio >= ``min_candle_body_ratio``.
        4. Room to the left.

        Returns
        -------
        tuple[bool, str]
            ``(is_valid, pattern_name)`` where *pattern_name* is
            ``"big_shadow_bullish"`` or ``"big_shadow_bearish"``.
        """
        if idx < 1:
            return False, ""

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]

        o, h, l, c = float(curr["open"]), float(curr["high"]), float(curr["low"]), float(curr["close"])
        po, ph, pl, pc = float(prev["open"]), float(prev["high"]), float(prev["low"]), float(prev["close"])

        curr_body_lo = min(o, c)
        curr_body_hi = max(o, c)
        prev_body_lo = min(po, pc)
        prev_body_hi = max(po, pc)

        # Body must engulf previous body.
        if curr_body_lo > prev_body_lo or curr_body_hi < prev_body_hi:
            return False, ""

        curr_range = h - l
        prev_range = ph - pl
        if curr_range == 0 or prev_range == 0:
            return False, ""

        # Range must be larger than previous.
        if curr_range < prev_range * self.config["engulfing_multiplier"]:
            return False, ""

        # Body must be a significant portion of the range.
        body_ratio = abs(c - o) / curr_range
        if body_ratio < self.config["min_candle_body_ratio"]:
            return False, ""

        if not self._has_room_to_left(df, idx):
            return False, ""

        # Determine direction.
        if c > o:
            return True, "big_shadow_bullish"
        else:
            return True, "big_shadow_bearish"

    # ------------------------------------------------------------------
    # Pattern: Kangaroo Tail
    # ------------------------------------------------------------------

    def is_kangaroo_tail(self, df: pd.DataFrame, idx: int) -> tuple[bool, str]:
        """Detect a Kangaroo Tail (pin bar) pattern at *idx*.

        A Kangaroo Tail requires:

        1. Body/range ratio <= ``1 - pin_tail_ratio`` (small body,
           long tail).
        2. The dominant tail is >= 2x the other wick AND >=
           ``pin_tail_ratio`` of the total range.
        3. Room to the left.

        Returns
        -------
        tuple[bool, str]
            ``(is_valid, pattern_name)``.
        """
        if idx < 1:
            return False, ""

        curr = df.iloc[idx]
        o = float(curr["open"])
        h = float(curr["high"])
        l = float(curr["low"])
        c = float(curr["close"])

        curr_range = h - l
        if curr_range == 0:
            return False, ""

        body = abs(c - o)
        body_ratio = body / curr_range
        pin_tail_ratio = self.config["pin_bar_tail_ratio"]

        # Small body check.
        if body_ratio > (1 - pin_tail_ratio):
            return False, ""

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # Determine which wick is the tail.
        if lower_wick > upper_wick:
            # Bullish tail (long lower wick).
            if lower_wick < 2 * upper_wick:
                return False, ""
            if lower_wick / curr_range < pin_tail_ratio:
                return False, ""
        else:
            # Bearish tail (long upper wick).
            if upper_wick < 2 * lower_wick:
                return False, ""
            if upper_wick / curr_range < pin_tail_ratio:
                return False, ""

        if not self._has_room_to_left(df, idx):
            return False, ""

        if lower_wick > upper_wick:
            return True, "kangaroo_tail_bullish"
        else:
            return True, "kangaroo_tail_bearish"

    # ------------------------------------------------------------------
    # Pattern: Last Kiss
    # ------------------------------------------------------------------

    def is_last_kiss(self, df: pd.DataFrame, idx: int, sr_levels: list[SRLevel]) -> tuple[bool, str]:
        """Detect a Last Kiss pattern at *idx*.

        A Last Kiss occurs when:

        * Price broke through a S/R level (1-3 candles ago),
        * Then comes back to kiss it from the other side,
        * The current candle has a decisive body.

        A **bullish** Last Kiss: price broke *below* support, then
        kissed support from below with a bullish candle.

        A **bearish** Last Kiss: price broke *above* resistance, then
        kissed resistance from above with a bearish candle.

        Returns
        -------
        tuple[bool, str]
            ``(is_valid, pattern_name)``.
        """
        if idx < 3:
            return False, ""
        if not sr_levels:
            return False, ""

        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr <= 0:
            return False, ""

        curr = df.iloc[idx]
        curr_close = float(curr["close"])
        curr_body = abs(float(curr["close"]) - float(curr["open"]))
        curr_range = float(curr["high"]) - float(curr["low"])

        if curr_range == 0:
            return False, ""

        # Current candle must be decisive.
        if curr_body / curr_range < self.config["min_candle_body_ratio"]:
            return False, ""

        # Check each S/R level.
        for level in sr_levels:
            if not self.sr_detector.is_near_level(curr_close, level, atr):
                continue

            # Look at the 1-3 previous candles for a break.
            for lookback in range(1, 4):
                if idx - lookback < 0:
                    continue
                prev = df.iloc[idx - lookback]
                prev_close = float(prev["close"])
                prev_high = float(prev["high"])
                prev_low = float(prev["low"])

                if level.type == "support":
                    # Bullish last kiss: prev closed below support (break),
                    # current closes near/above support (kiss from below).
                    if prev_close < level.price and curr_close >= level.price * 0.998:
                        # Current candle should be bullish (close > open).
                        if float(curr["close"]) > float(curr["open"]):
                            return True, "last_kiss_bullish"

                elif level.type == "resistance":
                    # Bearish last kiss: prev closed above resistance (break),
                    # current closes near/below resistance (kiss from above).
                    if prev_close > level.price and curr_close <= level.price * 1.002:
                        # Current candle should be bearish (close < open).
                        if float(curr["close"]) < float(curr["open"]):
                            return True, "last_kiss_bearish"

        return False, ""

    # ------------------------------------------------------------------
    # Pattern: Double Hit
    # ------------------------------------------------------------------

    def is_double_hit(self, df: pd.DataFrame, idx: int) -> tuple[bool, str]:
        """Detect a Double Hit (double top / double bottom) at *idx*.

        Looks back 5-15 candles for a similar low (double bottom) or
        high (double top).  The two hits must be within ``0.3 * ATR``
        of each other and there must be a reaction (higher mid for
        double bottom, lower mid for double top) between them.

        Returns
        -------
        tuple[bool, str]
            ``(is_valid, pattern_name)``.
        """
        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr <= 0:
            return False, ""

        curr = df.iloc[idx]
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        curr_close = float(curr["close"])
        curr_open = float(curr["open"])

        tolerance = atr * 0.3
        min_lookback = 5
        max_lookback = 15

        # --- Double Bottom ---
        # Current candle has a low that is near a previous low.
        for j in range(idx - max_lookback, idx - min_lookback):
            if j < 0:
                continue
            other = df.iloc[j]
            other_low = float(other["low"])

            if abs(curr_low - other_low) > tolerance:
                continue

            # There must be a higher reaction between the two lows.
            mid_slice = df.iloc[j + 1 : idx]
            if len(mid_slice) == 0:
                continue
            mid_high = float(mid_slice["high"].max())
            if mid_high > curr_low + tolerance:
                return True, "double_bottom"

        # --- Double Top ---
        for j in range(idx - max_lookback, idx - min_lookback):
            if j < 0:
                continue
            other = df.iloc[j]
            other_high = float(other["high"])

            if abs(curr_high - other_high) > tolerance:
                continue

            # There must be a lower reaction between the two highs.
            mid_slice = df.iloc[j + 1 : idx]
            if len(mid_slice) == 0:
                continue
            mid_low = float(mid_slice["low"].min())
            if mid_low < curr_high - tolerance:
                return True, "double_top"

        return False, ""

    # ------------------------------------------------------------------
    # Signal creation (with FIXED trend filter)
    # ------------------------------------------------------------------

    _PATTERN_MAP: dict[str, PatternName] = {
        "big_shadow_bullish": PatternName.BIG_SHADOW_BULL,
        "big_shadow_bearish": PatternName.BIG_SHADOW_BEAR,
        "kangaroo_tail_bullish": PatternName.KANGAROO_TAIL_BULL,
        "kangaroo_tail_bearish": PatternName.KANGAROO_TAIL_BEAR,
        "last_kiss_bullish": PatternName.LAST_KISS_BULL,
        "last_kiss_bearish": PatternName.LAST_KISS_BEAR,
        "double_bottom": PatternName.DOUBLE_BOTTOM,
        "double_top": PatternName.DOUBLE_TOP,
    }

    def _create_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        pattern_str: str,
        symbol: str,
        timeframe: str,
        sr_levels: list[SRLevel],
        trend: TrendDirection,
    ) -> Optional[TradeSignal]:
        """Build a :class:`TradeSignal` from a detected pattern.

        This method contains the **critical trend filter fix**: trades
        aligned with the trend are allowed, counter-trend trades are
        rejected unless the market is ranging.
        """
        # Determine direction from pattern name.
        is_bullish = "bullish" in pattern_str or "bottom" in pattern_str
        is_bearish = "bearish" in pattern_str or "top" in pattern_str

        # ----------------------------------------------------------------
        # FIXED TREND FILTER:
        #   - With-trend signals: ALLOW
        #   - Counter-trend signals: REJECT
        #   - Ranging market: allow both directions
        # ----------------------------------------------------------------
        if is_bullish and trend == TrendDirection.DOWN:
            logger.debug(
                "Rejected bullish signal '%s' in DOWN trend (counter-trend)", pattern_str
            )
            return None
        if is_bearish and trend == TrendDirection.UP:
            logger.debug(
                "Rejected bearish signal '%s' in UP trend (counter-trend)", pattern_str
            )
            return None

        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr == 0:
            return None

        candle = df.iloc[idx]
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])
        curr_close = float(candle["close"])

        # Determine entry, SL, TP.
        if is_bullish:
            entry = candle_high + atr * 0.1  # slight buffer above
            sl = candle_low - atr * 0.5  # below the candle + ATR buffer

            # TP: nearest resistance above.
            nearest_sr = self.sr_detector.find_nearest_resistance(entry, sr_levels)
            if nearest_sr is not None:
                tp = nearest_sr.price
            else:
                tp = entry + 3 * atr
        else:
            entry = candle_low - atr * 0.1  # slight buffer below
            sl = candle_high + atr * 0.5  # above the candle + ATR buffer

            # TP: nearest support below.
            nearest_sr = self.sr_detector.find_nearest_support(entry, sr_levels)
            if nearest_sr is not None:
                tp = nearest_sr.price
            else:
                tp = entry - 3 * atr

        # Risk / Reward check.
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return None
        rr = reward / risk
        if rr < settings.min_risk_reward:
            logger.debug(
                "Rejected '%s': R/R %.2f below minimum %.2f",
                pattern_str, rr, settings.min_risk_reward,
            )
            return None

        # Confidence scoring (0–1).
        confidence = 0.4  # base

        if (is_bullish and trend == TrendDirection.UP) or (is_bearish and trend == TrendDirection.DOWN):
            confidence += 0.25  # strong trend alignment
        elif trend == TrendDirection.RANGING:
            confidence += 0.05  # weak alignment

        if nearest_sr is not None:
            confidence += 0.15  # S/R confluence

        # Pattern-specific bonus.
        if "big_shadow" in pattern_str:
            confidence += 0.10
        elif "kangaroo" in pattern_str:
            confidence += 0.08
        elif "last_kiss" in pattern_str:
            confidence += 0.07
        elif "double" in pattern_str:
            confidence += 0.09

        confidence = min(confidence, 1.0)

        signal_type = SignalType.BUY if is_bullish else SignalType.SELL
        pattern_enum = self._PATTERN_MAP.get(pattern_str, PatternName.NONE)

        return TradeSignal(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            confidence=confidence,
            pattern=pattern_enum,
            timeframe=timeframe,
            reason=f"{pattern_str} at {trend.value} market",
            risk_reward=rr,
            metadata={},
        )

    # ------------------------------------------------------------------
    # Main analysis entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        symbol_spec: object = None,
        sr_levels: Optional[list[SRLevel]] = None,
    ) -> list[TradeSignal]:
        """Analyze OHLCV data and return trade signals.

        Scans the last 10 completed candles (excluding the possibly
        incomplete current bar) for the four Naked Forex patterns.
        Signals are sorted by confidence and the top 3 are returned.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        symbol:
            Instrument symbol.
        timeframe:
            Timeframe string (e.g. ``"H1"``).
        symbol_spec:
            Unused by this strategy (signals only, no position sizing).
        sr_levels:
            Optional pre-computed S/R levels.  If ``None``, levels
            are detected automatically.

        Returns
        -------
        list[TradeSignal]
            Up to 3 signals, sorted by confidence descending.
        """
        if df is None or len(df) < 50:
            return []

        trend = self.identify_trend(df)

        if sr_levels is None:
            sr_levels = self.sr_detector.detect_levels(df)

        signals: list[TradeSignal] = []

        # Check last 10 completed candles (skip the very last one which
        # may be incomplete).
        start = max(10, len(df) - 10)
        end = len(df) - 1

        for i in range(start, end):
            # Patterns that don't need S/R levels.
            for pattern_fn in [self.is_big_shadow, self.is_kangaroo_tail, self.is_double_hit]:
                valid, name = pattern_fn(df, i)
                if valid:
                    sig = self._create_signal(df, i, name, symbol, timeframe, sr_levels, trend)
                    if sig is not None:
                        signals.append(sig)

            # Last Kiss requires S/R levels.
            valid, name = self.is_last_kiss(df, i, sr_levels)
            if valid:
                sig = self._create_signal(df, i, name, symbol, timeframe, sr_levels, trend)
                if sig is not None:
                    signals.append(sig)

        # Sort by confidence descending, return top 3.
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals[:3]
