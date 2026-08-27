"""Risk management module for the MT5 AI Trader project.

Provides position sizing based on actual broker contract specifications
and a comprehensive risk manager that enforces daily drawdown limits,
consecutive-loss limits, position caps, spread limits, and more.
"""

from risk.position_sizer import PositionSizer
from risk.manager import RiskManager

__all__ = ["RiskManager", "PositionSizer"]
