"""Tests for is_valid_sl_tp from utils/helpers."""

import pytest

from utils.helpers import is_valid_sl_tp


class TestSLTPValidation:
    """SL/TP validation logic."""

    def test_buy_valid_sl_tp(self):
        "BUY, entry=1.1000, sl=1.0950, tp=1.1100 → valid."
        valid, reason = is_valid_sl_tp(1.1000, 1.0950, 1.1100, "BUY", 0.00001)
        assert valid is True
        assert reason == ""

    def test_sell_valid_sl_tp(self):
        "SELL, entry=1.1000, sl=1.1050, tp=1.0900 → valid."
        valid, reason = is_valid_sl_tp(1.1000, 1.1050, 1.0900, "SELL", 0.00001)
        assert valid is True
        assert reason == ""

    def test_buy_invalid_sl_above_entry(self):
        "BUY, entry=1.1000, sl=1.1050 → invalid."
        valid, reason = is_valid_sl_tp(1.1000, 1.1050, 1.1100, "BUY", 0.00001)
        assert valid is False
        assert "SL" in reason

    def test_sell_invalid_sl_below_entry(self):
        "SELL, entry=1.1000, sl=1.0950 → invalid."
        valid, reason = is_valid_sl_tp(1.1000, 1.0950, 1.0900, "SELL", 0.00001)
        assert valid is False
        assert "SL" in reason

    def test_buy_invalid_tp_below_entry(self):
        "BUY, entry=1.1000, tp=1.0950 → invalid."
        valid, reason = is_valid_sl_tp(1.1000, 1.0900, 1.0950, "BUY", 0.00001)
        assert valid is False
        assert "TP" in reason

    def test_sell_invalid_tp_above_entry(self):
        "SELL, entry=1.1000, sl=1.1050, tp=1.1010 → TP above entry, invalid."
        valid, reason = is_valid_sl_tp(1.1000, 1.1050, 1.1010, "SELL", 0.00001)
        assert valid is False
        assert "TP" in reason

    def test_long_direction_alias(self):
        "LONG is accepted as alias for BUY."
        valid, reason = is_valid_sl_tp(1.1000, 1.0950, 1.1100, "LONG", 0.00001)
        assert valid is True

    def test_short_direction_alias(self):
        "SHORT is accepted as alias for SELL."
        valid, reason = is_valid_sl_tp(1.1000, 1.1050, 1.0900, "SHORT", 0.00001)
        assert valid is True

    def test_unknown_direction(self):
        "Unknown direction → invalid."
        valid, reason = is_valid_sl_tp(1.1000, 1.0950, 1.1100, "HOLD", 0.00001)
        assert valid is False
        assert "Unknown" in reason

    def test_enum_direction(self):
        "TradeDirection enum is handled correctly."
        from models.enums import TradeDirection
        valid, reason = is_valid_sl_tp(
            1.1000, 1.0950, 1.1100, TradeDirection.LONG, 0.00001
        )
        assert valid is True
