"""AI decision layer for the MT5 AI Trader project.

Re-exports the public API so consumers can write:

    from ai_layer import AIDecisionEngine
"""

from ai_layer.decision_engine import AIDecisionEngine

__all__ = ["AIDecisionEngine"]
