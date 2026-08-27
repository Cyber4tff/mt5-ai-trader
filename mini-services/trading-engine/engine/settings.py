from __future__ import annotations

from typing import Dict, List


class Settings:
    """Cloud trading engine settings. No MT5 dependency."""

    # ── Server ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = True

    # ── Trading symbols (yfinance format) ───────────────────
    # Maps display name to yfinance ticker
    SYMBOL_MAP: Dict[str, str] = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCHF": "USDCHF=X",
        "USDCAD": "USDCAD=X",
        "NZDUSD": "NZDUSD=X",
        "XAUUSD": "GC=F",
        "BTCUSD": "BTC-USD",
        "ETHUSD": "ETH-USD",
    }

    DEFAULT_SYMBOLS: List[str] = ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD"]

    # ── Multi-timeframe hierarchy (higher → lower) ──────────
    # Use 3 key TFs for faster scans. Full 5-TF available on demand.
    MTF_TIMEFRAMES: List[str] = ["1d", "1h", "15m"]
    FULL_MTF_TIMEFRAMES: List[str] = ["1d", "4h", "1h", "15m", "5m"]

    # ── Risk management ────────────────────────────────────
    risk_per_trade: float = 0.02          # 2% per trade
    max_daily_drawdown_pct: float = 0.06  # 6% max daily loss
    max_consecutive_losses: int = 3
    max_open_positions: int = 3
    max_trades_per_day: int = 10
    min_risk_reward: float = 1.5

    # ── Naked Forex strategy ────────────────────────────────
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

    # ── AI confidence thresholds ────────────────────────────
    ai_confidence_threshold: float = 0.65
    ai_high_confidence: float = 0.80

    # ── Default paper trading balance ──────────────────────
    default_balance: float = 10000.0
    default_leverage: int = 100

    # ── Symbol specs for paper trading ─────────────────────
    # Used for P&L calculation and position sizing
    SYMBOL_SPECS: Dict[str, Dict] = {
        "EURUSD": {"digits": 5, "point": 0.00001, "tick_value": 1.0, "pip_value": 10.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "GBPUSD": {"digits": 5, "point": 0.00001, "tick_value": 1.0, "pip_value": 10.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "USDJPY": {"digits": 3, "point": 0.001, "tick_value": 0.8333, "pip_value": 8.33, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "AUDUSD": {"digits": 5, "point": 0.00001, "tick_value": 1.0, "pip_value": 10.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "USDCHF": {"digits": 5, "point": 0.00001, "tick_value": 1.1, "pip_value": 11.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "USDCAD": {"digits": 5, "point": 0.00001, "tick_value": 0.73, "pip_value": 7.3, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "NZDUSD": {"digits": 5, "point": 0.00001, "tick_value": 1.0, "pip_value": 10.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 100.0},
        "XAUUSD": {"digits": 2, "point": 0.01, "tick_value": 1.0, "pip_value": 1.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 50.0},
        "BTCUSD": {"digits": 2, "point": 0.01, "tick_value": 1.0, "pip_value": 1.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 10.0},
        "ETHUSD": {"digits": 2, "point": 0.01, "tick_value": 1.0, "pip_value": 1.0, "trade_lot_step": 0.01, "trade_lot_min": 0.01, "trade_lot_max": 50.0},
    }


settings = Settings()
