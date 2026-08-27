"""
Standalone Trading Engine

Runs the trading engine directly (without the API server).
Useful for running on a VPS where you just want the bot to trade.

Usage:
    python run_engine.py                    # Use defaults from .env
    python run_engine.py --interval 15       # Scan every 15 minutes
    python run_engine.py --symbols BTCUSD,XAUUSD

REQUIREMENTS:
- MT5 Terminal must be running on this machine
- .env file must be configured with MT5_BROKER, MT5_LOGIN, MT5_PASSWORD
- Start in DEMO mode first to validate!
"""
import argparse
import os
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from utils.logging import setup_logging, logger
from mt5_connector.connector import MT5Connector
from engine.trading_engine import TradingEngine


def parse_args():
    parser = argparse.ArgumentParser(description='MT5 AI Trading Engine')
    parser.add_argument('--interval', type=int, default=15,
                        help='Scan interval in minutes (default: 15)')
    parser.add_argument('--symbols', type=str, default=None,
                        help='Comma-separated symbols to trade (default: from .env)')
    parser.add_argument('--once', action='store_true',
                        help='Run one scan cycle and exit')
    parser.add_argument('--dry-run', action='store_true',
                        help='Scan and analyze but do NOT execute any trades')
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(settings.log_level, settings.log_file)

    symbols = args.symbols.split(',') if args.symbols else settings.trading_symbols

    print(f"\n{'='*60}")
    print(f"  MT5 AI Trading Engine v2.0")
    print(f"  Mode: {settings.trading_mode.upper()}")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Interval: {args.interval} minutes")
    print(f"  Dry run: {args.dry_run}")
    print(f"{'='*60}\n")

    if settings.trading_mode.lower() == 'live':
        logger.warning('*** LIVE TRADING MODE - REAL MONEY AT RISK ***')
        logger.warning('*** Press Ctrl+C within 10 seconds to abort ***')
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print('\nAborted. Good call if you were not ready.')
            sys.exit(0)
    else:
        logger.info('DEMO mode - safe for testing')

    # Connect to MT5
    login = int(os.environ.get('MT5_LOGIN', '0'))
    password = os.environ.get('MT5_PASSWORD', '')
    broker = os.environ.get('MT5_BROKER', 'exness')
    account_type = os.environ.get('MT5_ACCOUNT_TYPE', 'demo')
    server = os.environ.get('MT5_SERVER', None)

    if login == 0 or not password:
        logger.error('MT5_LOGIN and MT5_PASSWORD must be set in .env or environment')
        sys.exit(1)

    connector = MT5Connector(broker=broker, account_type=account_type)
    success = connector.connect(login=login, password=password, server=server)
    if not success:
        logger.error('Failed to connect to MT5. Is the terminal running?')
        sys.exit(1)

    account = connector.get_account_info()
    logger.info(f'Connected. Balance: ${account.balance:.2f}, Equity: ${account.equity:.2f}')

    engine = TradingEngine(connector)

    # Main loop
    cycle = 0
    try:
        while True:
            cycle += 1
            logger.info(f'--- Cycle {cycle} ---')

            # Check connection
            if not connector.is_connected():
                logger.warning('MT5 connection lost. Attempting reconnect...')
                success = connector.reconnect(login=login, password=password, server=server)
                if not success:
                    logger.error('Reconnect failed. Waiting 60s...')
                    time.sleep(60)
                    continue

            # Scan
            results = engine.scan_all(symbols)

            for r in results:
                symbol = r['symbol']
                confluence = r.get('confluence', {})
                actionable = r.get('actionable')
                errors = r.get('errors', [])

                if errors:
                    for e in errors:
                        logger.warning(f'{symbol}: {e}')

                if confluence:
                    logger.info(f'{symbol}: Confluence={confluence.get("direction", "?")} '
                               f'(score={confluence.get("score", 0):.0%})')

                if actionable:
                    logger.info(f'{symbol}: ACTIONABLE - {actionable["direction"]} '
                               f'Conf={actionable["confidence"]:.2f} '
                               f'R:R={actionable["risk_reward"]:.1f} '
                               f'Vol={actionable["volume"]}')

                    if not args.dry_run:
                        trade_result = engine.execute_trade(actionable)
                        if trade_result.get('success'):
                            logger.info(f'TRADE EXECUTED: Ticket={trade_result["ticket"]} '
                                       f'@ {trade_result["price"]}')
                        else:
                            logger.error(f'TRADE FAILED: {trade_result.get("error")}')
                elif r.get('risk_failures'):
                    logger.info(f'{symbol}: Signal found but risk check failed: {r["risk_failures"]}')
                else:
                    logger.info(f'{symbol}: No actionable signal (default: NO TRADE)')

            if args.once:
                break

            logger.info(f'Sleeping {args.interval} minutes...')
            time.sleep(args.interval * 60)

    except KeyboardInterrupt:
        logger.info('Engine stopped by user.')
    finally:
        connector.disconnect()
        logger.info('Disconnected from MT5.')


if __name__ == '__main__':
    main()
