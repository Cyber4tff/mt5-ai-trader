"""Support and resistance level detection for the MT5 AI Trader project.

Provides :class:`SupportResistanceDetector`, a standalone module that
identifies swing highs/lows, clusters them into S/R zones, and exposes
helpers for finding the nearest support/resistance to a given price.

Only ``numpy`` is used for the heavy lifting – no ``scipy`` dependency.
ATR-based tolerance ensures the detector scales correctly across
instruments (forex, gold, crypto, etc.).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from models.market import SRLevel, SwingPoint
from utils.helpers import calculate_atr_value

__all__ = ["SupportResistanceDetector"]


class SupportResistanceDetector:
    """Detect and rank support/resistance levels from OHLCV data.

    Parameters
    ----------
    lookback:
        Number of recent bars to consider when scanning for swing
        points.
    min_touches:
        Minimum number of clustered swing points required for a
        level to be included in the output.
    atr_tolerance_mult:
        Multiplier applied to ATR when clustering nearby swing
        points.  Two swing points within ``ATR * atr_tolerance_mult``
        of each other are considered the *same* level.
    """

    def __init__(
        self,
        lookback: int = 50,
        min_touches: int = 2,
        atr_tolerance_mult: float = 0.3,
    ) -> None:
        self.lookback = lookback
        self.min_touches = min_touches
        self.atr_tolerance_mult = atr_tolerance_mult

    # ------------------------------------------------------------------
    # Swing-point detection
    # ------------------------------------------------------------------

    def find_swing_points(
        self, df: pd.DataFrame, order: int = 3
    ) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Identify swing highs and swing lows using a window approach.

        A swing **high** at index *i* is the maximum ``high`` value in
        the window ``[i - order, i + order]`` (inclusive).  Similarly for
        swing **lows** with ``low``.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        order:
            Half-window size.  ``order=3`` checks 3 bars on each side
            (7-bar window).

        Returns
        -------
        tuple[list[SwingPoint], list[SwingPoint]]
            ``(swing_highs, swing_lows)``
        """
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        n = len(df)
        window = 2 * order + 1

        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []

        for i in range(order, n - order):
            # --- Swing High ---
            h_slice = highs[i - order : i + order + 1]
            if highs[i] == np.max(h_slice) and np.sum(highs[i] == h_slice) == 1:
                # Strength: count how many points in the window are
                # strictly lower than this peak (1–window).
                strength = min(3, max(1, int(np.sum(highs[i] > h_slice) / 2)))
                swing_highs.append(
                    SwingPoint(
                        price=float(highs[i]),
                        type="high",
                        index=int(i),
                        strength=strength,
                    )
                )

            # --- Swing Low ---
            l_slice = lows[i - order : i + order + 1]
            if lows[i] == np.min(l_slice) and np.sum(lows[i] == l_slice) == 1:
                strength = min(3, max(1, int(np.sum(lows[i] < l_slice) / 2)))
                swing_lows.append(
                    SwingPoint(
                        price=float(lows[i]),
                        type="low",
                        index=int(i),
                        strength=strength,
                    )
                )

        # Apply lookback filter — only keep points within the last
        # ``self.lookback`` bars of the dataframe.
        cutoff = max(0, n - self.lookback)
        swing_highs = [p for p in swing_highs if p.index >= cutoff]
        swing_lows = [p for p in swing_lows if p.index >= cutoff]

        return swing_highs, swing_lows

    # ------------------------------------------------------------------
    # Level detection & clustering
    # ------------------------------------------------------------------

    def detect_levels(self, df: pd.DataFrame, n_levels: int = 5) -> List[SRLevel]:
        """Detect the strongest S/R levels by clustering swing points.

        Algorithm
        ---------
        1. Find swing points via :meth:`find_swing_points`.
        2. Cluster nearby points (within ``ATR * atr_tolerance_mult``)
           using a greedy single-linkage approach.
        3. For each cluster, compute an :class:`SRLevel` whose price
           is the cluster's average price.
        4. Rank clusters by touch count (descending) and return the
           top ``n_levels``.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        n_levels:
            Maximum number of levels to return.

        Returns
        -------
        list[SRLevel]
            Detected levels sorted by strength (most touches first).
        """
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

        # ---- Greedy clustering ----
        clusters: List[List[SwingPoint]] = []
        assigned: List[bool] = [False] * len(all_points)

        for i, pt in enumerate(all_points):
            if assigned[i]:
                continue
            cluster = [pt]
            assigned[i] = True
            for j in range(i + 1, len(all_points)):
                if assigned[j]:
                    continue
                # Check if this point is close to *any* member of the
                # cluster (single-linkage).
                if any(
                    abs(all_points[j].price - cp.price) <= tolerance
                    for cp in cluster
                ):
                    cluster.append(all_points[j])
                    assigned[j] = True
            clusters.append(cluster)

        # ---- Build SRLevel for each cluster ----
        levels: List[SRLevel] = []
        for cluster in clusters:
            if len(cluster) < self.min_touches:
                continue

            prices = np.array([p.price for p in cluster])
            avg_price = float(np.mean(prices))
            zone_high = float(np.max(prices))
            zone_low = float(np.min(prices))
            touch_count = len(cluster)

            # Classify as support or resistance based on the majority
            # type of swing points in the cluster.
            high_count = sum(1 for p in cluster if p.type == "high")
            low_count = sum(1 for p in cluster if p.type == "low")
            level_type: str = "resistance" if high_count >= low_count else "support"

            # Strength = touch count, capped at 5.
            strength = min(5, touch_count)

            # Gather time indices of touches.
            touch_indices = [p.index for p in cluster]

            levels.append(
                SRLevel(
                    price=avg_price,
                    type=level_type,
                    strength=strength,
                    touches=touch_count,
                    touch_times=touch_indices,
                    last_touch_time=float(max(touch_indices)),
                    zone_high=zone_high,
                    zone_low=zone_low,
                )
            )

        # Sort by strength descending, then by touch count descending.
        levels.sort(key=lambda lv: (lv.strength, lv.touches), reverse=True)

        return levels[:n_levels]

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def find_nearest_support(
        self, price: float, levels: List[SRLevel]
    ) -> Optional[SRLevel]:
        """Return the closest support level below *price*.

        Parameters
        ----------
        price:
            The current (or reference) price.
        levels:
            List of detected S/R levels.

        Returns
        -------
        SRLevel or None
            The nearest support, or ``None`` if no support exists
            below the given price.
        """
        supports = [lv for lv in levels if lv.type == "support" and lv.price < price]
        if not supports:
            return None
        return min(supports, key=lambda lv: price - lv.price)

    def find_nearest_resistance(
        self, price: float, levels: List[SRLevel]
    ) -> Optional[SRLevel]:
        """Return the closest resistance level above *price*.

        Parameters
        ----------
        price:
            The current (or reference) price.
        levels:
            List of detected S/R levels.

        Returns
        -------
        SRLevel or None
            The nearest resistance, or ``None`` if no resistance
            exists above the given price.
        """
        resistances = [
            lv for lv in levels if lv.type == "resistance" and lv.price > price
        ]
        if not resistances:
            return None
        return min(resistances, key=lambda lv: lv.price - price)

    def is_near_level(
        self, price: float, level: SRLevel, atr: float
    ) -> bool:
        """Check whether *price* is within the level's zone or ATR tolerance.

        A price is considered *near* a level if:

        * It falls between ``level.zone_low`` and ``level.zone_high``, **or**
        * Its distance from ``level.price`` is less than
          ``atr * self.atr_tolerance_mult``.

        Parameters
        ----------
        price:
            The price to test.
        level:
            The S/R level to test against.
        atr:
            Current ATR value.

        Returns
        -------
        bool
            ``True`` if *price* is near the level.
        """
        # Within the defined zone.
        if level.zone_low is not None and level.zone_high is not None:
            if level.zone_low <= price <= level.zone_high:
                return True

        # Within ATR-based tolerance.
        tolerance = atr * self.atr_tolerance_mult
        if abs(price - level.price) <= tolerance:
            return True

        return False
