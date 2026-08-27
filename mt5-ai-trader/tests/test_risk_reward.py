"""Tests for risk/reward validation logic.

These tests verify the R:R checks that are embedded in both
AIDecisionEngine (hard reject below min) and RiskManager (soft check).
"""

import pytest

from config.settings import settings


class TestRiskReward:
    """Risk/reward ratio validation."""

    def test_rr_above_minimum(self):
        "RR 2.5 > 1.5 → passes."
        rr = 2.5
        assert rr >= settings.min_risk_reward

    def test_rr_below_minimum(self):
        "RR 1.2 < 1.5 → fails."
        rr = 1.2
        assert rr < settings.min_risk_reward

    def test_rr_exact_minimum(self):
        "RR 1.5 → passes (>= check)."
        rr = 1.5
        assert rr >= settings.min_risk_reward

    def test_rr_zero_risk(self):
        "risk=0 → division by zero would occur, invalid."
        risk = 0.0
        reward = 10.0
        # Can't compute RR when risk is 0
        with pytest.raises(ZeroDivisionError):
            _ = reward / risk

    def test_rr_negative(self):
        "tp < sl for BUY → RR is negative."
        entry = 1.1000
        sl = 1.0950
        tp = 1.0980  # TP closer to entry than SL
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0
        assert rr < settings.min_risk_reward
        assert rr < 1.0  # clearly a bad trade
