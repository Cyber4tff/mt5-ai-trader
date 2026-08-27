"""Market data fetcher using yfinance. No MT5 dependency.

Fetches real OHLCV candle data for forex, gold, and crypto.
Uses aggressive caching to minimize API calls.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from engine.settings import settings

# Cache: (symbol, interval) -> (timestamp, DataFrame)
_data_cache: Dict[Tuple[str, str], Tuple[float, pd.DataFrame]] = {}
CACHE_TTL = 300  # 5 minutes

# How much data to fetch per timeframe
YF_PERIOD_MAP = {
    "1d": "120d",
    "4h": "30d",
    "1h": "10d",
    "15m": "5d",
    "5m": "2d",
}


def get_yf_ticker(symbol: str) -> str:
    """Convert display symbol to yfinance ticker."""
    return settings.SYMBOL_MAP.get(symbol, f"{symbol}=X")


def fetch_candles(symbol: str, interval: str = "1h", period: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candles from yfinance with caching."""
    cache_key = (symbol, interval)
    now = time.time()

    # Check cache
    if cache_key in _data_cache:
        cached_time, cached_df = _data_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_df.copy()

    yf_ticker = get_yf_ticker(symbol)
    if period is None:
        period = YF_PERIOD_MAP.get(interval, "10d")

    try:
        ticker = yf.Ticker(yf_ticker)
        df = ticker.history(period=period, interval=interval, prepost=False)

        if df is None or df.empty:
            print(f"[DataFetcher] No data for {symbol} {interval}")
            return None

        # Normalize columns
        df = df.rename(columns={
            "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])

        if len(df) < 30:
            return None

        _data_cache[cache_key] = (now, df.copy())
        print(f"[DataFetcher] Fetched {symbol} {interval}: {len(df)} candles")
        return df

    except Exception as e:
        print(f"[DataFetcher] Error fetching {symbol} {interval}: {e}")
        return None


def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch the latest current price for a symbol."""
    yf_ticker = get_yf_ticker(symbol)
    try:
        ticker = yf.Ticker(yf_ticker)
        price = ticker.fast_info.last_price
        if price and price > 0:
            return float(price)

        df = ticker.history(period="2d", interval="1d")
        if df is not None and not df.empty:
            return float(df.iloc[-1]["Close"])

        return None
    except Exception as e:
        print(f"[DataFetcher] Error fetching price for {symbol}: {e}")
        return None


def get_available_symbols() -> Dict[str, Dict]:
    """Return dict of supported symbols with their latest prices."""
    result = {}
    for symbol in settings.DEFAULT_SYMBOLS:
        price = fetch_current_price(symbol)
        if price:
            result[symbol] = {"price": price, "ticker": get_yf_ticker(symbol)}
    return result


def invalidate_cache(symbol: Optional[str] = None):
    """Clear cache for a symbol or all symbols."""
    if symbol:
        keys_to_remove = [k for k in _data_cache if k[0] == symbol]
        for k in keys_to_remove:
            del _data_cache[k]
    else:
        _data_cache.clear()
