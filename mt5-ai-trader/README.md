# MT5 AI Trader v2.0

AI-assisted multi-timeframe trading system for MetaTrader 5.
Supports BTC, Gold/XAUUSD, Forex, and other MT5 instruments.

**Strict NO TRADE default.** A trade only executes when ALL conditions are satisfied.

---

## Features

- **Multi-Timeframe Analysis:** D1 → H4 → H1 → M15 → M5 hierarchy
- **Naked Forex Patterns:** Big Shadow, Kangaroo Tail, Last Kiss, Double Hit
- **Market Structure:** BOS, CHOCH, Swing Points, Liquidity Sweeps
- **AI Decision Layer:** Structured BUY / SELL / NO TRADE with confidence scoring
- **Risk Management:** Daily drawdown, consecutive losses, max positions, spread limits
- **Correct Position Sizing:** Uses actual broker tick_value/tick_size (not hardcoded)
- **REST API + WebSocket:** Full control via FastAPI
- **Standalone Engine:** Run without the API on a VPS
- **Broker Support:** Exness, OctaFX, Headway (Nigerian brokers)

---

## Requirements

- **Python 3.9+** (tested on 3.10, 3.11)
- **MetaTrader 5 Terminal** installed and running on Windows
- **Windows** (MT5 Python API only works on Windows)

## Installation

```bash
# 1. Clone/navigate to the project
cd mt5-ai-trader

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac (for tests only)
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env with your settings
```

## Configuration (.env)

```env
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-random-64-char-string

# Trading
TRADING_SYMBOLS=BTCUSD,XAUUSD,GBPUSD,EURUSD,USDJPY
RISK_PER_TRADE=0.02
MAX_DAILY_DRAWDOWN_PCT=0.06
MAX_CONSECUTIVE_LOSSES=3
MAX_OPEN_POSITIONS=3
MAX_TRADES_PER_DAY=10
MAX_SPREAD_POINTS=50
MIN_RISK_REWARD=1.5

# Mode: "demo" or "live"
TRADING_MODE=demo
```

### For the standalone engine, also set:

```env
MT5_BROKER=exness
MT5_ACCOUNT_TYPE=demo
MT5_LOGIN=your_login_number
MT5_PASSWORD=your_password
MT5_SERVER=Exness-MT5Trial  # or leave empty for default
```

> **NEVER commit .env to version control.** Credentials are read from environment variables only.

---

## How to Start

### Option A: API Server

```bash
python run.py
```

Then open `http://localhost:8000/docs` for the interactive API documentation.

### Option B: Standalone Trading Engine

```bash
# Dry run (scan but don't trade)
python run_engine.py --dry-run --once

# Live engine (demo account)
python run_engine.py --interval 15

# Custom symbols
python run_engine.py --symbols BTCUSD,XAUUSD --interval 30
```

### Option C: Auto-Trade via API

1. Start the API: `python run.py`
2. Connect to MT5 via `POST /connect`
3. Start auto-trading via `POST /auto-trade/{session_id}`

---

## How to Run Tests

Tests do NOT require MT5 to be installed. They use synthetic data and mocks.

```bash
# From project root
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_position_sizing.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## How to Demo Trade Safely

1. Set `TRADING_MODE=demo` in `.env`
2. Use a **demo account** from your broker (Exness, OctaFX, Headway)
3. Start with the API server: `python run.py`
4. Connect via the `/connect` endpoint with demo credentials
5. Use `/scan` to see what the system would trade
6. Review the `actionable_signal` field — it shows the full trade plan
7. Only enable `/auto-trade` after reviewing scan results for several cycles
8. Monitor via the WebSocket `/ws/{session_id}` endpoint

---

## How to Enable Live Trading (USE EXTREME CAUTION)

1. **Complete at least 2 weeks of successful demo trading first**
2. Change `TRADING_MODE=live` in `.env`
3. Start with **minimum risk**: `RISK_PER_TRADE=0.005` (0.5%)
4. Use `MAX_OPEN_POSITIONS=1` to limit exposure
5. Set `MAX_TRADES_PER_DAY=3`
6. Monitor closely for the first week
7. **This system does NOT guarantee profitability.** Past patterns do not predict future results.

---

## Project Structure

```
mt5-ai-trader/
├── app/                    # FastAPI application
│   └── main.py             # API endpoints
├── ai_layer/               # AI decision layer
│   └── decision_engine.py  # BUY/SELL/NO TRADE decisions
├── config/
│   └── settings.py         # Configuration (env vars)
├── engine/
│   └── trading_engine.py   # Main orchestrator
├── models/
│   ├── enums.py            # Signal types, timeframes, biases
│   ├── market.py           # CandleData, SymbolSpec, SRLevel
│   └── signals.py          # TradeSignal, AIDecision, MarketAnalysis
├── mt5_connector/
│   └── connector.py        # MT5 connection, orders, data
├── risk/
│   ├── manager.py          # Risk gate (9 checks)
│   └── position_sizer.py   # Correct lot sizing
├── strategies/
│   ├── base.py             # Abstract base strategy
│   ├── market_structure.py # BOS, CHOCH, swing points
│   ├── multi_timeframe.py  # D1→H4→H1→M15→M5 analysis
│   ├── naked_forex.py      # Price action patterns
│   └── support_resistance.py # S/R level detection
├── tests/                  # 78 tests (no MT5 required)
├── utils/
│   ├── helpers.py          # Price/volume normalization, ATR
│   └── logging.py          # Loguru setup
├── .env.example            # Environment template
├── requirements.txt
├── run.py                  # API server launcher
└── run_engine.py           # Standalone engine
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/connect` | Connect to MT5 |
| POST | `/disconnect/{session_id}` | Disconnect |
| GET | `/sessions` | List active sessions |
| GET | `/account/{session_id}` | Account info & positions |
| GET | `/symbol/{session_id}/{symbol}` | Symbol specifications |
| POST | `/scan/{session_id}` | Full MTF scan |
| POST | `/trade/{session_id}` | Place manual trade |
| POST | `/close/{session_id}/{ticket}` | Close position |
| POST | `/modify/{session_id}/{ticket}` | Modify SL/TP |
| POST | `/auto-trade/{session_id}` | Toggle auto-trading |
| GET | `/risk-status/{session_id}` | Daily risk summary |
| GET | `/ai-status` | System configuration |
| WS | `/ws/{session_id}` | Real-time updates |

---

## MT5 Setup (Windows)

1. Download and install MetaTrader 5 from your broker's website
2. Open MT5, log into your **demo** account
3. Enable algorithmic trading: Tools → Options → Expert Advisors → check "Allow Algo Trading"
4. Leave MT5 running in the background
5. This Python project connects to the running MT5 terminal via its Python API

---

## Disclaimer

**This software is for educational and research purposes only.**

- Trading involves substantial risk of loss.
- Past performance does not guarantee future results.
- This system is NOT guaranteed to be profitable.
- Always test extensively on DEMO accounts before considering live trading.
- The developers assume no liability for any financial losses.
- Do NOT trade with money you cannot afford to lose.
