"""Market structure analysis for the MT5 AI Trader project.

Implements Break of Structure (BOS), Change of Character (CHOCH),
liquidity sweeps, and swing-based trend/bias detection using the
Smart Money Concepts (SMC) framework.

All analysis operates on :class:`~models.market.SwingPoint` and
:class:`~models.market.StructureBreak` dataclasses.  Only ``numpy``
is required — no ``scipy`` dependency.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from models.enums import MarketBias, TrendDirection
from models.market import StructureBreak, SwingPoint
from utils.helpers import calculate_atr_value

__all__ = ["MarketStructureAnalyzer"]


class MarketStructureAnalyzer:
    """Analyse market structure to detect BOS, CHOCH, and trend bias.

    Parameters
    ----------
    swing_order:
        Half-window size used when identifying swing points.
        ``order=3`` means a 7-bar window (3 bars on each side of
        the candidate).
    """

    def __init__(self, swing_order: int = 3) -> None:
        self.swing_order = swing_order

    # ------------------------------------------------------------------
    # Swing-point detection
    # ------------------------------------------------------------------

    def find_swing_points(
        self, df: pd.DataFrame
    ) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Find swing highs and lows using a windowed peak/valley approach.

        Parameters
        ----------
        df:
            OHLCV DataFrame.

        Returns
        -------
        tuple[list[SwingPoint], list[SwingPoint]]
            ``(swing_highs, swing_lows)`` sorted by index ascending.
        """
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        n = len(df)
        order = self.swing_order

        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []

        for i in range(order, n - order):
            # --- Swing High ---
            h_slice = highs[i - order : i + order + 1]
            if highs[i] == np.max(h_slice) and np.sum(highs[i] == h_slice) == 1:
                swing_highs.append(
                    SwingPoint(
                        price=float(highs[i]),
                        type="high",
                        index=int(i),
                        strength=1,
                    )
                )

            # --- Swing Low ---
            l_slice = lows[i - order : i + order + 1]
            if lows[i] == np.min(l_slice) and np.sum(lows[i] == l_slice) == 1:
                swing_lows.append(
                    SwingPoint(
                        price=float(lows[i]),
                        type="low",
                        index=int(i),
                        strength=1,
                    )
                )

        return swing_highs, swing_lows

    # ------------------------------------------------------------------
    # Full structure analysis
    # ------------------------------------------------------------------

    def identify_structure(self, df: pd.DataFrame) -> Dict:
        """Produce a complete market-structure snapshot.

        The returned dictionary contains:

        * ``trend`` – ``"bullish"``, ``"bearish"``, or ``"ranging"``
        * ``swing_highs`` – list of :class:`SwingPoint`
        * ``swing_lows`` – list of :class:`SwingPoint`
        * ``last_bos`` – most recent :class:`StructureBreak` or ``None``
        * ``last_choch`` – most recent :class:`StructureBreak` or ``None``
        * ``structure_label`` – human-readable label

        Parameters
        ----------
        df:
            OHLCV DataFrame.

        Returns
        -------
        dict
        """
        swing_highs, swing_lows = self.find_swing_points(df)

        # Determine trend from swing-point pattern.
        trend = self._classify_swing_pattern(swing_highs, swing_lows)

        # Detect BOS and CHOCH events.
        bos_list = self.detect_bos(df, swing_highs, swing_lows)
        choch_list = self.detect_choch(df, swing_highs, swing_lows, trend)

        last_bos = bos_list[-1] if bos_list else None
        last_choch = choch_list[-1] if choch_list else None

        # Build a descriptive label.
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

    # ------------------------------------------------------------------
    # BOS detection
    # ------------------------------------------------------------------

    def detect_bos(
        self,
        df: pd.DataFrame,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
    ) -> List[StructureBreak]:
        """Detect Breaks of Structure (BOS).

        In a **bullish** trend a BOS occurs when price closes above the
        most recent swing high.  In a **bearish** trend a BOS occurs
        when price closes below the most recent swing low.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        swing_highs:
            Detected swing high points.
        swing_lows:
            Detected swing low points.

        Returns
        -------
        list[StructureBreak]
            All detected BOS events, chronologically ordered.
        """
        if not swing_highs or not swing_lows:
            return []

        closes = df["close"].astype(float).values
        n = len(df)
        results: List[StructureBreak] = []

        # Determine initial trend direction from first two swing points.
        current_trend = self._classify_swing_pattern(swing_highs, swing_lows)

        # We'll walk through the swing points and check whether price
        # broke past the most recent opposing swing point.
        hi_idx = 0
        lo_idx = 0

        # Collect all swing points sorted by index for sequential scan.
        all_swings = sorted(
            [("high", s, i) for i, s in enumerate(swing_highs)]
            + [("low", s, i) for i, s in enumerate(swing_lows)],
            key=lambda x: x[1].index,
        )

        last_sh: Optional[SwingPoint] = None
        last_sl: Optional[SwingPoint] = None

        for sw_type, sw_point, _ in all_swings:
            if sw_type == "high":
                last_sh = sw_point
            else:
                last_sl = sw_point

            # Check if candles *after* this swing point broke the
            # relevant level.
            start_bar = sw_point.index + 1
            if start_bar >= n:
                continue

            if current_trend == "bullish" and last_sh is not None:
                for bar_i in range(start_bar, n):
                    if closes[bar_i] > last_sh.price:
                        results.append(
                            StructureBreak(
                                type="BOS",
                                direction="bullish",
                                price=float(closes[bar_i]),
                                time=float(bar_i),
                                index=bar_i,
                                from_level=last_sh.price,
                            )
                        )
                        break  # one BOS per swing level

            elif current_trend == "bearish" and last_sl is not None:
                for bar_i in range(start_bar, n):
                    if closes[bar_i] < last_sl.price:
                        results.append(
                            StructureBreak(
                                type="BOS",
                                direction="bearish",
                                price=float(closes[bar_i]),
                                time=float(bar_i),
                                index=bar_i,
                                from_level=last_sl.price,
                            )
                        )
                        break

        return results

    # ------------------------------------------------------------------
    # CHOCH detection
    # ------------------------------------------------------------------

    def detect_choch(
        self,
        df: pd.DataFrame,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        current_trend: str,
    ) -> List[StructureBreak]:
        """Detect Changes of Character (CHOCH).

        A CHOCH signals a potential *reversal*:

        * **Bullish trend → CHOCH bearish:** price breaks below the
          most recent swing low.
        * **Bearish trend → CHOCH bullish:** price breaks above the
          most recent swing high.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        swing_highs:
            Detected swing high points.
        swing_lows:
            Detected swing low points.
        current_trend:
            Current structure trend (``"bullish"``, ``"bearish"``,
            or ``"ranging"``).

        Returns
        -------
        list[StructureBreak]
            All detected CHOCH events.
        """
        if current_trend == "ranging":
            return []
        if not swing_highs or not swing_lows:
            return []

        closes = df["close"].astype(float).values
        n = len(df)
        results: List[StructureBreak] = []

        if current_trend == "bullish":
            # Look for a break below the most recent swing low.
            last_sl = swing_lows[-1]
            for bar_i in range(last_sl.index + 1, n):
                if closes[bar_i] < last_sl.price:
                    results.append(
                        StructureBreak(
                            type="CHOCH",
                            direction="bearish",
                            price=float(closes[bar_i]),
                            time=float(bar_i),
                            index=bar_i,
                            from_level=last_sl.price,
                        )
                    )
                    break

        elif current_trend == "bearish":
            # Look for a break above the most recent swing high.
            last_sh = swing_highs[-1]
            for bar_i in range(last_sh.index + 1, n):
                if closes[bar_i] > last_sh.price:
                    results.append(
                        StructureBreak(
                            type="CHOCH",
                            direction="bullish",
                            price=float(closes[bar_i]),
                            time=float(bar_i),
                            index=bar_i,
                            from_level=last_sh.price,
                        )
                    )
                    break

        return results

    # ------------------------------------------------------------------
    # Liquidity sweep detection
    # ------------------------------------------------------------------

    def detect_liquidity_sweep(
        self,
        df: pd.DataFrame,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        atr: float,
    ) -> List[Dict]:
        """Detect liquidity sweeps of swing points.

        A **bearish sweep** occurs when recent candle(s) take out a
        swing high (``high > swing_high``) but then **close below**
        that level — indicating buying liquidity was absorbed and
        sellers regained control.

        A **bullish sweep** is the mirror: price dips below a swing
        low but closes above it.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        swing_highs:
            Swing high points to check.
        swing_lows:
            Swing low points to check.
        atr:
            Current ATR value, used to limit how far back we scan
            for swing points and to define a "recent" window.

        Returns
        -------
        list[dict]
            Each dict contains: ``type``, ``swept_level``,
            ``sweep_price``, ``current_close``.
        """
        if atr <= 0:
            return []

        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        closes = df["close"].astype(float).values
        n = len(df)
        last_close = float(closes[-1])

        # Only consider the most recent few bars (2× ATR window).
        recent_bars = max(3, int(atr))  # heuristic
        start_bar = max(0, n - recent_bars)

        results: List[Dict] = []

        # --- Bearish sweeps (take out swing high, close below) ---
        for sh in swing_highs:
            if sh.index < start_bar:
                continue
            recent_high = float(np.max(highs[start_bar:n]))
            if recent_high > sh.price and last_close < sh.price:
                results.append({
                    "type": "bearish_sweep",
                    "swept_level": sh.price,
                    "sweep_price": recent_high,
                    "current_close": last_close,
                })

        # --- Bullish sweeps (take out swing low, close above) ---
        for sl in swing_lows:
            if sl.index < start_bar:
                continue
            recent_low = float(np.min(lows[start_bar:n]))
            if recent_low < sl.price and last_close > sl.price:
                results.append({
                    "type": "bullish_sweep",
                    "swept_level": sl.price,
                    "sweep_price": recent_low,
                    "current_close": last_close,
                })

        return results

    # ------------------------------------------------------------------
    # Trend identification (swing-based)
    # ------------------------------------------------------------------

    def identify_trend(
        self, df: pd.DataFrame, lookback: int = 20
    ) -> TrendDirection:
        """Determine the trend using swing-point pattern analysis.

        Looks at the swing points within the last *lookback* bars:

        * **Higher Highs + Higher Lows** → ``UP``
        * **Lower Highs + Lower Lows** → ``DOWN``
        * Mixed or insufficient swings → ``RANGING``

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        lookback:
            Number of recent bars to consider.

        Returns
        -------
        TrendDirection
        """
        n = len(df)
        cutoff = max(0, n - lookback)

        swing_highs, swing_lows = self.find_swing_points(df)

        # Filter to the lookback window.
        recent_highs = [s for s in swing_highs if s.index >= cutoff]
        recent_lows = [s for s in swing_lows if s.index >= cutoff]

        if len(recent_highs) < 2 and len(recent_lows) < 2:
            return TrendDirection.RANGING

        # Count HH / HL / LH / LL among the last few swings.
        hh_count = 0
        hl_count = 0
        lh_count = 0
        ll_count = 0

        for i in range(1, len(recent_highs)):
            if recent_highs[i].price > recent_highs[i - 1].price:
                hh_count += 1
            else:
                lh_count += 1

        for i in range(1, len(recent_lows)):
            if recent_lows[i].price > recent_lows[i - 1].price:
                hl_count += 1
            else:
                ll_count += 1

        bullish_score = hh_count + hl_count
        bearish_score = lh_count + ll_count

        if bullish_score > bearish_score and bullish_score >= 1:
            return TrendDirection.UP
        if bearish_score > bullish_score and bearish_score >= 1:
            return TrendDirection.DOWN
        return TrendDirection.RANGING

    # ------------------------------------------------------------------
    # Market bias
    # ------------------------------------------------------------------

    def get_market_bias(self, df: pd.DataFrame) -> MarketBias:
        """Combine structure analysis with recent CHOCH for bias.

        The bias is:

        * ``BULLISH`` if the structure is bullish (HH+HL) and there
          is no recent bearish CHOCH.
        * ``BEARISH`` if the structure is bearish (LH+LL) and there
          is no recent bullish CHOCH.
        * ``NEUTRAL`` otherwise (ranging or CHOCH indicates potential
          reversal).

        Parameters
        ----------
        df:
            OHLCV DataFrame.

        Returns
        -------
        MarketBias
        """
        structure = self.identify_structure(df)
        trend = structure["trend"]
        last_choch = structure["last_choch"]

        if trend == "bullish":
            # A recent bearish CHOCH overrides bullish structure.
            if last_choch is not None and last_choch.direction == "bearish":
                return MarketBias.NEUTRAL
            return MarketBias.BULLISH

        if trend == "bearish":
            # A recent bullish CHOCH overrides bearish structure.
            if last_choch is not None and last_choch.direction == "bullish":
                return MarketBias.NEUTRAL
            return MarketBias.BEARISH

        return MarketBias.NEUTRAL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_swing_pattern(
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
    ) -> str:
        """Classify swing pattern as bullish, bearish, or ranging.

        Uses the last few swing points to count Higher Highs (HH),
        Higher Lows (HL), Lower Highs (LH), and Lower Lows (LL).
        """
        # Need at least 2 of each to form a pattern.
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "ranging"

        # Look at the most recent 3 swing points (enough for a pattern).
        recent_h = swing_highs[-min(3, len(swing_highs)) :]
        recent_l = swing_lows[-min(3, len(swing_lows)) :]

        hh = sum(
            1 for i in range(1, len(recent_h))
            if recent_h[i].price > recent_h[i - 1].price
        )
        hl = sum(
            1 for i in range(1, len(recent_l))
            if recent_l[i].price > recent_l[i - 1].price
        )
        lh = sum(
            1 for i in range(1, len(recent_h))
            if recent_h[i].price < recent_h[i - 1].price
        )
        ll = sum(
            1 for i in range(1, len(recent_l))
            if recent_l[i].price < recent_l[i - 1].price
        )

        bullish = hh + hl
        bearish = lh + ll

        if bullish > bearish:
            return "bullish"
        if bearish > bullish:
            return "bearish"
        return "ranging"
