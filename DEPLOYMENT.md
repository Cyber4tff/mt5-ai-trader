# MT5 AI Trader — Windows Deployment Guide

## The Short Answer

**YES, you download this entire project folder to your Windows PC. No more coding is needed. Everything is already built.**

You then:
1. Install 2 free tools (Python + Node.js) if you don't have them
2. Double-click `start.bat` to launch everything
3. Open MT5 desktop and log in
4. Open your browser to `http://localhost:3000`

That's it.

---

## What You're Downloading

This project has 2 parts that run together:

| Part | What it does | Port |
|------|-------------|------|
| **Next.js Frontend** | The website you see in the browser | 3000 |
| **Python Trading Engine** | The AI analysis + MT5 trade execution | 8001 |

Both run on YOUR PC. Nothing is sent to any external server (except market data from Yahoo Finance for analysis).

---

## Step-by-Step Instructions

### STEP 1: Download the Project

Download this entire project folder as a ZIP file. Extract it to a folder on your Windows PC, for example:
```
C:\MT5-AI-Trader\
```

The folder should contain these files at the top level:
- `start.bat` ← **This is your main launcher**
- `start-backend.bat`
- `start-frontend.bat`
- `package.json`
- `src/` folder
- `mini-services/` folder
- `prisma/` folder

### STEP 2: Install Prerequisites

You need 2 free tools installed on your PC:

#### A. Python 3.10 or newer
1. Go to: https://www.python.org/downloads/
2. Download the latest Python 3
3. **IMPORTANT: During installation, CHECK the box that says "Add Python to PATH"**
4. Click Install Now
5. To verify: open Command Prompt and type `python --version`

#### B. Node.js 20 or newer
1. Go to: https://nodejs.org/
2. Download the **LTS** version (recommended)
3. Install it (default settings are fine)
4. To verify: open Command Prompt and type `node --version`

#### C. MetaTrader 5 Desktop (you already have this)
- Just make sure it's installed and working
- You'll log in with your demo account: Login `5639816`, Server `Headway-Demo`

### STEP 3: Launch the System

**Easy way (recommended):**
1. Double-click `start.bat` in the project folder
2. It will open 2 command windows automatically:
   - Window 1: Python Trading Engine (port 8001)
   - Window 2: Next.js Website (port 3000)
3. Wait about 15-20 seconds for both to finish loading

**Manual way (if you prefer):**
1. Open a command prompt in the project folder
2. Run this to start the Python backend:
   ```
   start-backend.bat
   ```
3. Open ANOTHER command prompt in the project folder
4. Run this to start the website:
   ```
   start-frontend.bat
   ```

### STEP 4: Open MT5 Desktop

1. Open MetaTrader 5 on your PC
2. Log in with your credentials:
   - **Login:** `5639816`
   - **Password:** `Cyber7220$`
   - **Server:** `Headway-Demo`
3. Keep MT5 running in the background

### STEP 5: Open the Website

1. Open your browser (Chrome recommended)
2. Go to: **http://localhost:3000**
3. The website should load and automatically detect that MT5 is running
4. You'll see "MT5 Connected" status — this means trades can be executed

### STEP 6: Start Trading

1. Click **"Start Scanning"** on the website
2. The AI will analyze the markets and generate signals
3. When a signal appears, you can:
   - **Manually authorize** each trade (click the trade button, review details, confirm)
   - **Enable Auto-Execute** (toggle in the panel — the system will ask for security confirmation first)

---

## How It Works (Simple Explanation)

```
Your Browser (localhost:3000)
    ↓
Next.js Website (shows the UI)
    ↓
Python Trading Engine (localhost:8001)  ← AI analysis happens here
    ↓
MetaTrader5 Python Library
    ↓
MT5 Desktop App (running on your PC)  ← Actual trades go through here
    ↓
Your Broker (Headway-Demo server)     ← Orders sent to market
```

**Key point:** The Python `MetaTrader5` library can ONLY connect to the MT5 desktop app running on the SAME computer. That's why you need both on your Windows PC.

---

## Troubleshooting

### "MT5 Not Available" on the website
- **Cause:** MT5 desktop is not running, or the Python MetaTrader5 library failed to install
- **Fix:** Make sure MT5 desktop is open and logged in. Check the backend window for errors.

### Backend window shows errors about missing packages
- **Fix:** Open command prompt and run:
  ```
  cd mini-services\trading-engine
   pip install -r requirements.txt
n  ```

### Frontend won't start / "npm not found"
- **Fix:** Node.js is not installed. Go to https://nodejs.org/ and install it.

### "Python not found" error
- **Fix:** Python is not in your PATH. Reinstall Python and CHECK "Add to PATH".

### Port 3000 or 8001 already in use
- **Fix:** Close any other programs using those ports. Or restart your PC.

### Trades not executing even though MT5 shows connected
- Check that you're in **Live Mode** (not Demo mode) on the website
- Check that the symbol name matches (e.g., `EURUSD` not `EURUSDm`)
- Check the backend window for error messages

---

## File Structure (What's Important)

```
your-project-folder/
├── start.bat                    ← Double-click this to launch everything
├── start-backend.bat            ← Starts Python trading engine only
├── start-frontend.bat           ← Starts the website only
├── package.json                 ← Node.js dependencies
├── src/                         ← Website source code (Next.js)
│   ├── app/
│   │   ├── page.tsx             ← Main page
│   │   └── api/trading/         ← API proxy to Python backend
│   ├── components/trading/      ← UI components
│   └── lib/                     ← Trading logic, API client, store
├── mini-services/
│   └── trading-engine/
│       ├── requirements.txt     ← Python dependencies
│       └── engine/
│           ├── main.py          ← Python FastAPI server + MT5 connection
│           ├── analysis.py      ← AI analysis engine
│           ├── data_fetcher.py  ← Market data (Yahoo Finance)
│           ├── paper_trading.py ← Paper trading simulation
│           └── models.py        ← Data models
├── prisma/
│   └── schema.prisma            ← Database schema
└── public/                      ← Static assets
```

---

## Summary

| Question | Answer |
|----------|--------|
| Do I need to write more code? | **No. Everything is done.** |
| Do I download the project? | **Yes. Download the whole folder.** |
| Do I need MT5 on my PC? | **Yes. MT5 desktop must be running.** |
| What do I install? | **Python 3 + Node.js (both free)** |
| How do I start it? | **Double-click `start.bat`** |
| Where do I open it? | **http://localhost:3000** |
