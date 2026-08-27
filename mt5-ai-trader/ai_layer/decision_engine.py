"""AI decision layer for the MT5 AI Trader project.

This module does NOT blindly control the trading account.  It receives
structured market information and returns a structured decision:
BUY, SELL, or NO TRADE.

If data is incomplete or conflicting, it returns NO TRADE.

Evaluation checks (in order):

1. Higher-timeframe bias agreement
2. Multi-timeframe confluence score
3. Trend alignment across TFs
4. Volatility regime
5. Spread (hard reject)
6. Risk/Reward (hard reject if below minimum)
7. Base signal confidence
8. BOS / CHOCH confirmation
9. S/R confluence

Each check adjusts confidence up or down.  The final confidence is
clamped to [0, 1] and compared against the configured thresholds.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from config.settings import settings
from models.enums import MarketBias, SignalType
from models.signals import AIDecision, MarketAnalysis, TradeSignal
from utils.logging import logger

__all__ = ["AIDecisionEngine"]


class AIDecisionEngine:
    """AI Decision Layer.

    Receives structured market information and returns a structured
    decision: BUY, SELL, or NO TRADE.

    If data is incomplete or conflicting, it returns NO TRADE.

    Parameters
    ----------
    confidence_threshold:
        Minimum confidence for a trade to be approved.  Defaults
        to ``settings.ai_confidence_threshold`` (0.65).
    high_confidence:
        Confidence level above which even some conflicting factors
        are tolerated.  Defaults to ``settings.ai_high_confidence``
        (0.80).
    """

    def __init__(
        self,
        confidence_threshold: Optional[float] = None,
        high_confidence: Optional[float] = None,
    ) -> None:
        self.confidence_threshold = (
            confidence_threshold if confidence_threshold is not None
            else settings.ai_confidence_threshold
        )
        self.high_confidence = (
            high_confidence if high_confidence is not None
            else settings.ai_high_confidence
        )

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        signal: TradeSignal,
        mtf_analyses: Dict[str, MarketAnalysis],
        confluence: dict,
        spread_points: int = 0,
        volatility_regime: str = "normal",
    ) -> AIDecision:
        """Main evaluation method.

        Parameters
        ----------
        signal:
            The candidate trade signal from the strategy.
        mtf_analyses:
            Market analysis from each timeframe.
        confluence:
            Output from :meth:`MultiTimeframeAnalyzer.compute_confluence`.
        spread_points:
            Current spread in points.
        volatility_regime:
            Current volatility regime (``"high"``, ``"normal"``,
            ``"low"``).

        Returns
        -------
        AIDecision
            Structured decision with direction, confidence, and all
            contributing factors.
        """
        rejection_reasons: List[str] = []
        confirmation_factors: List[str] = []
        confidence = signal.confidence

        # ── CHECK 1: Higher-timeframe bias agreement ──
        higher_tf_bias = confluence.get("higher_tf_bias", MarketBias.NEUTRAL)
        if signal.signal_type == SignalType.BUY and higher_tf_bias == MarketBias.BULLISH:
            confidence += 0.15
            confirmation_factors.append("HTF bullish bias aligns with BUY signal")
        elif signal.signal_type == SignalType.SELL and higher_tf_bias == MarketBias.BEARISH:
            confidence += 0.15
            confirmation_factors.append("HTF bearish bias aligns with SELL signal")
        elif higher_tf_bias == MarketBias.NEUTRAL:
            confirmation_factors.append("HTF bias is neutral")
        else:
            rejection_reasons.append(
                f"HTF bias ({higher_tf_bias.value}) conflicts with "
                f"{signal.signal_type.value} signal"
            )
            confidence -= 0.20

        # ── CHECK 2: Multi-timeframe confluence score ──
        confluence_score = confluence.get("score", 0.0)
        if confluence_score >= 0.8:
            confidence += 0.10
            confirmation_factors.append(
                f"Strong MTF confluence ({confluence_score:.0%})"
            )
        elif confluence_score >= 0.6:
            confidence += 0.05
            confirmation_factors.append(
                f"Moderate MTF confluence ({confluence_score:.0%})"
            )
        else:
            rejection_reasons.append(
                f"Weak MTF confluence ({confluence_score:.0%})"
            )
            confidence -= 0.15

        # ── CHECK 3: Trend alignment across TFs ──
        if confluence.get("trend_alignment", False):
            confidence += 0.10
            confirmation_factors.append("All timeframes agree on direction")

        # ── CHECK 4: Volatility regime ──
        if volatility_regime == "high":
            confidence += 0.03
            confirmation_factors.append(
                "High volatility - potential momentum trade"
            )
        elif volatility_regime == "low":
            rejection_reasons.append(
                "Low volatility - insufficient movement for entry"
            )
            confidence -= 0.10

        # ── CHECK 5: Spread (hard reject) ──
        max_spread = settings.max_spread_points
        if spread_points > max_spread:
            rejection_reasons.append(
                f"Spread ({spread_points} pts) exceeds maximum ({max_spread})"
            )
            return self._no_trade(signal, rejection_reasons, confirmation_factors)

        # ── CHECK 6: Risk/Reward (hard reject if below minimum) ──
        if signal.risk_reward >= 2.0:
            confidence += 0.10
            confirmation_factors.append(
                f"Excellent R:R ({signal.risk_reward:.1f})"
            )
        elif signal.risk_reward >= settings.min_risk_reward:
            confirmation_factors.append(
                f"Adequate R:R ({signal.risk_reward:.1f})"
            )
        else:
            rejection_reasons.append(
                f"R:R ({signal.risk_reward:.1f}) below minimum "
                f"({settings.min_risk_reward})"
            )
            return self._no_trade(signal, rejection_reasons, confirmation_factors)

        # ── CHECK 7: Base signal confidence ──
        if signal.confidence < 0.5:
            rejection_reasons.append(
                f"Base signal confidence too low ({signal.confidence:.2f})"
            )
            return self._no_trade(signal, rejection_reasons, confirmation_factors)

        # ── CHECK 8: BOS/CHOCH confirmation from MTF analyses ──
        for tf_name, analysis in mtf_analyses.items():
            for sb in analysis.structure_breaks:
                if sb.type in ("BOS", "CHOCH"):
                    if (
                        signal.signal_type == SignalType.BUY
                        and sb.direction == "bullish"
                    ) or (
                        signal.signal_type == SignalType.SELL
                        and sb.direction == "bearish"
                    ):
                        confirmation_factors.append(
                            f"{sb.type} {sb.direction} on {tf_name}"
                        )
                        confidence += 0.05

        # ── CHECK 9: S/R confluence ──
        for tf_name, analysis in mtf_analyses.items():
            for sr in analysis.sr_levels:
                entry = signal.entry_price
                # Guard against None zones.
                zone_lo = sr.zone_low if sr.zone_low is not None else sr.price
                zone_hi = sr.zone_high if sr.zone_high is not None else sr.price
                if zone_lo <= entry <= zone_hi:
                    if (
                        signal.signal_type == SignalType.BUY
                        and sr.type == "support"
                    ) or (
                        signal.signal_type == SignalType.SELL
                        and sr.type == "resistance"
                    ):
                        confirmation_factors.append(
                            f"Entry near {sr.type} level on {tf_name}"
                        )
                        confidence += 0.05
                        break  # one S/R hit is enough

        # ── FINAL DECISION ──
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= self.confidence_threshold:
            direction = signal.signal_type  # BUY or SELL
        else:
            rejection_reasons.append(
                f"Final confidence ({confidence:.2f}) below threshold "
                f"({self.confidence_threshold})"
            )
            return self._no_trade(signal, rejection_reasons, confirmation_factors)

        # Even if confidence is above the normal threshold, a
        # conflict with HTF bias is only acceptable at high_confidence.
        critical_rejections = [
            r for r in rejection_reasons if "conflict" in r.lower()
        ]
        if critical_rejections and confidence < self.high_confidence:
            return self._no_trade(signal, rejection_reasons, confirmation_factors)

        logger.info(
            "AI APPROVED %s %s confidence=%.3f factors=%s",
            signal.symbol, direction.value, confidence,
            confirmation_factors,
        )

        return AIDecision(
            direction=direction,
            confidence=round(confidence, 3),
            market_bias=higher_tf_bias,
            entry_zone=(signal.entry_price, signal.entry_price),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_reward=signal.risk_reward,
            confirmation_factors=confirmation_factors,
            rejection_reasons=rejection_reasons,  # include for transparency
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _no_trade(
        self,
        signal: TradeSignal,
        rejection_reasons: List[str],
        confirmation_factors: List[str],
    ) -> AIDecision:
        """Return a NO TRADE decision."""
        logger.debug(
            "AI REJECTED %s reasons=%s confirmations=%s",
            signal.symbol, rejection_reasons, confirmation_factors,
        )
        return AIDecision(
            direction=SignalType.NO_TRADE,
            confidence=0.0,
            market_bias=MarketBias.NEUTRAL,
            entry_zone=(signal.entry_price, signal.entry_price),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_reward=signal.risk_reward,
            confirmation_factors=confirmation_factors,
            rejection_reasons=rejection_reasons,
        )

    def score_signal(
        self,
        signal: TradeSignal,
        mtf_analyses: Optional[Dict[str, MarketAnalysis]] = None,
        confluence: Optional[dict] = None,
        atr_history: Optional[list] = None,
    ) -> float:
        """Backward-compatible scoring method.

        Returns a 0-1 confidence score for a signal based on
        available context.
        """
        if confluence is None:
            confluence = {
                "score": 0.5,
                "direction": "neutral",
                "higher_tf_bias": MarketBias.NEUTRAL,
                "trend_alignment": False,
            }
        if mtf_analyses is None:
            mtf_analyses = {}

        decision = self.evaluate(signal, mtf_analyses, confluence)
        return decision.confidence
