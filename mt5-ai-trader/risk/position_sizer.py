"""Position sizing using actual broker contract specifications.

This module fixes the common bug where position sizing uses hardcoded
point_value=1.0 and standard_lot=100000 for all instruments.

The correct formula uses broker-supplied ``tick_value`` and ``tick_size``:

    risk_amount = balance * risk_percent
    sl_distance = abs(entry - sl)   (in price units)
    sl_distance_ticks = sl_distance / tick_size
    tick_loss = sl_distance_ticks * tick_value
    lots = risk_amount / tick_loss

Where ``tick_value``, ``tick_size``, and ``volume_min/max/step`` come from
the broker's ``symbol_info`` at runtime.
"""

from __future__ import annotations

from typing import Optional

from models.market import SymbolSpec
from utils.helpers import normalize_volume
from utils.logging import logger


class PositionSizer:
    """Calculate position size using actual broker contract specifications.

    Every value used in the calculation (tick_value, tick_size,
    volume_min, volume_max, volume_step) is read from the live
    ``SymbolSpec`` produced by the MT5 connector.  No values are
    hardcoded, so the sizer works correctly for forex pairs, metals,
    crypto, indices, or any other instrument.
    """

    def calculate(
        self,
        balance: float,
        risk_percent: float,
        entry: float,
        sl: float,
        symbol_spec: SymbolSpec,
    ) -> float:
        """Calculate position size in lots.

        Parameters
        ----------
        balance :
            Account balance in account currency.
        risk_percent :
            Fraction of balance to risk (e.g. ``0.02`` for 2 %).
        entry :
            Planned entry price.
        sl :
            Stop-loss price.
        symbol_spec :
            Live symbol specification from MT5.  **Must** have
            ``tick_value``, ``tick_size``, ``volume_min``,
            ``volume_max``, and ``volume_step`` populated.

        Returns
        -------
        float
            Position size in lots, normalised to the broker's
            ``volume_step`` and clamped to ``[volume_min, volume_max]``.
            Returns ``volume_min`` as a safe fallback on any error.
        """
        # --- Input validation ---
        if balance <= 0 or risk_percent <= 0:
            logger.warning(
                "Invalid balance ({}) or risk_percent ({}) for position sizing",
                balance,
                risk_percent,
            )
            return symbol_spec.volume_min

        if entry == sl:
            logger.warning("Entry equals SL – no stop distance")
            return symbol_spec.volume_min

        if symbol_spec is None:
            logger.error("No symbol spec provided – cannot calculate position size")
            return 0.01

        if symbol_spec.tick_value is None or symbol_spec.tick_value == 0:
            logger.error(
                "tick_value is {} – cannot calculate position size",
                symbol_spec.tick_value,
            )
            return symbol_spec.volume_min

        if symbol_spec.tick_size is None or symbol_spec.tick_size == 0:
            logger.error(
                "tick_size is {} – cannot calculate position size",
                symbol_spec.tick_size,
            )
            return symbol_spec.volume_min

        # --- Core calculation ---
        risk_amount = balance * risk_percent
        sl_distance = abs(entry - sl)
        sl_ticks = sl_distance / symbol_spec.tick_size
        loss_per_lot = sl_ticks * symbol_spec.tick_value

        if loss_per_lot <= 0:
            logger.error("loss_per_lot is {} – calculation error", loss_per_lot)
            return symbol_spec.volume_min

        lots = risk_amount / loss_per_lot

        # --- Normalise to broker requirements ---
        lots = normalize_volume(
            lots,
            symbol_spec.volume_step,
            symbol_spec.volume_min,
            symbol_spec.volume_max,
        )

        logger.info(
            "Position size calculated: {} lots | "
            "Risk: ${:.2f} ({:.1f}%) | "
            "SL distance: {:.5f} ({:.0f} ticks) | "
            "Tick value: ${:.4f} | "
            "Symbol: {}",
            lots,
            risk_amount,
            risk_percent * 100,
            sl_distance,
            sl_ticks,
            symbol_spec.tick_value,
            symbol_spec.name,
        )

        return lots

    def calculate_risk_amount(self, balance: float, risk_percent: float) -> float:
        """Return the dollar amount to risk for a single trade.

        Parameters
        ----------
        balance :
            Current account balance.
        risk_percent :
            Fraction of balance to risk (e.g. ``0.02``).

        Returns
        -------
        float
            Risk amount in account currency.
        """
        return balance * risk_percent
