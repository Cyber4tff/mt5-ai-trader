"""
Configuration module for MT5 AI Trader.

All sensitive values come from environment variables.
Broker contract specs (min_lot, max_lot, etc.) are NOT hardcoded here
because they vary per symbol and must be fetched from MT5 at runtime.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── Server ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = "./logs/trader.log"

    # ── Security ───────────────────────────────────────────
    secret_key: str = "CHANGE-ME"

    # ── MT5 ────────────────────────────────────────────────
    mt5_path: str = ""

    # ── Broker server name registry ────────────────────────
    # These are server *name patterns* used at login, NOT
    # contract specifications.  Actual lot/point/tick details
    # are fetched from MT5 at runtime per-symbol.
    brokers: Dict[str, Dict] = {
        "exness": {
            "name": "Exness",
            "servers": {
                "demo": "Exness-MT5Trial",
                "real": "Exness-MT5Real",
                "demo2": "Exness-MT5Trial2",
                "real2": "Exness-MT5Real2",
            },
        },
        "octafx": {
            "name": "OctaFX",
            "servers": {
                "demo": "OctaFX-Demo",
                "real": "OctaFX-Real",
            },
        },
        "headway": {
            "name": "Headway",
            "servers": {
                "demo": "Headway-Demo",
                "real": "Headway-Real",
            },
        },
    }

    # ── Trading parameters ─────────────────────────────────
    trading_symbols: List[str] = ["BTCUSD", "XAUUSD"]
    default_timeframe: str = "H1"

    # Multi-timeframe hierarchy (higher → lower)
    mtf_timeframes: List[str] = ["D1", "H4", "H1", "M15", "M5"]

    # ── Risk management ────────────────────────────────────
    risk_per_trade: float = 0.02
    max_daily_drawdown_pct: float = 0.06
    max_consecutive_losses: int = 3
    max_open_positions: int = 3
    max_trades_per_day: int = 10
    max_spread_points: int = 50
    min_risk_reward: float = 1.5
    magic_number: int = 234000

    # ── Trailing stop ──────────────────────────────────────
    trailing_stop_enabled: bool = True
    trailing_stop_atr_multiplier: float = 1.5

    # ── Naked Forex strategy tunables ──────────────────────
    naked_forex: Dict = {
        "room_to_left": 7,
        "max_room_to_left": 20,
        "min_candle_body_ratio": 0.6,
        "engulfing_multiplier": 1.2,
        "pin_bar_tail_ratio": 0.7,
        "support_resistance_lookback": 50,
        "trend_lookback": 20,
        "atr_period": 14,
        "sr_touch_tolerance_atr_mult": 0.3,
    }

    # ── AI / confirmation ──────────────────────────────────
    ai_confidence_threshold: float = 0.65
    ai_high_confidence: float = 0.80

    # ── Mode ───────────────────────────────────────────────
    trading_mode: str = "demo"

    @property
    def is_demo_mode(self) -> bool:
        return self.trading_mode.lower() == "demo"


settings = Settings()
