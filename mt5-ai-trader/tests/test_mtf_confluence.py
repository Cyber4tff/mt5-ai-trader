"""Tests for MultiTimeframeAnalyzer — TF ranking and confluence."""

from unittest.mock import MagicMock

import pytest

from models.enums import MarketBias, TrendDirection
from models.signals import MarketAnalysis
from strategies.multi_timeframe import MultiTimeframeAnalyzer


# =====================================================================
# Helper: build a concrete strategy stub so MultiTimeframeAnalyzer can
# be instantiated (it requires a BaseStrategy subclass).
# =====================================================================


class _StubStrategy:
    """Minimal strategy stub satisfying the BaseStrategy interface."""

    name = "stub"

    def analyze(self, df, symbol, timeframe, symbol_spec=None, sr_levels=None):
        return []

    def identify_trend(self, df, lookback=20):
        return TrendDirection.RANGING

    def calculate_atr(self, df, period=14):
        from utils.helpers import calculate_atr
        return calculate_atr(df, period)


def _make_analyzer() -> MultiTimeframeAnalyzer:
    return MultiTimeframeAnalyzer(strategy=_StubStrategy())


def _make_analysis(tf: str, bias: MarketBias) -> MarketAnalysis:
    """Build a MarketAnalysis with the given bias."""
    return MarketAnalysis(
        timeframe=tf,
        trend=TrendDirection.UP,
        bias=bias,
        atr=1.0,
    )


class TestMTFConfluence:
    """Multi-timeframe confluence and ranking tests."""

    def test_tf_ranking(self):
        "D1 < H4 < H1 < M15 < M5."
        analyzer = _make_analyzer()
        ranks = {
            "D1": analyzer.get_tf_rank("D1"),
            "H4": analyzer.get_tf_rank("H4"),
            "H1": analyzer.get_tf_rank("H1"),
            "M15": analyzer.get_tf_rank("M15"),
            "M5": analyzer.get_tf_rank("M5"),
        }
        assert ranks["D1"] < ranks["H4"] < ranks["H1"] < ranks["M15"] < ranks["M5"]

    def test_higher_timeframes(self):
        "For H1, higher should be [D1, H4]."
        analyzer = _make_analyzer()
        higher = analyzer.get_higher_timeframes("H1")
        assert higher == ["D1", "H4"]

    def test_lower_timeframes(self):
        "For H4, lower should be [H1, M15, M5]."
        analyzer = _make_analyzer()
        lower = analyzer.get_lower_timeframes("H4")
        assert lower == ["H1", "M15", "M5"]

    def test_bullish_confluence(self):
        "4 MarketAnalysis all BULLISH → direction='bullish', score=1.0."
        analyzer = _make_analyzer()
        analyses = {
            "D1": _make_analysis("D1", MarketBias.BULLISH),
            "H4": _make_analysis("H4", MarketBias.BULLISH),
            "H1": _make_analysis("H1", MarketBias.BULLISH),
            "M15": _make_analysis("M15", MarketBias.BULLISH),
        }
        result = analyzer.compute_confluence(analyses)
        assert result["direction"] == "bullish"
        assert result["score"] == pytest.approx(1.0)
        assert result["trend_alignment"] is True

    def test_mixed_confluence(self):
        "2 bullish, 2 bearish → direction='neutral', score=0.5."
        analyzer = _make_analyzer()
        analyses = {
            "D1": _make_analysis("D1", MarketBias.BULLISH),
            "H4": _make_analysis("H4", MarketBias.BEARISH),
            "H1": _make_analysis("H1", MarketBias.BULLISH),
            "M15": _make_analysis("M15", MarketBias.BEARISH),
        }
        result = analyzer.compute_confluence(analyses)
        assert result["direction"] == "neutral"
        assert result["score"] == pytest.approx(0.5)

    def test_bearish_confluence(self):
        "3 bearish, 1 neutral → direction='bearish', score=0.75."
        analyzer = _make_analyzer()
        analyses = {
            "D1": _make_analysis("D1", MarketBias.BEARISH),
            "H4": _make_analysis("H4", MarketBias.BEARISH),
            "H1": _make_analysis("H1", MarketBias.BEARISH),
            "M15": _make_analysis("M15", MarketBias.NEUTRAL),
        }
        result = analyzer.compute_confluence(analyses)
        assert result["direction"] == "bearish"
        assert result["score"] == pytest.approx(0.75)

    def test_empty_analyses(self):
        "No analyses → neutral with score 0."
        analyzer = _make_analyzer()
        result = analyzer.compute_confluence({})
        assert result["direction"] == "neutral"
        assert result["score"] == 0.0

    def test_higher_tf_bias(self):
        "higher_tf_bias comes from the highest non-neutral TF."
        analyzer = _make_analyzer()
        analyses = {
            "D1": _make_analysis("D1", MarketBias.BEARISH),
            "H4": _make_analysis("H4", MarketBias.BULLISH),
            "H1": _make_analysis("H1", MarketBias.BULLISH),
        }
        result = analyzer.compute_confluence(analyses)
        assert result["higher_tf_bias"] == MarketBias.BEARISH
