"""Tests for signal creation and AI decision engine."""

import pytest

from models.enums import MarketBias, PatternName, SignalType
from models.signals import AIDecision, MarketAnalysis, TradeSignal
from ai_layer.decision_engine import AIDecisionEngine


# =====================================================================
# Helpers
# =====================================================================


def _buy_signal(confidence=0.80, risk_reward=2.5) -> TradeSignal:
    """Create a bullish TradeSignal."""
    return TradeSignal(
        symbol="EURUSD",
        signal_type=SignalType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1225,
        confidence=confidence,
        pattern=PatternName.BIG_SHADOW_BULL,
        timeframe="H1",
        reason="Strong bullish engulfing",
        risk_reward=risk_reward,
    )


def _sell_signal(confidence=0.75, risk_reward=2.0) -> TradeSignal:
    """Create a bearish TradeSignal."""
    return TradeSignal(
        symbol="EURUSD",
        signal_type=SignalType.SELL,
        entry_price=1.1000,
        stop_loss=1.1050,
        take_profit=1.0700,
        confidence=confidence,
        pattern=PatternName.KANGAROO_TAIL_BEAR,
        timeframe="H1",
        reason="Bearish pin bar at resistance",
        risk_reward=risk_reward,
    )


def _bullish_confluence() -> dict:
    """Confluence dict with bullish HTF bias and high score."""
    return {
        "direction": "bullish",
        "score": 0.80,
        "higher_tf_bias": MarketBias.BULLISH,
        "trend_alignment": True,
        "factors": [],
        "bullish_ratio": 0.80,
        "bearish_ratio": 0.20,
    }


def _bearish_confluence() -> dict:
    """Confluence dict with bearish HTF bias."""
    return {
        "direction": "bearish",
        "score": 0.80,
        "higher_tf_bias": MarketBias.BEARISH,
        "trend_alignment": True,
        "factors": [],
        "bullish_ratio": 0.20,
        "bearish_ratio": 0.80,
    }


class TestSignalCreation:
    """TradeSignal and AIDecision dataclass tests."""

    def test_buy_signal_creation(self):
        "Create a TradeSignal with BUY, valid params → verify all fields."
        sig = _buy_signal()
        assert sig.signal_type == SignalType.BUY
        assert sig.symbol == "EURUSD"
        assert sig.entry_price == 1.1000
        assert sig.stop_loss == 1.0950
        assert sig.take_profit == 1.1225
        assert sig.confidence == 0.80
        assert sig.pattern == PatternName.BIG_SHADOW_BULL
        assert sig.timeframe == "H1"
        assert sig.risk_reward == 2.5
        assert isinstance(sig.metadata, dict)

    def test_sell_signal_creation(self):
        "Create a TradeSignal with SELL."
        sig = _sell_signal()
        assert sig.signal_type == SignalType.SELL
        assert sig.entry_price == 1.1000
        assert sig.stop_loss == 1.1050
        assert sig.take_profit == 1.0700

    def test_no_trade_decision(self):
        "Create AIDecision with NO_TRADE direction."
        dec = AIDecision(
            direction=SignalType.NO_TRADE,
            confidence=0.0,
            market_bias=MarketBias.NEUTRAL,
            entry_zone=(1.1000, 1.1000),
            rejection_reasons=["No clear signal"],
        )
        assert dec.direction == SignalType.NO_TRADE
        assert dec.confidence == 0.0


class TestAIDecision:
    """AI Decision Engine evaluation tests."""

    def test_ai_rejects_low_confidence(self):
        "Signal with confidence=0.3 → evaluate should return NO_TRADE."
        engine = AIDecisionEngine(confidence_threshold=0.65, high_confidence=0.80)
        sig = _buy_signal(confidence=0.30, risk_reward=2.5)
        confluence = _bullish_confluence()
        decision = engine.evaluate(sig, {}, confluence)
        assert decision.direction == SignalType.NO_TRADE

    def test_ai_rejects_bad_risk_reward(self):
        "Signal with RR=0.8 → evaluate should return NO_TRADE (hard reject)."
        engine = AIDecisionEngine(confidence_threshold=0.65, high_confidence=0.80)
        sig = _buy_signal(confidence=0.80, risk_reward=0.8)
        confluence = _bullish_confluence()
        decision = engine.evaluate(sig, {}, confluence)
        assert decision.direction == SignalType.NO_TRADE
        assert any("R:R" in r for r in decision.rejection_reasons)

    def test_ai_rejects_htf_conflict(self):
        "Bullish signal but HTF bias is BEARISH → should reject."
        engine = AIDecisionEngine(confidence_threshold=0.65, high_confidence=0.80)
        sig = _buy_signal(confidence=0.55, risk_reward=1.6)
        # HTF bias conflicts → -0.20; confluence score 0.4 → -0.15
        confluence = {
            "direction": "bearish",
            "score": 0.4,
            "higher_tf_bias": MarketBias.BEARISH,
            "trend_alignment": False,
            "factors": [],
            "bullish_ratio": 0.25,
            "bearish_ratio": 0.75,
        }
        decision = engine.evaluate(sig, {}, confluence)
        assert decision.direction == SignalType.NO_TRADE

    def test_ai_approves_strong_signal(self):
        "Strong bullish signal, HTF bullish, good RR → should approve."
        engine = AIDecisionEngine(confidence_threshold=0.65, high_confidence=0.80)
        sig = _buy_signal(confidence=0.75, risk_reward=2.5)
        confluence = _bullish_confluence()
        decision = engine.evaluate(sig, {}, confluence)
        assert decision.direction == SignalType.BUY
        assert decision.confidence >= 0.65
        assert decision.stop_loss == sig.stop_loss
        assert decision.take_profit == sig.take_profit

    def test_score_signal(self):
        "score_signal returns a 0-1 float."
        engine = AIDecisionEngine()
        sig = _buy_signal(confidence=0.75, risk_reward=2.5)
        score = engine.score_signal(sig)
        assert 0.0 <= score <= 1.0
