"""Tests for utility helper functions."""

import numpy as np
import pandas as pd
import pytest

from utils.helpers import (
    calculate_atr,
    calculate_atr_value,
    normalize_price,
    normalize_volume,
    pips_to_price,
)


class TestNormalizePrice:
    """Price rounding tests."""

    def test_normalize_price_2_digits(self):
        "1.123456 → 1.12."
        assert normalize_price(1.123456, 2) == pytest.approx(1.12)

    def test_normalize_price_5_digits(self):
        "1.123456 → 1.12346."
        assert normalize_price(1.123456, 5) == pytest.approx(1.12346)

    def test_normalize_price_0_digits(self):
        "1.7 → 2."
        assert normalize_price(1.7, 0) == pytest.approx(2.0)


class TestNormalizeVolume:
    """Volume rounding and clamping tests."""

    def test_normalize_volume_standard(self):
        "0.015 with step 0.01 → rounds DOWN to 0.01."
        result = normalize_volume(0.015, 0.01, 0.01, 100.0)
        assert result == pytest.approx(0.01)

    def test_normalize_volume_micro(self):
        "0.015 → round(0.015/0.01)*0.01 = int(1.5)*0.01 = 1*0.01 = 0.01 (floor)."
        # The function uses int() which truncates (floors for positive).
        result = normalize_volume(0.015, 0.01, 0.01, 100.0)
        assert result == pytest.approx(0.01)

    def test_normalize_volume_clamp_min(self):
        "0.001 → clamped to 0.01."
        result = normalize_volume(0.001, 0.01, 0.01, 100.0)
        assert result == pytest.approx(0.01)

    def test_normalize_volume_clamp_max(self):
        "500 → clamped to 100.0."
        result = normalize_volume(500.0, 0.01, 0.01, 100.0)
        assert result == pytest.approx(100.0)

    def test_normalize_volume_exact_step(self):
        "0.05 with step 0.01 → 0.05."
        result = normalize_volume(0.05, 0.01, 0.01, 100.0)
        assert result == pytest.approx(0.05)

    def test_normalize_volume_zero_step_raises(self):
        "volume_step=0 → raises ValueError."
        with pytest.raises(ValueError, match="volume_step must be positive"):
            normalize_volume(1.0, 0.0, 0.01, 100.0)


class TestATR:
    """ATR calculation tests."""

    def test_calculate_atr(self):
        "Known data → verify ATR calculation."
        # Create a DataFrame where every bar has H-L = 2.0
        n = 20
        data = {
            "high": [102.0] * n,
            "low": [100.0] * n,
            "close": [101.0] * n,
        }
        df = pd.DataFrame(data)
        atr = calculate_atr(df, period=14)
        # All bars have same H-L=2, close-prev_close=0
        # TR = max(2, 0, 0) = 2.0 for every bar.
        # ATR = rolling mean of 2.0 over 14 bars = 2.0
        assert atr.iloc[-1] == pytest.approx(2.0, abs=1e-10)

    def test_calculate_atr_value(self):
        "calculate_atr_value returns the last ATR as float."
        n = 20
        data = {
            "high": [52.0] * n,
            "low": [50.0] * n,
            "close": [51.0] * n,
        }
        df = pd.DataFrame(data)
        atr_val = calculate_atr_value(df, period=14)
        assert atr_val == pytest.approx(2.0, abs=1e-10)

    def test_calculate_atr_insufficient_data(self):
        "Not enough data for ATR → returns 0.0."
        data = {
            "high": [52.0, 53.0],
            "low": [50.0, 51.0],
            "close": [51.0, 52.0],
        }
        df = pd.DataFrame(data)
        atr_val = calculate_atr_value(df, period=14)
        assert atr_val == 0.0


class TestPipsToPrice:
    """Pip ↔ price conversion tests."""

    def test_pips_to_price(self):
        "10 pips * 0.00001 point = 10 * 0.00001 * 10 = 0.001."
        # pips_to_price multiplies by point * 10
        result = pips_to_price(10, 0.00001)
        assert result == pytest.approx(0.001)

    def test_pips_to_price_gold(self):
        "10 pips for gold (point=0.01) = 10 * 0.01 * 10 = 1.0."
        result = pips_to_price(10, 0.01)
        assert result == pytest.approx(1.0)
