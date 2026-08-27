import { create } from "zustand";
import type {
  ConnectionState,
  AccountInfo,
  Position,
  ScanResult,
  DailyRiskSummary,
  AIStatus,
  AutoTradeState,
  ActionableSignal,
} from "./trading-types";

// ─── Demo Data Generators ─────────────────────────────────────

function randomBetween(min: number, max: number, decimals = 2): number {
  return Number((Math.random() * (max - min) + min).toFixed(decimals));
}

function generateDemoAccount(): AccountInfo {
  return {
    balance: 10523.45,
    equity: 10782.30,
    margin: 2145.60,
    free_margin: 8636.70,
    leverage: 500,
    profit: 258.85,
    margin_level: 502.48,
  };
}

function generateDemoPositions(): Position[] {
  return [
    {
      ticket: 8234567,
      symbol: "XAUUSD",
      type: "BUY",
      volume: 0.05,
      open_price: 2345.20,
      current_price: 2352.80,
      sl: 2335.50,
      tp: 2370.00,
      profit: 38.00,
      swap: -0.12,
      comment: "AI Engine: conf=0.78",
      time: new Date(Date.now() - 3600000 * 2).toISOString(),
    },
    {
      ticket: 8234580,
      symbol: "BTCUSD",
      type: "SELL",
      volume: 0.02,
      open_price: 67450.00,
      current_price: 67280.50,
      sl: 67900.00,
      tp: 66500.00,
      profit: 34.00,
      swap: 0.00,
      comment: "AI Engine: conf=0.72",
      time: new Date(Date.now() - 3600000 * 1).toISOString(),
    },
  ];
}

function generateDemoScanResults(): ScanResult[] {
  return [
    {
      symbol: "XAUUSD",
      confluence: {
        direction: "bullish",
        score: 0.8,
        higher_tf_bias: "bullish",
        trend_alignment: true,
        factors: [
          "D1: bullish bias",
          "H4: bullish bias",
          "H1: bullish bias",
          "M15: bullish bias",
          "M5: neutral",
        ],
        bullish_ratio: 0.8,
        bearish_ratio: 0.0,
      },
      decisions_count: 2,
      actionable: {
        symbol: "XAUUSD",
        direction: "BUY",
        entry: 2353.50,
        sl: 2335.00,
        tp: 2385.00,
        volume: 0.04,
        confidence: 0.82,
        risk_reward: 1.98,
        confirmation_factors: [
          "HTF bullish bias aligns with BUY signal",
          "Strong MTF confluence (80%)",
          "All timeframes agree on direction",
          "Excellent R:R (2.0)",
          "BOS bullish on H4",
          "Entry near support level on H1",
        ],
        confluence: {
          direction: "bullish",
          score: 0.8,
          higher_tf_bias: "bullish",
          trend_alignment: true,
          factors: [],
          bullish_ratio: 0.8,
          bearish_ratio: 0.0,
        },
      },
      errors: [],
      timeframes: {
        D1: { trend: "UP", bias: "bullish", atr: 32.5, volatility: "normal", signals_count: 0, structure_breaks: 1, sr_levels: 3 },
        H4: { trend: "UP", bias: "bullish", atr: 12.8, volatility: "normal", signals_count: 1, structure_breaks: 2, sr_levels: 4 },
        H1: { trend: "UP", bias: "bullish", atr: 5.2, volatility: "normal", signals_count: 1, structure_breaks: 1, sr_levels: 5 },
        M15: { trend: "UP", bias: "bullish", atr: 2.1, volatility: "low", signals_count: 0, structure_breaks: 0, sr_levels: 3 },
        M5: { trend: "RANGING", bias: "neutral", atr: 0.9, volatility: "low", signals_count: 0, structure_breaks: 0, sr_levels: 2 },
      },
    },
    {
      symbol: "BTCUSD",
      confluence: {
        direction: "bearish",
        score: 0.6,
        higher_tf_bias: "bearish",
        trend_alignment: false,
        factors: [
          "D1: bearish bias",
          "H4: bearish bias",
          "H1: neutral",
          "M15: neutral",
          "M5: bullish",
        ],
        bullish_ratio: 0.2,
        bearish_ratio: 0.4,
      },
      decisions_count: 1,
      actionable: null,
      errors: [],
      risk_failures: ["R:R (1.2) below minimum (1.5)"],
      timeframes: {
        D1: { trend: "DOWN", bias: "bearish", atr: 1850.0, volatility: "high", signals_count: 0, structure_breaks: 2, sr_levels: 2 },
        H4: { trend: "DOWN", bias: "bearish", atr: 720.0, volatility: "high", signals_count: 1, structure_breaks: 1, sr_levels: 3 },
        H1: { trend: "RANGING", bias: "neutral", atr: 310.0, volatility: "normal", signals_count: 0, structure_breaks: 0, sr_levels: 4 },
        M15: { trend: "RANGING", bias: "neutral", atr: 125.0, volatility: "normal", signals_count: 0, structure_breaks: 0, sr_levels: 2 },
        M5: { trend: "UP", bias: "bullish", atr: 52.0, volatility: "normal", signals_count: 0, structure_breaks: 0, sr_levels: 1 },
      },
    },
  ];
}

function generateDemoRisk(): DailyRiskSummary {
  return {
    date: new Date().toISOString().split("T")[0],
    realized_pnl: 85.30,
    trades_count: 3,
    consecutive_losses: 0,
    remaining_trades: 7,
    remaining_loss_limit: 4.2,
  };
}

function generateDemoAIStatus(): AIStatus {
  return {
    strategy: "Naked Forex Price Action + Market Structure",
    patterns: ["Big Shadow", "Kangaroo Tail", "Last Kiss", "Double Hit"],
    structure_analysis: ["BOS", "CHOCH", "Liquidity Sweeps", "Swing Points"],
    mtf_timeframes: ["D1", "H4", "H1", "M15", "M5"],
    symbols_focus: ["BTCUSD", "XAUUSD"],
    brokers: ["exness", "octafx", "headway"],
    confidence_threshold: 0.65,
    high_confidence: 0.80,
    risk_per_trade: 0.02,
    max_daily_loss_pct: 0.06,
    max_consecutive_losses: 3,
    max_open_positions: 3,
    max_trades_per_day: 10,
    max_spread_points: 50,
    min_risk_reward: 1.5,
    mode: "demo",
    trailing_stop: true,
  };
}

// ─── Store Interface ──────────────────────────────────────────

interface TradingStore {
  // State
  demoMode: boolean;
  connection: ConnectionState;
  positions: Position[];
  pendingOrders: Position[];
  scanResults: ScanResult[];
  riskSummary: DailyRiskSummary;
  aiStatus: AIStatus;
  autoTrade: AutoTradeState;
  scanning: boolean;
  scanLog: string[];

  // Actions
  setDemoMode: (enabled: boolean) => void;
  connect: (broker: string, login: number, password: string, server?: string) => Promise<boolean>;
  disconnect: () => void;
  fetchAccount: () => Promise<void>;
  scanMarkets: (symbols?: string[]) => Promise<void>;
  toggleAutoTrade: (enabled: boolean, interval?: number) => void;
  closePosition: (ticket: number) => Promise<void>;
  simulateTick: () => void;
}

export const useTradingStore = create<TradingStore>((set, get) => ({
  // ── Initial State ───────────────────────────────────────────
  demoMode: true,
  connection: {
    connected: false,
    sessionId: null,
    broker: null,
    server: null,
    account: null,
    lastUpdate: null,
  },
  positions: [],
  pendingOrders: [],
  scanResults: [],
  riskSummary: generateDemoRisk(),
  aiStatus: generateDemoAIStatus(),
  autoTrade: {
    enabled: false,
    intervalMinutes: 15,
    symbols: ["BTCUSD", "XAUUSD"],
    lastScan: null,
    cycleCount: 0,
  },
  scanning: false,
  scanLog: ["System initialized. Awaiting connection..."],

  // ── Actions ─────────────────────────────────────────────────
  setDemoMode: (enabled) => set({ demoMode: enabled }),

  connect: async (broker, login, password, server) => {
    const state = get();
    if (state.demoMode) {
      // Simulate connection
      await new Promise((r) => setTimeout(r, 1500));
      const account = generateDemoAccount();
      const sessionId = `${broker}_${login}_${Date.now()}`;
      set({
        connection: {
          connected: true,
          sessionId,
          broker,
          server: server || `${broker}-MT5Trial`,
          account,
          lastUpdate: new Date().toISOString(),
        },
        positions: generateDemoPositions(),
        scanLog: [`[${new Date().toLocaleTimeString()}] Connected to ${broker} (${server || "auto"}). Balance: $${account.balance.toLocaleString()}`],
      });
      return true;
    }
    // Real API call would go here
    return false;
  },

  disconnect: () => {
    set({
      connection: {
        connected: false,
        sessionId: null,
        broker: null,
        server: null,
        account: null,
        lastUpdate: null,
      },
      positions: [],
      pendingOrders: [],
      scanResults: [],
      autoTrade: { enabled: false, intervalMinutes: 15, symbols: ["BTCUSD", "XAUUSD"], lastScan: null, cycleCount: 0 },
      scanLog: [`[${new Date().toLocaleTimeString()}] Disconnected.`],
    });
  },

  fetchAccount: async () => {
    const state = get();
    if (state.demoMode && state.connection.connected) {
      // Simulate price fluctuation
      await new Promise((r) => setTimeout(r, 200));
      const account = { ...state.connection.account! };
      account.equity = account.balance + randomBetween(-500, 800);
      account.profit = account.equity - account.balance;
      account.free_margin = account.equity - account.margin;
      account.margin_level = account.margin > 0 ? (account.equity / account.margin) * 100 : 0;
      set({
        connection: { ...state.connection, account, lastUpdate: new Date().toISOString() },
      });
    }
  },

  scanMarkets: async (symbols) => {
    const state = get();
    if (!state.connection.connected) return;

    set({ scanning: true });
    const ts = new Date().toLocaleTimeString();
    set((s) => ({ scanLog: [...s.scanLog, `[${ts}] Scanning ${symbols?.join(", ") || "all symbols"}...`] }));

    await new Promise((r) => setTimeout(r, 2000));

    const results = generateDemoScanResults();
    // Add some randomness to confidence/score
    results.forEach((r) => {
      if (r.actionable) {
        r.actionable.confidence = Math.min(1, r.actionable.confidence + randomBetween(-0.05, 0.05, 3));
      }
      if (r.confluence) {
        r.confluence.score = Math.min(1, r.confluence.score + randomBetween(-0.05, 0.05, 3));
      }
    });

    const actionableCount = results.filter((r) => r.actionable).length;
    const noTradeCount = results.length - actionableCount;

    set((s) => ({
      scanResults: results,
      scanning: false,
      autoTrade: { ...s.autoTrade, lastScan: new Date().toISOString(), cycleCount: s.autoTrade.cycleCount + 1 },
      scanLog: [
        ...s.scanLog,
        `[${ts}] Scan complete: ${actionableCount} actionable, ${noTradeCount} NO TRADE`,
        ...results.flatMap((r) => {
          const msgs: string[] = [];
          if (r.actionable) {
            msgs.push(`[${ts}] ${r.symbol}: ACTIONABLE ${r.actionable.direction} conf=${r.actionable.confidence.toFixed(2)} R:R=${r.actionable.risk_reward.toFixed(1)}`);
          } else if (r.risk_failures?.length) {
            msgs.push(`[${ts}] ${r.symbol}: Signal rejected → ${r.risk_failures[0]}`);
          } else {
            msgs.push(`[${ts}] ${r.symbol}: NO TRADE`);
          }
          return msgs;
        }),
      ],
    }));
  },

  toggleAutoTrade: (enabled, interval) => {
    set((s) => ({
      autoTrade: { ...s.autoTrade, enabled, intervalMinutes: interval ?? s.autoTrade.intervalMinutes },
      scanLog: [
        ...s.scanLog,
        `[${new Date().toLocaleTimeString()}] Auto-trade ${enabled ? "ENABLED" : "DISABLED"} (interval: ${interval ?? s.autoTrade.intervalMinutes}min)`,
      ],
    }));
  },

  closePosition: async (ticket: number) => {
    const state = get();
    if (state.demoMode) {
      await new Promise((r) => setTimeout(r, 500));
      const closed = state.positions.find((p) => p.ticket === ticket);
      set({
        positions: state.positions.filter((p) => p.ticket !== ticket),
        scanLog: [
          ...state.scanLog,
          `[${new Date().toLocaleTimeString()}] Closed position #${ticket} (${closed?.symbol} ${closed?.type}) P&L: $${closed?.profit.toFixed(2)}`,
        ],
      });
    }
  },

  simulateTick: () => {
    const state = get();
    if (!state.connection.connected || state.demoMode) return;
    // Slightly shift current prices on positions
    const updated = state.positions.map((p) => {
      const shift = p.type === "BUY" ? randomBetween(-2, 3, 2) : randomBetween(-3, 2, 2);
      const newPrice = p.current_price + shift;
      const pnlPerLot = p.type === "BUY" ? (newPrice - p.open_price) : (p.open_price - newPrice);
      return { ...p, current_price: newPrice, profit: pnlPerLot * p.volume * (p.symbol.includes("XAU") ? 100 : 1) };
    });
    set({ positions: updated });
  },
}));
