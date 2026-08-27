"""Tests for RiskManager — all risk gate checks."""

from unittest.mock import MagicMock

import pytest

from models.enums import MarketBias, SignalType
from models.signals import AIDecision
from risk.manager import DailyState, RiskManager


# =====================================================================
# Mock connector
# =====================================================================


class MockConnector:
    """Minimal mock of MT5Connector for risk tests."""

    def __init__(self, spread_points: int = 10, history_deals=None, positions=None):
        self._spread = spread_points
        self._deals = history_deals or []
        self._positions = positions or []

    def get_history_deals(self, days: int = 1):
        return self._deals

    def get_current_spread_points(self, symbol: str) -> int:
        return self._spread

    def get_positions(self, symbol: str = None):
        return self._positions


# =====================================================================
# Helpers
# =====================================================================


def _make_decision(
    direction=SignalType.BUY,
    confidence=0.80,
    stop_loss=1.0900,
    take_profit=1.1200,
    risk_reward=2.0,
) -> AIDecision:
    """Build a valid AIDecision with sensible defaults."""
    return AIDecision(
        direction=direction,
        confidence=confidence,
        market_bias=MarketBias.BULLISH,
        entry_zone=(1.1000, 1.1000),
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_reward=risk_reward,
    )


def _make_risk_manager(connector=None, daily_state=None) -> RiskManager:
    """Create a RiskManager with an optional pre-set daily state."""
    if connector is None:
        connector = MockConnector()
    rm = RiskManager(connector)
    if daily_state is not None:
        rm.daily_state = daily_state
    return rm


# =====================================================================
# Tests
# =====================================================================


class TestRiskLimits:
    """RiskManager.check_all and check_spread."""

    def test_no_trade_decision(self):
        "AI says NO_TRADE → check_all returns (False, [...])."
        rm = _make_risk_manager()
        decision = _make_decision(direction=SignalType.NO_TRADE)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("NO TRADE" in f for f in failures)

    def test_missing_sl(self):
        "decision with stop_loss=None → rejected."
        rm = _make_risk_manager()
        decision = _make_decision(stop_loss=None)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("stop loss" in f.lower() for f in failures)

    def test_missing_tp(self):
        "decision with take_profit=None → rejected."
        rm = _make_risk_manager()
        decision = _make_decision(take_profit=None)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("take profit" in f.lower() for f in failures)

    def test_daily_drawdown_limit(self):
        "Daily loss exceeds max_drawdown_pct → rejected."
        # $10k balance, 6% max drawdown = $600 max loss.
        # Set realized_pnl to -$700.
        ds = DailyState(realized_pnl=-700.0)
        rm = _make_risk_manager(daily_state=ds)
        decision = _make_decision()
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("Daily loss" in f for f in failures)

    def test_consecutive_losses_limit(self):
        "consecutive_losses >= max (3) → rejected."
        ds = DailyState(consecutive_losses=3)
        rm = _make_risk_manager(daily_state=ds)
        decision = _make_decision()
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("Consecutive" in f for f in failures)

    def test_max_open_positions(self):
        "open_positions_count >= max (3) → rejected."
        rm = _make_risk_manager()
        decision = _make_decision()
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=3)
        assert allowed is False
        assert any("Max open positions" in f for f in failures)

    def test_max_trades_per_day(self):
        "trades_count >= max (10) → rejected."
        ds = DailyState(trades_count=10)
        rm = _make_risk_manager(daily_state=ds)
        decision = _make_decision()
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("Max daily trades" in f for f in failures)

    def test_low_risk_reward(self):
        "decision.risk_reward < min (1.5) → rejected."
        rm = _make_risk_manager()
        decision = _make_decision(risk_reward=1.2)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("R:R too low" in f for f in failures)

    def test_low_confidence(self):
        "decision.confidence < threshold (0.65) → rejected."
        rm = _make_risk_manager()
        decision = _make_decision(confidence=0.50)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("Confidence" in f for f in failures)

    def test_all_checks_pass(self):
        "Valid decision with all params correct → (True, [])."
        rm = _make_risk_manager()
        decision = _make_decision(confidence=0.80, risk_reward=2.0)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is True
        assert failures == []

    def test_spread_too_high(self):
        "mock spread > max_spread_points (50) → check_spread returns (False, ...)."
        connector = MockConnector(spread_points=60)
        rm = _make_risk_manager(connector=connector)
        ok, msg = rm.check_spread("EURUSD")
        assert ok is False
        assert "Spread too high" in msg

    def test_spread_ok(self):
        "Spread within limits → check_spread returns (True, ...)."
        connector = MockConnector(spread_points=10)
        rm = _make_risk_manager(connector=connector)
        ok, msg = rm.check_spread("EURUSD")
        assert ok is True
        assert "OK" in msg

    def test_missing_risk_reward(self):
        "risk_reward=None → rejected with 'R:R is missing'."
        rm = _make_risk_manager()
        decision = _make_decision(risk_reward=None)
        allowed, failures = rm.check_all("EURUSD", decision, balance=10_000, open_positions_count=0)
        assert allowed is False
        assert any("R:R is missing" in f for f in failures)
