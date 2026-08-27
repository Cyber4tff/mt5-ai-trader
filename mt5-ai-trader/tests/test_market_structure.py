"""Tests for MarketStructureAnalyzer and SupportResistanceDetector."""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

from models.enums import MarketBias, TrendDirection
from models.market import StructureBreak, SwingPoint
from strategies.market_structure import MarketStructureAnalyzer
from strategies.support_resistance import SupportResistanceDetector


# =====================================================================
# Helpers: craft OHLCV data with known structure
# =====================================================================


def _make_uptrend_df(n: int = 50) -> pd.DataFrame:
    """Create a clean uptrending DataFrame with clear swing points.

    Uses a sawtooth pattern: price rises, dips, rises higher, dips higher.
    This guarantees HH and HL swing patterns.
    """
    np.random.seed(99)
    base_time = datetime(2024, 1, 1)
    times = [base_time + timedelta(hours=i) for i in range(n)]

    # Build a price series with clear peaks and troughs.
    # Pattern: rise 10 bars, dip 5 bars, rise higher, dip higher, etc.
    price = 100.0
    closes = []
    for i in range(n):
        phase = i % 15
        if phase < 10:
            price += 0.5 + np.random.normal(0, 0.1)
        else:
            price -= 0.3 + np.random.normal(0, 0.05)
        closes.append(price)

    closes = np.array(closes)
    opens = closes - np.random.uniform(0.1, 0.3, n)
    highs = np.maximum(opens, closes) + np.random.uniform(0.2, 0.5, n)
    lows = np.minimum(opens, closes) - np.random.uniform(0.2, 0.5, n)
    volumes = np.full(n, 500.0)
    spreads = np.full(n, 2.0)

    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes,
         "tick_volume": volumes, "spread": spreads},
        index=times,
    )
    df.index.name = "time"
    return df


def _make_downtrend_df(n: int = 50) -> pd.DataFrame:
    """Create a clean downtrending DataFrame."""
    np.random.seed(77)
    base_time = datetime(2024, 1, 1)
    times = [base_time + timedelta(hours=i) for i in range(n)]

    price = 200.0
    closes = []
    for i in range(n):
        phase = i % 15
        if phase < 10:
            price -= 0.5 + np.random.normal(0, 0.1)
        else:
            price += 0.3 + np.random.normal(0, 0.05)
        closes.append(price)

    closes = np.array(closes)
    opens = closes + np.random.uniform(0.1, 0.3, n)
    highs = np.maximum(opens, closes) + np.random.uniform(0.2, 0.5, n)
    lows = np.minimum(opens, closes) - np.random.uniform(0.2, 0.5, n)
    volumes = np.full(n, 500.0)
    spreads = np.full(n, 2.0)

    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes,
         "tick_volume": volumes, "spread": spreads},
        index=times,
    )
    df.index.name = "time"
    return df


def _make_sr_df() -> pd.DataFrame:
    """Create data with obvious support/resistance levels.

    Price bounces between 100 and 110 several times.
    """
    np.random.seed(55)
    n = 80
    base_time = datetime(2024, 1, 1)
    times = [base_time + timedelta(hours=i) for i in range(n)]

    # Alternate between ~100 (support) and ~110 (resistance).
    pattern = []
    for i in range(n):
        cycle = i % 20
        if cycle < 10:
            # Rising from 100 to 110
            price = 100 + (cycle / 10.0) * 10
        else:
            # Falling from 110 to 100
            price = 110 - ((cycle - 10) / 10.0) * 10
        price += np.random.normal(0, 0.2)
        pattern.append(price)

    closes = np.array(pattern)
    opens = closes + np.random.normal(0, 0.3, n)
    highs = np.maximum(opens, closes) + np.random.uniform(0.1, 0.4, n)
    lows = np.minimum(opens, closes) - np.random.uniform(0.1, 0.4, n)

    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes,
         "tick_volume": np.full(n, 500.0), "spread": np.full(n, 2.0)},
        index=times,
    )
    df.index.name = "time"
    return df


def _make_bos_df() -> pd.DataFrame:
    """Create data with a clear bullish Break of Structure.

    Builds a series with explicit swing highs and a breakout.
    Uses no random noise for reliability.
    """
    n = 60
    base_time = datetime(2024, 1, 1)
    times = [base_time + timedelta(hours=i) for i in range(n)]

    closes = []
    for i in range(n):
        if i < 8:
            price = 100.0 + i * 1.0       # rise to 108
        elif i < 14:
            price = 108.0 - (i - 8) * 0.8   # dip to 103.2
        elif i < 20:
            price = 103.2 + (i - 14) * 1.2  # rise to 110.4  ← swing high
        elif i < 26:
            price = 110.4 - (i - 20) * 0.8  # dip to 105.6  ← swing low
        elif i < 32:
            price = 105.6 + (i - 26) * 0.4  # slow rise to 108.0 (consolidation below 110.4)
        else:
            price = 108.0 + (i - 32) * 1.5  # BREAK above 110.4 → BOS
        closes.append(price)

    closes = np.array(closes)
    # Make high/low include the close with a small spread.
    highs = closes + 0.5
    lows = closes - 0.5
    opens = closes - 0.2

    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes,
         "tick_volume": np.full(n, 500.0), "spread": np.full(n, 2.0)},
        index=times,
    )
    df.index.name = "time"
    return df


# =====================================================================
# Tests
# =====================================================================


class TestSwingPointDetection:
    """Swing point detection in market structure analyzer."""

    def test_swing_point_detection(self, sample_ohlcdf):
        "Uptrending data → should find swing highs and swing lows."
        analyzer = MarketStructureAnalyzer(swing_order=3)
        swing_highs, swing_lows = analyzer.find_swing_points(sample_ohlcdf)
        # With 100 bars of uptrending data, we should find at least some
        # swing highs and lows.
        assert len(swing_highs) > 0
        assert len(swing_lows) > 0

    def test_swing_points_are_peaks(self, sample_ohlcdf):
        "Every swing high should have type='high', every low type='low'."
        analyzer = MarketStructureAnalyzer(swing_order=3)
        highs, lows = analyzer.find_swing_points(sample_ohlcdf)
        for sh in highs:
            assert sh.type == "high"
        for sl in lows:
            assert sl.type == "low"


class TestTrendIdentification:
    """Trend identification from swing point analysis."""

    def test_trend_identification_up(self):
        "Clear uptrend → TrendDirection.UP."
        df = _make_uptrend_df()
        analyzer = MarketStructureAnalyzer(swing_order=3)
        trend = analyzer.identify_trend(df, lookback=50)
        assert trend == TrendDirection.UP

    def test_trend_identification_down(self):
        "Clear downtrend → TrendDirection.DOWN."
        df = _make_downtrend_df()
        analyzer = MarketStructureAnalyzer(swing_order=3)
        trend = analyzer.identify_trend(df, lookback=50)
        assert trend == TrendDirection.DOWN


class TestSRDetection:
    """Support/Resistance level detection."""

    def test_sr_detection(self):
        "Data bouncing between 100 and 110 → should find levels."
        df = _make_sr_df()
        detector = SupportResistanceDetector(lookback=80, min_touches=2)
        levels = detector.detect_levels(df, n_levels=5)
        # Should find at least 1 S/R level with the bouncing data.
        assert len(levels) >= 1

    def test_sr_levels_have_correct_types(self):
        "Each level should be 'support' or 'resistance'."
        df = _make_sr_df()
        detector = SupportResistanceDetector(lookback=80, min_touches=2)
        levels = detector.detect_levels(df)
        for lv in levels:
            assert lv.type in ("support", "resistance")
            assert lv.touches >= 2
            assert lv.strength >= 2


class TestBOSDetection:
    """Break of Structure detection."""

    def test_bos_detection(self):
        "Data with clear break of structure → should detect BOS."
        df = _make_bos_df()
        analyzer = MarketStructureAnalyzer(swing_order=3)
        swing_highs, swing_lows = analyzer.find_swing_points(df)
        bos_list = analyzer.detect_bos(df, swing_highs, swing_lows)
        # With a clear uptrend breaking above consolidation, should find BOS.
        assert len(bos_list) >= 1
        assert bos_list[0].type == "BOS"


class TestMarketBiasConfluence:
    """Market bias from structure + CHOCH."""

    def test_confluence_with_market_structure(self):
        "BOS bullish + uptrend → bullish bias."
        df = _make_uptrend_df()
        analyzer = MarketStructureAnalyzer(swing_order=3)
        bias = analyzer.get_market_bias(df)
        # An uptrend without bearish CHOCH should be BULLISH.
        assert bias == MarketBias.BULLISH

    def test_downtrend_bias(self):
        "Clear downtrend → BEARISH bias."
        df = _make_downtrend_df()
        analyzer = MarketStructureAnalyzer(swing_order=3)
        bias = analyzer.get_market_bias(df)
        assert bias == MarketBias.BEARISH


class TestStructureAnalysis:
    """Full identify_structure snapshot."""

    def test_identify_structure_returns_keys(self, sample_ohlcdf):
        "identify_structure returns a dict with expected keys."
        analyzer = MarketStructureAnalyzer(swing_order=3)
        result = analyzer.identify_structure(sample_ohlcdf)
        expected_keys = {"trend", "swing_highs", "swing_lows", "last_bos", "last_choch", "structure_label"}
        assert set(result.keys()) == expected_keys
