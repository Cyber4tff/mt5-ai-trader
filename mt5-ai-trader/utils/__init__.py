"""Utility package for the MT5 AI Trader project.

Re-exports all public helpers and the logging setup so that consumers
can write, for example::

    from utils import setup_logging, normalize_price, logger
"""

from utils.helpers import (
    calculate_atr,
    calculate_atr_value,
    get_filling_mode,
    is_valid_sl_tp,
    normalize_price,
    normalize_volume,
    pips_to_price,
    price_to_pips,
)
from utils.logging import logger, setup_logging

__all__ = [
    # logging
    "setup_logging",
    "logger",
    # helpers
    "normalize_price",
    "normalize_volume",
    "calculate_atr",
    "calculate_atr_value",
    "pips_to_price",
    "price_to_pips",
    "is_valid_sl_tp",
    "get_filling_mode",
]
