"""General-purpose helper functions for the MT5 AI Trader project.

Provides price/volume normalisation, ATR calculation, pip conversions,
SL/TP validation, and MT5 filling-mode detection.  All functions use
explicit type hints and are safe for use in the trading pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from models.enums import TradeDirection

if TYPE_CHECKING:
    import MetaTrader5 as mt5

__all__ = [
    "normalize_price",
    "normalize_volume",
    "calculate_atr",
    "calculate_atr_value",
    "pips_to_price",
    "price_to_pips",
    "is_valid_sl_tp",
    "get_filling_mode",
]


# ---------------------------------------------------------------------------
# Price / Volume normalisation
# ---------------------------------------------------------------------------


def normalize_price(price: float, digits: int) -> float:
    """Round *price* to the symbol's decimal digit count.

    Parameters
    ----------
    price:
        The raw price value to normalise.
    digits:
        Number of decimal places the symbol uses (e.g. ``5`` for most
        forex pairs, ``2`` for JPY pairs).

    Returns
    -------
    float
        The price rounded to *digits* decimal places.
    """
    return round(price, digits)


def normalize_volume(
    volume: float,
    volume_step: float,
    volume_min: float,
    volume_max: float,
) -> float:
    """Round *volume* to the broker's lot step and clamp to ``[min, max]``.

    The volume is first rounded **down** to the nearest multiple of
    *volume_step*, then clamped so that ``volume_min <= result <= volume_max``.

    Parameters
    ----------
    volume:
        Desired volume (lots).
    volume_step:
        Minimum volume increment allowed by the broker.
    volume_min:
        Minimum allowable volume.
    volume_max:
        Maximum allowable volume.

    Returns
    -------
    float
        Normalised volume within the broker's constraints.
    """
    if volume_step <= 0:
        raise ValueError(f"volume_step must be positive, got {volume_step}")

    # Round down to the nearest step.
    steps = int(volume / volume_step)
    normalized = steps * volume_step

    # Clamp to allowed range.
    normalized = max(volume_min, min(normalized, volume_max))

    return float(normalized)


# ---------------------------------------------------------------------------
# ATR calculation
# ---------------------------------------------------------------------------


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute the Average True Range (ATR) over a candle DataFrame.

    True Range for each bar is defined as::

        TR = max(H - L, |H - prev_close|, |L - prev_close|)

    The first bar (where there is no previous close) uses ``H - L``
    as its True Range.  The ATR is the simple rolling mean of TR over
    *period* bars.

    Parameters
    ----------
    df:
        OHLC DataFrame with at least columns ``'high'``, ``'low'``,
        and ``'close'``.
    period:
        Look-back window for the rolling mean.  Defaults to ``14``.

    Returns
    -------
    pd.Series
        ATR series indexed like *df*.  The first *period - 1* rows
        are ``NaN``.
    """
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    prev_close = close.shift(1)

    # Components of True Range.
    tr_hl = high - low
    tr_hc = (high - prev_close).abs()
    tr_lc = (low - prev_close).abs()

    # First row: prev_close is NaN so hc/lc are NaN; fall back to H-L.
    true_range = pd.concat([tr_hl, tr_hc, tr_lc], axis=1).max(axis=1)

    # For the very first row where prev_close is NaN, max(axis=1) across
    # [H-L, NaN, NaN] correctly yields H-L.

    atr = true_range.rolling(window=period, min_periods=period).mean()

    return atr


def calculate_atr_value(df: pd.DataFrame, period: int = 14) -> float:
    """Return the latest (most recent) ATR value as a plain float.

    Parameters
    ----------
    df:
        OHLC DataFrame passed to :func:`calculate_atr`.
    period:
        Look-back window.  Defaults to ``14``.

    Returns
    -------
    float
        The ATR value of the last row, or ``0.0`` if the DataFrame
        does not contain enough bars to compute a valid ATR.
    """
    atr_series = calculate_atr(df, period=period)

    if atr_series.empty or pd.isna(atr_series.iloc[-1]):
        return 0.0

    return float(atr_series.iloc[-1])


# ---------------------------------------------------------------------------
# Pip conversions
# ---------------------------------------------------------------------------


def pips_to_price(pips: float, point: float) -> float:
    """Convert a pip value to the equivalent price distance.

    Most forex pairs: 1 pip = 10 points.  JPY pairs: 1 pip = 100 points.
    The caller is responsible for passing the correct *point* value
    from the symbol specification.

    Parameters
    ----------
    pips:
        Number of pips.
    point:
        The symbol's point value (smallest price increment).

    Returns
    -------
    float
        Price distance corresponding to *pips*.
    """
    return pips * point * 10.0


def price_to_pips(distance: float, point: float) -> float:
    """Convert a price distance to the equivalent pip value.

    Parameters
    ----------
    distance:
        Price distance to convert.
    point:
        The symbol's point value (smallest price increment).

    Returns
    -------
    float
        Number of pips represented by *distance*.
    """
    if point == 0:
        return 0.0
    return distance / (point * 10.0)


# ---------------------------------------------------------------------------
# SL / TP validation
# ---------------------------------------------------------------------------


def is_valid_sl_tp(
    entry: float,
    sl: float,
    tp: float,
    direction: str,
    point: float,
) -> tuple[bool, str]:
    """Validate stop-loss and take-profit relative to entry and direction.

    For a **BUY** (long) position: ``SL < entry < TP``.
    For a **SELL** (short) position: ``SL > entry > TP``.

    A small tolerance of ``point * 0.5`` is applied to handle
    floating-point rounding on the broker side.

    Parameters
    ----------
    entry:
        The intended entry price.
    sl:
        The stop-loss price.
    tp:
        The take-profit price.
    direction:
        Trade direction as a string — ``"BUY"``, ``"SELL"``, or a
        :class:`~models.enums.TradeDirection` value.
    point:
        The symbol's point value, used as a rounding tolerance.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` when valid, or ``(False, reason)`` with a
        human-readable explanation when invalid.
    """
    # Normalise direction string — handle enum before calling .upper().
    if hasattr(direction, "value"):  # Enum support
        dir_str = str(direction.value).upper()
    else:
        dir_str = str(direction).upper()

    # Accept both "BUY"/"SELL" and "LONG"/"SHORT".
    if dir_str in ("BUY", "LONG"):
        # SL must be below entry, TP must be above entry.
        if sl >= entry:
            return False, f"BUY: SL ({sl}) must be below entry ({entry})"
        if tp <= entry:
            return False, f"BUY: TP ({tp}) must be above entry ({entry})"
        return True, ""

    if dir_str in ("SELL", "SHORT"):
        # SL must be above entry, TP must be below entry.
        if sl <= entry:
            return False, f"SELL: SL ({sl}) must be above entry ({entry})"
        if tp >= entry:
            return False, f"SELL: TP ({tp}) must be below entry ({entry})"
        return True, ""

    return False, f"Unknown direction: {direction!r}"


# ---------------------------------------------------------------------------
# MT5 filling mode
# ---------------------------------------------------------------------------


def get_filling_mode(symbol_info_obj: object) -> int:
    """Determine the correct order-filling mode for an MT5 symbol.

    MetaTrader 5 exposes ``symbol_info.filling_mode`` as a bit-field
    integer.  This function checks the bits in priority order:

    1. ``SYMBOL_FILLING_FOK`` (``1``) → return ``mt5.ORDER_FILLING_FOK``
    2. ``SYMBOL_FILLING_IOC`` (``2``) → return ``mt5.ORDER_FILLING_IOC``
    3. Fallback → return ``mt5.ORDER_FILLING_RETURN``

    Parameters
    ----------
    symbol_info_obj:
        An MT5 ``SymbolInfo`` named-tuple (the object returned by
        ``mt5.symbol_info(symbol)``).

    Returns
    -------
    int
        One of ``mt5.ORDER_FILLING_FOK``, ``mt5.ORDER_FILLING_IOC``,
        or ``mt5.ORDER_FILLING_RETURN``.
    """
    import MetaTrader5 as mt5

    # Bit masks defined by MT5 for filling_mode.
    SYMBOL_FILLING_FOK = 1
    SYMBOL_FILLING_IOC = 2

    filling_mode = getattr(symbol_info_obj, "filling_mode", None)

    if filling_mode is None:
        return mt5.ORDER_FILLING_RETURN

    if filling_mode & SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK

    if filling_mode & SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC

    return mt5.ORDER_FILLING_RETURN
