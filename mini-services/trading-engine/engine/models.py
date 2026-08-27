from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple
import time
import uuid


# ── Enums ─────────────────────────────────────────────────────────


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


class TrendDirection(Enum):
    UP = "UP"
    DOWN = "DOWN"
    RANGING = "RANGING"


class MarketBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PatternName(Enum):
    BIG_SHADOW_BULL = "BIG_SHADOW_BULL"
    BIG_SHADOW_BEAR = "BIG_SHADOW_BEAR"
    KANGAROO_TAIL_BULL = "KANGAROO_TAIL_BULL"
    KANGAROO_TAIL_BEAR = "KANGAROO_TAIL_BEAR"
    LAST_KISS_BULL = "LAST_KISS_BULL"
    LAST_KISS_BEAR = "LAST_KISS_BEAR"
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"
    DOUBLE_TOP = "DOUBLE_TOP"
    NONE = "NONE"


# ── Market Data Models ─────────────────────────────────────────────


@dataclass
class SwingPoint:
    price: float
    type: Literal["high", "low"]
    index: int
    strength: int


@dataclass
class SRLevel:
    price: float
    type: Literal["support", "resistance"]
    strength: int
    touches: int
    touch_times: List = field(default_factory=list)
    last_touch_time: Optional[float] = None
    zone_high: Optional[float] = None
    zone_low: Optional[float] = None


@dataclass
class StructureBreak:
    type: Literal["BOS", "CHOCH"]
    direction: Literal["bullish", "bearish"]
    price: float
    time: float
    index: int
    from_level: Optional[float] = None


@dataclass
class TradeSignal:
    symbol: str
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    pattern: PatternName
    timeframe: str
    reason: str
    risk_reward: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class MarketAnalysis:
    timeframe: str
    trend: TrendDirection
    bias: MarketBias
    atr: Optional[float] = None
    atr_percentile: Optional[float] = None
    volatility_regime: Optional[str] = None
    structure_breaks: List = field(default_factory=list)
    sr_levels: List = field(default_factory=list)
    momentum: Optional[str] = None
    signals: List[TradeSignal] = field(default_factory=list)


# ── Paper Trading Models ──────────────────────────────────────────


@dataclass
class PaperPosition:
    ticket: int
    symbol: str
    type: Literal["BUY", "SELL"]
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    open_time: str
    comment: str
    swap: float = 0.0

    @property
    def profit(self) -> float:
        spec = self._get_spec()
        tick_val = spec.get("tick_value", 1.0) if spec else 1.0
        point = spec.get("point", 0.00001) if spec else 0.00001
        if point == 0:
            return 0.0
        ticks_diff = (self.current_price - self.open_price) / point
        if self.type == "SELL":
            ticks_diff = -ticks_diff
        return round(ticks_diff * tick_val * self.volume, 2)

    def _get_spec(self) -> Optional[Dict]:
        from engine.settings import settings
        return settings.SYMBOL_SPECS.get(self.symbol)

    def to_dict(self) -> Dict:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.type,
            "volume": self.volume,
            "open_price": self.open_price,
            "current_price": self.current_price,
            "sl": self.sl,
            "tp": self.tp,
            "profit": self.profit,
            "swap": self.swap,
            "comment": self.comment,
            "time": self.open_time,
        }


@dataclass
class PaperAccount:
    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: int
    margin_level: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "margin": self.margin,
            "free_margin": self.free_margin,
            "leverage": self.leverage,
            "profit": self.equity - self.balance,
            "margin_level": self.margin_level,
        }


@dataclass
class DailyRisk:
    date: str
    realized_pnl: float = 0.0
    trades_count: int = 0
    consecutive_losses: int = 0
    remaining_trades: int = 10
    remaining_loss_limit: float = 600.0

    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "realized_pnl": self.realized_pnl,
            "trades_count": self.trades_count,
            "consecutive_losses": self.consecutive_losses,
            "remaining_trades": self.remaining_trades,
            "remaining_loss_limit": self.remaining_loss_limit,
        }


# ── Session ───────────────────────────────────────────────────────


class TradingSession:
    def __init__(
        self,
        broker: str = "Paper Trading",
        account_type: str = "paper",
        login: int = 0,
        password: str = "",
        balance: float = 10000.0,
        leverage: int = 100,
    ):
        self.session_id: str = uuid.uuid4().hex[:16]
        self.broker: str = broker
        self.server: str = f"{broker}-Paper"
        self.mode: str = account_type
        self.login: int = login
        self.created_at: float = time.time()

        self.balance: float = balance
        self.initial_balance: float = balance
        self.leverage: int = leverage

        self.positions: List[PaperPosition] = []
        self.closed_today: List[Dict] = []  # closed trades today
        self.next_ticket: int = 100000 + int(time.time() % 100000)

        # Daily risk tracking
        self.daily_risk = DailyRisk(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            remaining_trades=10,
            remaining_loss_limit=balance * 0.06,
        )

        # Auto-trade state
        self.auto_trade_enabled: bool = False
        self.auto_trade_interval: int = 15  # minutes
        self.auto_trade_last_scan: Optional[float] = None

        # Market data cache
        self.price_cache: Dict[str, float] = {}  # symbol -> current price

    def get_account(self) -> PaperAccount:
        total_profit = sum(p.profit for p in self.positions)
        equity = self.balance + total_profit
        margin = sum(p.volume * p.open_price / self.leverage for p in self.positions)
        free_margin = equity - margin
        margin_level = (equity / margin * 100) if margin > 0 else 0.0

        return PaperAccount(
            balance=round(self.balance, 2),
            equity=round(equity, 2),
            margin=round(margin, 2),
            free_margin=round(max(0, free_margin), 2),
            leverage=self.leverage,
            margin_level=round(margin_level, 1),
        )

    def reset_daily_risk(self):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.daily_risk.date != today:
            self.daily_risk = DailyRisk(
                date=today,
                remaining_trades=10,
                remaining_loss_limit=self.balance * 0.06,
            )
            self.closed_today = []
