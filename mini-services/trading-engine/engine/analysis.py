"""Complete analysis engine for cloud trading system.

Port of the MT5 AI Trader analysis pipeline:
- ATR calculation
- Support/Resistance detection
- Market Structure (BOS, CHOCH, swing points)
- Naked Forex patterns (Big Shadow, Kangaroo Tail, Last Kiss, Double Hit)
- Multi-Timeframe confluence
- AI Decision (9-check risk gate)

All analysis uses pandas DataFrames with columns:
  open, high, low, close, volume
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine.models import (
    MarketAnalysis,
    MarketBias,
    PatternName,
    SignalType,
    SRLevel,
    StructureBreak,
    SwingPoint,
    TradeSignal,
    TrendDirection,
)
from engine.settings import settings


# ====================================================================
# ATR Calculation
# ====================================================================


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr_hl = high - low
    tr_hc = (high - prev_close).abs()
    tr_lc = (low - prev_close).abs()
    true_range = pd.concat([tr_hl, tr_hc, tr_lc], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    return atr


def calculate_atr_value(df: pd.DataFrame, period: int = 14) -> float:
    atr_series = calculate_atr(df, period=period)
    if atr_series.empty or pd.isna(atr_series.iloc[-1]):
        return 0.0
    return float(atr_series.iloc[-1])


# ====================================================================
# Support & Resistance Detection
# ====================================================================


class SupportResistanceDetector:
    def __init__(self, lookback: int = 50, min_touches: int = 2, atr_tolerance_mult: float = 0.3):
        self.lookback = lookback
        self.min_touches = min_touches
        self.atr_tolerance_mult = atr_tolerance_mult

    def find_swing_points(self, df: pd.DataFrame, order: int = 3) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        n = len(df)

        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []

        for i in range(order, n - order):
            h_slice = highs[i - order : i + order + 1]
            if highs[i] == np.max(h_slice) and np.sum(highs[i] == h_slice) == 1:
                strength = min(3, max(1, int(np.sum(highs[i] > h_slice) / 2)))
                swing_highs.append(SwingPoint(price=float(highs[i]), type="high", index=int(i), strength=strength))

            l_slice = lows[i - order : i + order + 1]
            if lows[i] == np.min(l_slice) and np.sum(lows[i] == l_slice) == 1:
                strength = min(3, max(1, int(np.sum(lows[i] < l_slice) / 2)))
                swing_lows.append(SwingPoint(price=float(lows[i]), type="low", index=int(i), strength=strength))

        cutoff = max(0, n - self.lookback)
        swing_highs = [p for p in swing_highs if p.index >= cutoff]
        swing_lows = [p for p in swing_lows if p.index >= cutoff]

        return swing_highs, swing_lows

    def detect_levels(self, df: pd.DataFrame, n_levels: int = 5) -> List[SRLevel]:
        atr = calculate_atr_value(df, period=14)
        if atr <= 0:
            atr = float((df["high"].astype(float) - df["low"].astype(float)).tail(14).mean())
        if atr <= 0:
            return []

        tolerance = atr * self.atr_tolerance_mult
        swing_highs, swing_lows = self.find_swing_points(df)
        all_points = swing_highs + swing_lows

        if not all_points:
            return []

        clusters: List[List[SwingPoint]] = []
        assigned = [False] * len(all_points)

        for i, pt in enumerate(all_points):
            if assigned[i]:
                continue
            cluster = [pt]
            assigned[i] = True
            for j in range(i + 1, len(all_points)):
                if assigned[j]:
                    continue
                if any(abs(all_points[j].price - cp.price) <= tolerance for cp in cluster):
                    cluster.append(all_points[j])
                    assigned[j] = True
            clusters.append(cluster)

        levels: List[SRLevel] = []
        for cluster in clusters:
            if len(cluster) < self.min_touches:
                continue
            prices = np.array([p.price for p in cluster])
            avg_price = float(np.mean(prices))
            zone_high = float(np.max(prices))
            zone_low = float(np.min(prices))
            touch_count = len(cluster)
            high_count = sum(1 for p in cluster if p.type == "high")
            low_count = sum(1 for p in cluster if p.type == "low")
            level_type = "resistance" if high_count >= low_count else "support"
            strength = min(5, touch_count)
            touch_indices = [p.index for p in cluster]

            levels.append(SRLevel(
                price=avg_price, type=level_type, strength=strength,
                touches=touch_count, touch_times=touch_indices,
                last_touch_time=float(max(touch_indices)),
                zone_high=zone_high, zone_low=zone_low,
            ))

        levels.sort(key=lambda lv: (lv.strength, lv.touches), reverse=True)
        return levels[:n_levels]

    def find_nearest_support(self, price: float, levels: List[SRLevel]) -> Optional[SRLevel]:
        supports = [lv for lv in levels if lv.type == "support" and lv.price < price]
        return min(supports, key=lambda lv: price - lv.price) if supports else None

    def find_nearest_resistance(self, price: float, levels: List[SRLevel]) -> Optional[SRLevel]:
        resistances = [lv for lv in levels if lv.type == "resistance" and lv.price > price]
        return min(resistances, key=lambda lv: lv.price - price) if resistances else None

    def is_near_level(self, price: float, level: SRLevel, atr: float) -> bool:
        if level.zone_low is not None and level.zone_high is not None:
            if level.zone_low <= price <= level.zone_high:
                return True
        tolerance = atr * self.atr_tolerance_mult
        return abs(price - level.price) <= tolerance


# ====================================================================
# Market Structure Analysis (BOS / CHOCH)
# ====================================================================


class MarketStructureAnalyzer:
    def __init__(self, swing_order: int = 3):
        self.swing_order = swing_order

    def find_swing_points(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        n = len(df)
        order = self.swing_order

        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []

        for i in range(order, n - order):
            h_slice = highs[i - order : i + order + 1]
            if highs[i] == np.max(h_slice) and np.sum(highs[i] == h_slice) == 1:
                swing_highs.append(SwingPoint(price=float(highs[i]), type="high", index=int(i), strength=1))

            l_slice = lows[i - order : i + order + 1]
            if lows[i] == np.min(l_slice) and np.sum(lows[i] == l_slice) == 1:
                swing_lows.append(SwingPoint(price=float(lows[i]), type="low", index=int(i), strength=1))

        return swing_highs, swing_lows

    def identify_structure(self, df: pd.DataFrame) -> Dict:
        swing_highs, swing_lows = self.find_swing_points(df)
        trend = self._classify_swing_pattern(swing_highs, swing_lows)

        bos_list = self.detect_bos(df, swing_highs, swing_lows)
        choch_list = self.detect_choch(df, swing_highs, swing_lows, trend)

        last_bos = bos_list[-1] if bos_list else None
        last_choch = choch_list[-1] if choch_list else None

        if trend == "bullish":
            structure_label = "Bullish (HH + HL)"
        elif trend == "bearish":
            structure_label = "Bearish (LH + LL)"
        else:
            structure_label = "Ranging (mixed)"

        if last_choch is not None:
            structure_label += f" | CHOCH {last_choch.direction}"

        return {
            "trend": trend,
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "last_bos": last_bos,
            "last_choch": last_choch,
            "structure_label": structure_label,
        }

    def detect_bos(self, df: pd.DataFrame, swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> List[StructureBreak]:
        if not swing_highs or not swing_lows:
            return []

        closes = df["close"].astype(float).values
        n = len(df)
        results: List[StructureBreak] = []
        current_trend = self._classify_swing_pattern(swing_highs, swing_lows)

        all_swings = sorted(
            [("high", s) for s in swing_highs] + [("low", s) for s in swing_lows],
            key=lambda x: x[1].index,
        )

        last_sh: Optional[SwingPoint] = None
        last_sl: Optional[SwingPoint] = None

        for sw_type, sw_point in all_swings:
            if sw_type == "high":
                last_sh = sw_point
            else:
                last_sl = sw_point

            start_bar = sw_point.index + 1
            if start_bar >= n:
                continue

            if current_trend == "bullish" and last_sh is not None:
                for bar_i in range(start_bar, n):
                    if closes[bar_i] > last_sh.price:
                        results.append(StructureBreak(
                            type="BOS", direction="bullish", price=float(closes[bar_i]),
                            time=float(bar_i), index=bar_i, from_level=last_sh.price,
                        ))
                        break
            elif current_trend == "bearish" and last_sl is not None:
                for bar_i in range(start_bar, n):
                    if closes[bar_i] < last_sl.price:
                        results.append(StructureBreak(
                            type="BOS", direction="bearish", price=float(closes[bar_i]),
                            time=float(bar_i), index=bar_i, from_level=last_sl.price,
                        ))
                        break

        return results

    def detect_choch(self, df: pd.DataFrame, swing_highs: List[SwingPoint], swing_lows: List[SwingPoint], current_trend: str) -> List[StructureBreak]:
        if current_trend == "ranging" or not swing_highs or not swing_lows:
            return []

        closes = df["close"].astype(float).values
        n = len(df)
        results: List[StructureBreak] = []

        if current_trend == "bullish" and swing_lows:
            last_sl = swing_lows[-1]
            for bar_i in range(last_sl.index + 1, n):
                if closes[bar_i] < last_sl.price:
                    results.append(StructureBreak(
                        type="CHOCH", direction="bearish", price=float(closes[bar_i]),
                        time=float(bar_i), index=bar_i, from_level=last_sl.price,
                    ))
                    break
        elif current_trend == "bearish" and swing_highs:
            last_sh = swing_highs[-1]
            for bar_i in range(last_sh.index + 1, n):
                if closes[bar_i] > last_sh.price:
                    results.append(StructureBreak(
                        type="CHOCH", direction="bullish", price=float(closes[bar_i]),
                        time=float(bar_i), index=bar_i, from_level=last_sh.price,
                    ))
                    break

        return results

    def identify_trend(self, df: pd.DataFrame, lookback: int = 20) -> TrendDirection:
        n = len(df)
        cutoff = max(0, n - lookback)
        swing_highs, swing_lows = self.find_swing_points(df)
        recent_highs = [s for s in swing_highs if s.index >= cutoff]
        recent_lows = [s for s in swing_lows if s.index >= cutoff]

        if len(recent_highs) < 2 and len(recent_lows) < 2:
            return TrendDirection.RANGING

        hh = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i].price > recent_highs[i - 1].price)
        hl = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i].price > recent_lows[i - 1].price)
        lh = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i].price < recent_highs[i - 1].price)
        ll = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i].price < recent_lows[i - 1].price)

        bullish_score = hh + hl
        bearish_score = lh + ll

        if bullish_score > bearish_score and bullish_score >= 1:
            return TrendDirection.UP
        if bearish_score > bullish_score and bearish_score >= 1:
            return TrendDirection.DOWN
        return TrendDirection.RANGING

    def get_market_bias(self, df: pd.DataFrame) -> MarketBias:
        structure = self.identify_structure(df)
        trend = structure["trend"]
        last_choch = structure["last_choch"]

        if trend == "bullish":
            if last_choch is not None and last_choch.direction == "bearish":
                return MarketBias.NEUTRAL
            return MarketBias.BULLISH
        if trend == "bearish":
            if last_choch is not None and last_choch.direction == "bullish":
                return MarketBias.NEUTRAL
            return MarketBias.BEARISH
        return MarketBias.NEUTRAL

    @staticmethod
    def _classify_swing_pattern(swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> str:
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "ranging"

        recent_h = swing_highs[-min(3, len(swing_highs)):]
        recent_l = swing_lows[-min(3, len(swing_lows)):]

        hh = sum(1 for i in range(1, len(recent_h)) if recent_h[i].price > recent_h[i - 1].price)
        hl = sum(1 for i in range(1, len(recent_l)) if recent_l[i].price > recent_l[i - 1].price)
        lh = sum(1 for i in range(1, len(recent_h)) if recent_h[i].price < recent_h[i - 1].price)
        ll = sum(1 for i in range(1, len(recent_l)) if recent_l[i].price < recent_l[i - 1].price)

        bullish = hh + hl
        bearish = lh + ll
        if bullish > bearish:
            return "bullish"
        if bearish > bullish:
            return "bearish"
        return "ranging"


# ====================================================================
# Naked Forex Pattern Detection
# ====================================================================


class NakedForexStrategy:
    name: str = "naked_forex"

    def __init__(self):
        self.config = settings.naked_forex
        self.sr_detector = SupportResistanceDetector(
            lookback=self.config["support_resistance_lookback"],
            atr_tolerance_mult=self.config.get("sr_touch_tolerance_atr_mult", 0.3),
        )
        self.structure_analyzer = MarketStructureAnalyzer()

    def identify_trend(self, df: pd.DataFrame, lookback: Optional[int] = None) -> TrendDirection:
        if lookback is None:
            lookback = self.config["trend_lookback"]
        return self.structure_analyzer.identify_trend(df.tail(lookback))

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        return calculate_atr(df, period)

    def get_latest_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        return calculate_atr_value(df, period)

    def _has_room_to_left(self, df: pd.DataFrame, idx: int) -> bool:
        min_candles = self.config["room_to_left"]
        max_candles = self.config["max_room_to_left"]
        if idx < min_candles:
            return False

        left = df.iloc[max(0, idx - max_candles):idx]
        if len(left) == 0:
            return False

        curr_range = float(df.iloc[idx]["high"] - df.iloc[idx]["low"])
        if curr_range == 0:
            return False

        similar_bodies = ((abs(left["close"] - left["open"]) / curr_range) > 0.7).sum()
        return int(similar_bodies) == 0

    def is_big_shadow(self, df: pd.DataFrame, idx: int) -> tuple:
        """Naked Forex 'Big Shadow' — a strong engulfing candle whose body
        completely contains the previous candle's body. Must have room to
        the left (no similar-sized bodies nearby) and be at least 1.2x the
        previous candle's range.
        """
        if idx < 1:
            return False, ""
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        o, h, l, c = float(curr["open"]), float(curr["high"]), float(curr["low"]), float(curr["close"])
        po, ph, pl, pc = float(prev["open"]), float(prev["high"]), float(prev["low"]), float(prev["close"])

        curr_body_lo = min(o, c)
        curr_body_hi = max(o, c)
        prev_body_lo = min(po, pc)
        prev_body_hi = max(po, pc)

        # Full engulfing: current body must COMPLETELY contain previous body
        if curr_body_lo > prev_body_lo or curr_body_hi < prev_body_hi:
            return False, ""

        # Current candle must be significantly larger (at least 1.2x range)
        curr_range = h - l
        prev_range = ph - pl
        if curr_range == 0 or prev_range == 0:
            return False, ""
        if curr_range < prev_range * self.config["engulfing_multiplier"]:
            return False, ""

        # Body must be substantial (>= 60% of total range, not a doji)
        body_ratio = abs(c - o) / curr_range
        if body_ratio < self.config["min_candle_body_ratio"]:
            return False, ""
        # Room to left: no similar-sized candles in recent history
        if not self._has_room_to_left(df, idx):
            return False, ""

        return (True, "big_shadow_bullish") if c > o else (True, "big_shadow_bearish")

    def is_kangaroo_tail(self, df: pd.DataFrame, idx: int) -> tuple:
        if idx < 1:
            return False, ""
        curr = df.iloc[idx]
        o, h, l, c = float(curr["open"]), float(curr["high"]), float(curr["low"]), float(curr["close"])

        curr_range = h - l
        if curr_range == 0:
            return False, ""

        body = abs(c - o)
        body_ratio = body / curr_range
        pin_tail_ratio = self.config["pin_bar_tail_ratio"]

        if body_ratio > (1 - pin_tail_ratio):
            return False, ""

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        if lower_wick > upper_wick:
            if lower_wick < 2 * upper_wick or lower_wick / curr_range < pin_tail_ratio:
                return False, ""
        else:
            if upper_wick < 2 * lower_wick or upper_wick / curr_range < pin_tail_ratio:
                return False, ""

        if not self._has_room_to_left(df, idx):
            return False, ""

        return (True, "kangaroo_tail_bullish") if lower_wick > upper_wick else (True, "kangaroo_tail_bearish")

    def is_last_kiss(self, df: pd.DataFrame, idx: int, sr_levels: list) -> tuple:
        if idx < 3 or not sr_levels:
            return False, ""

        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr <= 0:
            return False, ""

        curr = df.iloc[idx]
        curr_close = float(curr["close"])
        curr_body = abs(float(curr["close"]) - float(curr["open"]))
        curr_range = float(curr["high"]) - float(curr["low"])
        if curr_range == 0:
            return False, ""
        if curr_body / curr_range < self.config["min_candle_body_ratio"]:
            return False, ""

        for level in sr_levels:
            if not self.sr_detector.is_near_level(curr_close, level, atr):
                continue
            for lookback in range(1, 4):
                if idx - lookback < 0:
                    continue
                prev = df.iloc[idx - lookback]
                prev_close = float(prev["close"])

                if level.type == "support":
                    if prev_close < level.price and curr_close >= level.price * 0.998:
                        if float(curr["close"]) > float(curr["open"]):
                            return True, "last_kiss_bullish"
                elif level.type == "resistance":
                    if prev_close > level.price and curr_close <= level.price * 1.002:
                        if float(curr["close"]) < float(curr["open"]):
                            return True, "last_kiss_bearish"

        return False, ""

    def is_double_hit(self, df: pd.DataFrame, idx: int) -> tuple:
        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr <= 0:
            return False, ""

        curr = df.iloc[idx]
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        tolerance = atr * 0.3
        min_lookback = 5
        max_lookback = 15

        # Double Bottom
        for j in range(idx - max_lookback, idx - min_lookback):
            if j < 0:
                continue
            other = df.iloc[j]
            if abs(curr_low - float(other["low"])) > tolerance:
                continue
            mid_slice = df.iloc[j + 1:idx]
            if len(mid_slice) == 0:
                continue
            if float(mid_slice["high"].max()) > curr_low + tolerance:
                return True, "double_bottom"

        # Double Top
        for j in range(idx - max_lookback, idx - min_lookback):
            if j < 0:
                continue
            other = df.iloc[j]
            if abs(curr_high - float(other["high"])) > tolerance:
                continue
            mid_slice = df.iloc[j + 1:idx]
            if len(mid_slice) == 0:
                continue
            if float(mid_slice["low"].min()) < curr_high - tolerance:
                return True, "double_top"

        return False, ""

    _PATTERN_MAP = {
        "big_shadow_bullish": PatternName.BIG_SHADOW_BULL,
        "big_shadow_bearish": PatternName.BIG_SHADOW_BEAR,
        "kangaroo_tail_bullish": PatternName.KANGAROO_TAIL_BULL,
        "kangaroo_tail_bearish": PatternName.KANGAROO_TAIL_BEAR,
        "last_kiss_bullish": PatternName.LAST_KISS_BULL,
        "last_kiss_bearish": PatternName.LAST_KISS_BEAR,
        "double_bottom": PatternName.DOUBLE_BOTTOM,
        "double_top": PatternName.DOUBLE_TOP,
    }

    def _create_signal(self, df, idx, pattern_str, symbol, timeframe, sr_levels, trend) -> Optional[TradeSignal]:
        is_bullish = "bullish" in pattern_str or "bottom" in pattern_str
        is_bearish = "bearish" in pattern_str or "top" in pattern_str

        # FIXED trend filter: allow with-trend, reject counter-trend
        if is_bullish and trend == TrendDirection.DOWN:
            return None
        if is_bearish and trend == TrendDirection.UP:
            return None

        atr = self.get_latest_atr(df, self.config["atr_period"])
        if atr == 0:
            return None

        candle = df.iloc[idx]
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])

        if is_bullish:
            entry = candle_high + atr * 0.1
            sl = candle_low - atr * 0.5
            nearest_sr = self.sr_detector.find_nearest_resistance(entry, sr_levels)
            tp = nearest_sr.price if nearest_sr else entry + 3 * atr
        else:
            entry = candle_low - atr * 0.1
            sl = candle_high + atr * 0.5
            nearest_sr = self.sr_detector.find_nearest_support(entry, sr_levels)
            tp = nearest_sr.price if nearest_sr else entry - 3 * atr

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return None
        rr = reward / risk
        if rr < settings.min_risk_reward:
            return None

        confidence = 0.4
        if (is_bullish and trend == TrendDirection.UP) or (is_bearish and trend == TrendDirection.DOWN):
            confidence += 0.25
        elif trend == TrendDirection.RANGING:
            confidence += 0.05
        if nearest_sr:
            confidence += 0.15
        if "big_shadow" in pattern_str:
            confidence += 0.10
        elif "kangaroo" in pattern_str:
            confidence += 0.08
        elif "last_kiss" in pattern_str:
            confidence += 0.07
        elif "double" in pattern_str:
            confidence += 0.09
        confidence = min(confidence, 1.0)

        signal_type = SignalType.BUY if is_bullish else SignalType.SELL
        pattern_enum = self._PATTERN_MAP.get(pattern_str, PatternName.NONE)

        return TradeSignal(
            symbol=symbol, signal_type=signal_type, entry_price=entry,
            stop_loss=sl, take_profit=tp, confidence=confidence,
            pattern=pattern_enum, timeframe=timeframe,
            reason=f"{pattern_str} at {trend.value} market",
            risk_reward=rr,
        )

    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str, sr_levels=None) -> list:
        if df is None or len(df) < 50:
            return []

        trend = self.identify_trend(df)
        if sr_levels is None:
            sr_levels = self.sr_detector.detect_levels(df)

        signals: list = []
        start = max(10, len(df) - 10)
        end = len(df) - 1

        for i in range(start, end):
            for pattern_fn in [self.is_big_shadow, self.is_kangaroo_tail, self.is_double_hit]:
                valid, name = pattern_fn(df, i)
                if valid:
                    sig = self._create_signal(df, i, name, symbol, timeframe, sr_levels, trend)
                    if sig:
                        signals.append(sig)

            valid, name = self.is_last_kiss(df, i, sr_levels)
            if valid:
                sig = self._create_signal(df, i, name, symbol, timeframe, sr_levels, trend)
                if sig:
                    signals.append(sig)

        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals[:3]


class NakedForexScalperStrategy(NakedForexStrategy):
    """Naked Forex Scalping Strategy for fast short-duration trades (1m, 5m, 15m timeframes).
    Features tight ATR stop-losses, fast 1:1.5 - 1:2 R:R targets, and micro-structure pinbar/engulfing triggers.
    """
    name: str = "naked_forex_scalper"

    def analyze_scalp(self, df: pd.DataFrame, symbol: str, timeframe: str = "5m", sr_levels=None) -> list:
        if df is None or len(df) < 20:
            return []

        trend = self.identify_trend(df.tail(30))
        if sr_levels is None:
            sr_levels = self.sr_detector.detect_levels(df, n_levels=3)

        signals = []
        last_idx = len(df) - 1

        for pattern_fn in [self.is_big_shadow, self.is_kangaroo_tail]:
            valid, name = pattern_fn(df, last_idx)
            if not valid and last_idx >= 1:
                valid, name = pattern_fn(df, last_idx - 1)

            if valid:
                is_bullish = "bullish" in name
                atr = self.get_latest_atr(df, 14)
                if atr <= 0:
                    continue

                curr = df.iloc[-1]
                close_p = float(curr["close"])
                high_p = float(curr["high"])
                low_p = float(curr["low"])

                # Fast Scalp Entry & Targets
                if is_bullish:
                    entry = close_p
                    sl = low_p - 0.2 * atr
                    tp = entry + 1.5 * abs(entry - sl)
                    sig_type = SignalType.BUY
                else:
                    entry = close_p
                    sl = high_p + 0.2 * atr
                    tp = entry - 1.5 * abs(entry - sl)
                    sig_type = SignalType.SELL

                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = reward / risk if risk > 0 else 0

                signals.append(TradeSignal(
                    symbol=symbol,
                    signal_type=sig_type,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    confidence=0.85,
                    pattern=PatternName.BIG_SHADOW_BULL if is_bullish else PatternName.BIG_SHADOW_BEAR,
                    timeframe=timeframe,
                    reason=f"Naked Forex Scalp {name} on {timeframe}",
                    risk_reward=rr,
                ))

        return signals


# ====================================================================
# Multi-Timeframe Confluence
# ====================================================================

_TREND_TO_CHOCH_LABEL = {
    TrendDirection.UP: "bullish",
    TrendDirection.DOWN: "bearish",
    TrendDirection.RANGING: "ranging",
}


class MultiTimeframeAnalyzer:
    def __init__(self):
        self.structure_analyzer = MarketStructureAnalyzer()
        self.sr_detector = SupportResistanceDetector()
        self.strategy = NakedForexStrategy()
        self.timeframes = ["1d", "1h", "15m"]
        self.tf_rank = {"1d": 0, "4h": 1, "1h": 2, "15m": 3, "5m": 4, "30m": 3.5}

    def get_tf_rank(self, tf: str) -> float:
        return self.tf_rank.get(tf.lower(), 99)

    def analyze_timeframe(self, df: pd.DataFrame, symbol: str, timeframe: str, sr_levels=None) -> MarketAnalysis:
        trend = self.structure_analyzer.identify_trend(df)
        bias = self.structure_analyzer.get_market_bias(df)
        atr = calculate_atr_value(df, 14)

        # Volatility regime
        atr_series = calculate_atr(df, 14)
        atr_list = atr_series.dropna().tolist()
        vol_regime = "normal"
        if len(atr_list) >= 20:
            recent_avg = sum(atr_list[-5:]) / 5
            historical_avg = sum(atr_list[-20:]) / 20
            if historical_avg > 0:
                ratio = recent_avg / historical_avg
                if ratio > 1.5:
                    vol_regime = "high"
                elif ratio < 0.7:
                    vol_regime = "low"

        atr_percentile = 50.0
        if len(atr_list) >= 20 and atr > 0:
            atr_percentile = sum(1 for a in atr_list if a < atr) / len(atr_list) * 100

        if sr_levels is None:
            sr_levels = self.sr_detector.detect_levels(df)

        swing_highs, swing_lows = self.structure_analyzer.find_swing_points(df)
        structure_breaks = self.structure_analyzer.detect_bos(df, swing_highs, swing_lows)
        choch_label = _TREND_TO_CHOCH_LABEL.get(trend, "ranging")
        structure_breaks += self.structure_analyzer.detect_choch(df, swing_highs, swing_lows, choch_label)

        signals = self.strategy.analyze(df, symbol, timeframe, sr_levels=sr_levels)

        sma20 = df["close"].tail(20).mean()
        current = df.iloc[-1]["close"]
        momentum = "bullish" if current > sma20 else "bearish"

        return MarketAnalysis(
            timeframe=timeframe, trend=trend, bias=bias, atr=atr,
            atr_percentile=atr_percentile, volatility_regime=vol_regime,
            structure_breaks=structure_breaks, sr_levels=sr_levels,
            momentum=momentum, signals=signals,
        )

    def compute_confluence(self, analyses: Dict[str, MarketAnalysis]) -> dict:
        if not analyses:
            return {"direction": "neutral", "score": 0.0, "higher_tf_bias": MarketBias.NEUTRAL, "trend_alignment": False, "factors": ["No data"], "bullish_ratio": 0.0, "bearish_ratio": 0.0}

        sorted_tfs = sorted(analyses.keys(), key=lambda t: self.get_tf_rank(t))
        bullish_count = 0
        bearish_count = 0
        total = len(sorted_tfs)
        factors = []

        for tf in sorted_tfs:
            analysis = analyses[tf]
            if analysis.bias == MarketBias.BULLISH:
                bullish_count += 1
                factors.append(f"{tf}: bullish bias")
            elif analysis.bias == MarketBias.BEARISH:
                bearish_count += 1
                factors.append(f"{tf}: bearish bias")
            else:
                factors.append(f"{tf}: neutral")

        higher_tf_bias = MarketBias.NEUTRAL
        for tf in sorted_tfs:
            if analyses[tf].bias != MarketBias.NEUTRAL:
                higher_tf_bias = analyses[tf].bias
                break

        if bullish_count > bearish_count and bullish_count >= total * 0.6:
            direction = "bullish"
        elif bearish_count > bullish_count and bearish_count >= total * 0.6:
            direction = "bearish"
        else:
            direction = "neutral"

        score = max(bullish_count, bearish_count) / total if total > 0 else 0
        trend_alignment = (bullish_count == total) or (bearish_count == total)

        return {
            "direction": direction, "score": score, "higher_tf_bias": higher_tf_bias,
            "trend_alignment": trend_alignment, "factors": factors,
            "bullish_ratio": bullish_count / total if total else 0,
            "bearish_ratio": bearish_count / total if total else 0,
        }


# ====================================================================
# AI Decision Engine (9-Check Risk Gate)
# ====================================================================


class AIDecisionEngine:
    """9-check risk gate. Strict NO TRADE default."""

    def __init__(self):
        self.settings = settings

    def evaluate(self, signal: TradeSignal, confluence: dict, session: object) -> dict:
        """Run 9 risk checks. Returns decision dict."""
        checks_passed = []
        checks_failed = []

        # 1. Trend alignment (Naked Forex: >= 50% TF alignment or higher TF direction)
        conf_score = confluence.get("score", 0.0)
        direction = confluence.get("direction", "neutral")
        if confluence.get("trend_alignment") or conf_score >= 0.5 or direction != "neutral":
            checks_passed.append(f"TF Confluence Aligned ({conf_score:.0%})")
        else:
            checks_failed.append("Insufficient TF alignment")

        # 2. Confluence score
        if conf_score >= 0.5:
            checks_passed.append(f"Confluence {conf_score:.0%}")
        else:
            checks_failed.append(f"Low confluence {conf_score:.0%}")

        # 3. Confidence threshold
        if signal.confidence >= self.settings.ai_confidence_threshold:
            checks_passed.append(f"Confidence {signal.confidence:.0%}")
        else:
            checks_failed.append(f"Low confidence {signal.confidence:.0%}")

        # 4. Risk/Reward minimum
        if signal.risk_reward >= self.settings.min_risk_reward:
            checks_passed.append(f"R:R {signal.risk_reward:.1f}")
        else:
            checks_failed.append(f"R:R {signal.risk_reward:.1f} < {self.settings.min_risk_reward}")

        # 5. Daily loss limit
        from engine.models import TradingSession
        if isinstance(session, TradingSession):
            session.reset_daily_risk()
            if session.daily_risk.realized_pnl >= -session.initial_balance * self.settings.max_daily_drawdown_pct:
                checks_passed.append("Within daily loss limit")
            else:
                checks_failed.append("Daily loss limit reached")

        # 6. Max daily trades
        if isinstance(session, TradingSession):
            if session.daily_risk.trades_count < self.settings.max_trades_per_day:
                checks_passed.append(f"Trades {session.daily_risk.trades_count}/{self.settings.max_trades_per_day}")
            else:
                checks_failed.append("Max daily trades reached")

        # 7. Consecutive losses
        if isinstance(session, TradingSession):
            if session.daily_risk.consecutive_losses < self.settings.max_consecutive_losses:
                checks_passed.append(f"Consec losses {session.daily_risk.consecutive_losses}/{self.settings.max_consecutive_losses}")
            else:
                checks_failed.append(f"Max consecutive losses ({session.daily_risk.consecutive_losses})")

        # 8. Max open positions
        if isinstance(session, TradingSession):
            if len(session.positions) < self.settings.max_open_positions:
                checks_passed.append(f"Positions {len(session.positions)}/{self.settings.max_open_positions}")
            else:
                checks_failed.append("Max open positions")

        # 9. Pattern detection
        if signal.pattern != PatternName.NONE:
            checks_passed.append(f"Pattern: {signal.pattern.value}")
        else:
            checks_failed.append("No pattern detected")

        # Decision
        all_passed = len(checks_failed) == 0

        if all_passed:
            direction = signal.signal_type.value
            high_conf = signal.confidence >= self.settings.ai_high_confidence
        else:
            direction = "NO_TRADE"
            high_conf = False

        return {
            "direction": direction,
            "confidence": signal.confidence,
            "market_bias": confluence.get("higher_tf_bias", MarketBias.NEUTRAL),
            "entry_zone": (signal.entry_price, signal.stop_loss, signal.take_profit),
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "risk_reward": signal.risk_reward,
            "confirmation_factors": checks_passed,
            "rejection_reasons": checks_failed,
            "all_checks_passed": all_passed,
            "high_confidence": high_conf,
        }
