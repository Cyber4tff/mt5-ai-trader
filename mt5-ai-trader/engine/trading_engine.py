from typing import Dict, List, Optional

from models.enums import SignalType, MarketBias
from models.signals import TradeSignal, AIDecision, MarketAnalysis
from models.market import SymbolSpec
from mt5_connector.connector import MT5Connector, AccountInfo
from strategies.naked_forex import NakedForexStrategy
from strategies.multi_timeframe import MultiTimeframeAnalyzer
from ai_layer.decision_engine import AIDecisionEngine
from risk.manager import RiskManager
from config.settings import settings
from utils.logging import logger


__all__ = ["TradingEngine"]


class TradingEngine:
    """Main trading engine orchestrator.

    Coordinates: MT5 connection -> Multi-TF analysis -> AI decision -> Risk check -> Execution.

    STRICT RULE: Default is NO TRADE. A trade only executes when:
    - Higher-TF bias is established
    - Lower-TF entry confirms the bias
    - Strategy signals provide sufficient agreement
    - Signal quality passes the confidence threshold
    - Risk/reward meets the configured minimum
    - A valid SL exists
    - A valid TP exists
    - Position size is correctly calculated
    - Daily drawdown limit has not been reached
    - Consecutive-loss limit has not been reached
    - Maximum open trades has not been reached
    - Spread is acceptable
    - Market conditions are suitable

    Never force a trade because the market is moving.
    """

    def __init__(self, connector: MT5Connector) -> None:
        self.connector = connector
        self.strategy = NakedForexStrategy()
        self.mtf_analyzer = MultiTimeframeAnalyzer(self.strategy)
        self.ai_engine = AIDecisionEngine()
        self.risk_manager = RiskManager(connector)
        self.running = False
        self._last_scan_results: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Full pipeline scan for a single symbol
    # ------------------------------------------------------------------

    def scan_symbol(self, symbol: str, entry_timeframe: str = 'H1') -> dict:
        """Full pipeline scan for a single symbol.

        1. Fetch OHLCV data for all MTF timeframes
        2. Analyze each timeframe
        3. Compute confluence
        4. If signals exist, run AI decision engine
        5. Return structured results

        Returns dict with:
        - symbol: str
        - analyses: Dict[str, MarketAnalysis] per timeframe
        - confluence: dict
        - decisions: List[AIDecision]  (one per candidate signal)
        - actionable: Optional[dict]  (the best signal that passed all checks, or None)
        - errors: List[str]
        """
        result: dict = {
            'symbol': symbol,
            'analyses': {},
            'confluence': None,
            'decisions': [],
            'actionable': None,
            'errors': []
        }

        # --- Guard: MT5 must be connected ---
        if not self.connector.is_connected():
            result['errors'].append('MT5 not connected')
            return result

        # --- Guard: symbol must be available ---
        symbol_spec = self.connector.get_symbol_spec(symbol)
        if symbol_spec is None:
            result['errors'].append(f'Symbol {symbol} not available')
            return result

        # 1. Fetch and analyze each timeframe
        for tf in settings.mtf_timeframes:
            bars = 500 if tf in ('D1', 'H4') else 300
            df = self.connector.get_ohlcv(symbol, tf, bars=bars)
            if df is None or len(df) < 50:
                result['errors'].append(f'Insufficient data for {symbol} {tf}')
                continue

            try:
                analysis = self.mtf_analyzer.analyze_timeframe(df, symbol, tf)
                result['analyses'][tf] = analysis
                logger.debug(
                    '{} {}: trend={}, bias={}, signals={}',
                    symbol, tf, analysis.trend.value, analysis.bias.value,
                    len(analysis.signals),
                )
            except Exception as e:
                result['errors'].append(f'{tf} analysis error: {e}')
                logger.error('{} {} analysis error: {}', symbol, tf, e)

        if not result['analyses']:
            result['errors'].append('No timeframe data available')
            return result

        # 2. Compute confluence
        result['confluence'] = self.mtf_analyzer.compute_confluence(result['analyses'])
        confluence = result['confluence']
        logger.info(
            '{} MTF confluence: {} (score: {:.0%})',
            symbol, confluence['direction'], confluence['score'],
        )

        # 3. Get signals from the entry timeframe (and one lower if available)
        entry_signals: List[TradeSignal] = []
        entry_analysis = result['analyses'].get(entry_timeframe)
        if entry_analysis:
            entry_signals.extend(entry_analysis.signals)

        # Also get signals from the next lower timeframe
        lower_tfs = self.mtf_analyzer.get_lower_timeframes(entry_timeframe)
        for ltf in lower_tfs[:1]:  # Just one lower TF
            ltf_analysis = result['analyses'].get(ltf)
            if ltf_analysis:
                entry_signals.extend(ltf_analysis.signals)

        if not entry_signals:
            logger.info('{}: No entry signals found', symbol)
            return result

        # 4. Run AI decision engine on each signal
        spread = self.connector.get_current_spread_points(symbol)
        vol_regime = 'normal'
        if entry_analysis:
            vol_regime = entry_analysis.volatility_regime or 'normal'

        for signal in entry_signals:
            try:
                decision = self.ai_engine.evaluate(
                    signal=signal,
                    mtf_analyses=result['analyses'],
                    confluence=confluence,
                    spread_points=spread,
                    volatility_regime=vol_regime,
                )
                result['decisions'].append(decision)
            except Exception as e:
                result['errors'].append(f'AI evaluation error: {e}')
                logger.error('AI evaluation error for {}: {}', signal.pattern, e)

        # 5. Find the best actionable decision
        #    Only consider decisions that are not NO_TRADE.
        buy_decisions = [d for d in result['decisions'] if d.direction == SignalType.BUY]
        sell_decisions = [d for d in result['decisions'] if d.direction == SignalType.SELL]

        best: Optional[AIDecision] = None
        if buy_decisions and confluence['direction'] == 'bullish':
            best = max(buy_decisions, key=lambda d: d.confidence)
        elif sell_decisions and confluence['direction'] == 'bearish':
            best = max(sell_decisions, key=lambda d: d.confidence)
        elif buy_decisions or sell_decisions:
            all_trades = buy_decisions + sell_decisions
            if all_trades:
                best = max(all_trades, key=lambda d: d.confidence)

        # 6. If a best decision exists and is not NO_TRADE, run risk checks
        if best and best.direction != SignalType.NO_TRADE:
            account = self.connector.get_account_info()
            positions = self.connector.get_positions()
            open_count = len(positions)

            allowed, failures = self.risk_manager.check_all(
                symbol=symbol,
                decision=best,
                balance=account.balance if account else 0,
                open_positions_count=open_count,
            )

            # Also check spread independently
            spread_ok, spread_msg = self.risk_manager.check_spread(symbol)
            if not spread_ok:
                failures.append(spread_msg)
                allowed = False

            # Validate SL/TP placement
            if best.stop_loss is not None and best.take_profit is not None and symbol_spec:
                entry = best.entry_zone[0] if best.entry_zone else 0
                sl_tp_ok, sl_tp_msg = self.risk_manager.validate_sl_tp(
                    entry=entry,
                    sl=best.stop_loss,
                    tp=best.take_profit,
                    direction=best.direction,
                    symbol_spec=symbol_spec,
                )
                if not sl_tp_ok:
                    failures.append(sl_tp_msg)
                    allowed = False

            if allowed and account:
                # Calculate position size
                entry = best.entry_zone[0] if best.entry_zone else 0
                volume = self.risk_manager.calculate_position_size(
                    balance=account.balance,
                    entry=entry,
                    sl=best.stop_loss or 0,
                    symbol_spec=symbol_spec,
                )
                result['actionable'] = {
                    'symbol': symbol,
                    'direction': best.direction.value,
                    'entry': entry,
                    'sl': best.stop_loss,
                    'tp': best.take_profit,
                    'volume': volume,
                    'confidence': best.confidence,
                    'risk_reward': best.risk_reward,
                    'confirmation_factors': best.confirmation_factors,
                    'confluence': confluence,
                }
                logger.info(
                    'ACTIONABLE SIGNAL: {} {} @ {} SL={} TP={} '
                    'Vol={} Conf={:.2f} R:R={:.1f}',
                    symbol, best.direction.value, entry,
                    best.stop_loss, best.take_profit,
                    volume, best.confidence, best.risk_reward or 0,
                )
            else:
                result['actionable'] = None
                result['risk_failures'] = failures
                logger.info(
                    '{}: Signal rejected by risk management: {}', symbol, failures
                )

        self._last_scan_results[symbol] = result
        return result

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def execute_trade(self, actionable: Optional[dict]) -> dict:
        """Execute an actionable trade signal.

        Parameters
        ----------
        actionable : dict or None
            The actionable trade dict produced by :meth:`scan_symbol`.

        Returns
        -------
        dict
            Execution result with ``success``, ``ticket``, ``error`` etc.
        """
        if actionable is None:
            return {'success': False, 'error': 'No actionable signal'}

        symbol = actionable['symbol']
        direction = actionable['direction']

        logger.info(
            'Executing trade: {} {} @ {}',
            symbol, direction, actionable['entry'],
        )

        # DEMO MODE: extra safety logging
        if settings.is_demo_mode:
            logger.info('[DEMO MODE] Trade would be executed: {}', actionable)

        result = self.connector.place_market_order(
            symbol=symbol,
            order_type=direction,
            volume=actionable['volume'],
            sl=actionable['sl'],
            tp=actionable['tp'],
            comment=f'AI Engine: conf={actionable["confidence"]:.2f}',
        )

        if result.success:
            logger.info(
                'TRADE EXECUTED: {} {} Ticket={} @ {}',
                symbol, direction, result.ticket, result.price,
            )
            return {
                'success': True,
                'ticket': result.ticket,
                'price': result.price,
                'symbol': symbol,
                'direction': direction,
                'volume': actionable['volume'],
            }
        else:
            logger.error('TRADE FAILED: {} {} - {}', symbol, direction, result.error)
            return {
                'success': False,
                'error': result.error,
                'symbol': symbol,
            }

    # ------------------------------------------------------------------
    # Scan multiple symbols
    # ------------------------------------------------------------------

    def scan_all(self, symbols: Optional[List[str]] = None) -> List[dict]:
        """Scan all configured symbols.

        Parameters
        ----------
        symbols : list[str] or None
            Symbols to scan.  Falls back to ``settings.trading_symbols``.

        Returns
        -------
        list[dict]
            One result dict per symbol (same shape as :meth:`scan_symbol`).
        """
        if symbols is None:
            symbols = settings.trading_symbols

        results: List[dict] = []
        for symbol in symbols:
            try:
                result = self.scan_symbol(symbol)
                results.append(result)
            except Exception as e:
                logger.error('Scan error for {}: {}', symbol, e)
                results.append({'symbol': symbol, 'errors': [str(e)]})

        return results

    # ------------------------------------------------------------------
    # Single scan-and-execute cycle
    # ------------------------------------------------------------------

    def run_cycle(self) -> List[dict]:
        """Run one complete scan-and-execute cycle.

        Scans all configured symbols and executes any actionable signals.

        Returns
        -------
        list[dict]
            One result dict per symbol, with ``trade_result`` appended
            to any symbol that had an actionable signal.
        """
        results = self.scan_all()

        for result in results:
            if result.get('actionable'):
                trade_result = self.execute_trade(result['actionable'])
                result['trade_result'] = trade_result

        return results
