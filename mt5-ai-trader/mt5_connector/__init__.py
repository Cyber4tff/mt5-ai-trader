"""MT5 connector package.

Re-exports the three main public classes so that consumers can write::

    from mt5_connector import MT5Connector, AccountInfo, TradeResult
"""

from mt5_connector.connector import AccountInfo, MT5Connector, SymbolSpec, TradeResult

__all__ = [
    "MT5Connector",
    "AccountInfo",
    "TradeResult",
    "SymbolSpec",
]
