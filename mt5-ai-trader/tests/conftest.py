"""Shared pytest fixtures for the MT5 AI Trader test suite.

All tests must be runnable without MetaTrader5 installed.
Synthetic data is used throughout.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

# ── Mock MetaTrader5 so the entire project can be imported without MT5 ──
if "MetaTrader5" not in sys.modules:
    _mt5_mock = MagicMock()
    _mt5_mock.ORDER_FILLING_FOK = 0
    _mt5_mock.ORDER_FILLING_IOC = 1
    _mt5_mock.ORDER_FILLING_RETURN = 2
    sys.modules["MetaTrader5"] = _mt5_mock

# Ensure the project root is on sys.path so absolute imports
# (e.g. ``from models.enums import SignalType``) resolve correctly
# when running ``python -m pytest tests/`` from the project root.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from models.market import SymbolSpec


# =====================================================================
# OHLCV DataFrame fixture
# =====================================================================


@pytest.fixture
def sample_ohlcdf(n: int = 100, trend: str = "up"):
    """Return a synthetic OHLCV DataFrame.

    Parameters
    ----------
    n : int
        Number of bars to generate.
    trend : str
        One of ``'up'``, ``'down'``, ``'range'``.
    """
    np.random.seed(42)
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    times = [base_time + timedelta(hours=i) for i in range(n)]

    if trend == "up":
        # Generally rising closes with noise.
        drift = np.linspace(100, 200, n)
        noise = np.random.normal(0, 1.5, n)
        closes = drift + noise
    elif trend == "down":
        drift = np.linspace(200, 100, n)
        noise = np.random.normal(0, 1.5, n)
        closes = drift + noise
    else:  # range
        closes = np.random.normal(150, 2, n)

    opens = closes + np.random.normal(0, 0.5, n)
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0.5, 0.3, n))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0.5, 0.3, n))
    volumes = np.random.randint(100, 1000, n).astype(float)
    spreads = np.random.randint(1, 5, n).astype(float)

    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "tick_volume": volumes,
            "spread": spreads,
        },
        index=times,
    )
    df.index.name = "time"
    return df


# =====================================================================
# SymbolSpec fixtures
# =====================================================================


@pytest.fixture
def gold_spec():
    """SymbolSpec with Gold-like values (XAUUSD)."""
    return SymbolSpec(
        name="XAUUSD",
        bid=2000.00,
        ask=2000.10,
        spread=10.0,
        point=0.01,
        digits=2,
        trade_allowed=True,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        tick_value=1.0,
        tick_size=0.01,
        volume_contract_size=100.0,
        trade_mode=0,
        filling_mode=1,
    )


@pytest.fixture
def btc_spec():
    """SymbolSpec with BTC-like values (BTCUSD)."""
    return SymbolSpec(
        name="BTCUSD",
        bid=40000.00,
        ask=40000.10,
        spread=10.0,
        point=0.01,
        digits=2,
        trade_allowed=True,
        volume_min=0.01,
        volume_max=50.0,
        volume_step=0.01,
        tick_value=1.0,
        tick_size=0.01,
        volume_contract_size=1.0,
        trade_mode=0,
        filling_mode=1,
    )


@pytest.fixture
def forex_spec():
    """SymbolSpec with EURUSD-like values."""
    return SymbolSpec(
        name="EURUSD",
        bid=1.10000,
        ask=1.10010,
        spread=1.0,
        point=0.00001,
        digits=5,
        trade_allowed=True,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        tick_value=1.0,
        tick_size=0.00001,
        volume_contract_size=100000.0,
        trade_mode=0,
        filling_mode=1,
    )
