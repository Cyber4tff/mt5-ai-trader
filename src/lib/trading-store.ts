import { create } from "zustand";
import type {
  ConnectionState,
  AccountInfo,
  Position,
  ScanResult,
  DailyRiskSummary,
  AIStatus,
  AutoTradeState,
  SessionMode,
} from "./trading-types";

// ─── Live connection tracking ────────────────────────────────
export interface LiveConnectionState {
  mt5Confirmed: boolean;
  manualBalance: string;
  manualEquity: string;
  connectedAt: string | null;
}
import { getWebTerminalUrl } from "./trading-types";
import { tradingApi, type ConnectParams } from "./trading-api";

// ─── Empty defaults (NO mock data) ────────────────────────────

const EMPTY_ACCOUNT: AccountInfo = {
  balance: 0,
  equity: 0,
  margin: 0,
  free_margin: 0,
  leverage: 0,
  profit: 0,
  margin_level: 0,
};

const EMPTY_RISK: DailyRiskSummary = {
  date: new Date().toISOString().split("T")[0],
  realized_pnl: 0,
  trades_count: 0,
  consecutive_losses: 0,
  remaining_trades: 0,
  remaining_loss_limit: 0,
};

const EMPTY_AI: AIStatus = {
  strategy: "—",
  patterns: [],
  structure_analysis: [],
  mtf_timeframes: [],
  symbols_focus: [],
  brokers: [],
  confidence_threshold: 0,
  high_confidence: 0,
  risk_per_trade: 0,
  max_daily_loss_pct: 0,
  max_consecutive_losses: 0,
  max_open_positions: 0,
  max_trades_per_day: 0,
  max_spread_points: 0,
  min_risk_reward: 0,
  mode: "live",
  trailing_stop: false,
};

const EMPTY_CONNECTION: ConnectionState = {
  connected: false,
  sessionId: null,
  broker: null,
  server: null,
  account: null,
  lastUpdate: null,
  mode: "live",
  selectedBrokerId: null,
  mt5Server: null,
  webTerminalUrl: null,
  analysisSessionId: null,
};

// ─── Store Interface ──────────────────────────────────────

interface TradingStore {
  // State
  backendAvailable: boolean;
  backendChecking: boolean;
  connection: ConnectionState;
  liveState: LiveConnectionState;
  positions: Position[];
  pendingOrders: Position[];
  scanResults: ScanResult[];
  riskSummary: DailyRiskSummary;
  aiStatus: AIStatus;
  autoTrade: AutoTradeState;
  scanning: boolean;
  scanLog: string[];
  fetchingAccount: boolean;

  // Actions
  connectLive: (brokerName: string, brokerId: string, mt5Server: string) => Promise<void>;
  startPaperTrading: (balance?: number, leverage?: number) => Promise<boolean>;
  connect: (broker: string, login: number, password: string, server?: string) => Promise<boolean>;
  disconnect: () => Promise<void>;
  confirmMT5Connection: (balance?: string, equity?: string) => void;
  unconfirmMT5Connection: () => void;
  fetchAccount: () => Promise<void>;
  fetchRiskStatus: () => Promise<void>;
  fetchAIStatus: () => Promise<void>;
  scanMarkets: (symbols?: string[]) => Promise<void>;
  toggleAutoTrade: (enabled: boolean, interval?: number) => Promise<void>;
  closePosition: (ticket: number) => Promise<void>;
  checkBackendHealth: () => Promise<boolean>;
}

function log(state: TradingStore, msg: string): string[] {
  const ts = new Date().toLocaleTimeString();
  return [...state.scanLog.slice(-200), `[${ts}] ${msg}`];
}

function parsePosition(p: Record<string, unknown>): Position {
  return {
    ticket: p.ticket as number,
    symbol: (p.symbol as string) || "",
    type: ((p.type as string) || "BUY").toUpperCase() as "BUY" | "SELL",
    volume: p.volume as number,
    open_price: p.open_price as number,
    current_price: p.current_price as number,
    sl: p.sl as number,
    tp: p.tp as number,
    profit: p.profit as number,
    swap: p.swap as number,
    comment: (p.comment as string) || "",
    time: p.time as string,
  };
}

export const useTradingStore = create<TradingStore>((set, get) => ({
  // ── Initial State ──────────────────────────────
  backendAvailable: false,
  backendChecking: false,
  connection: { ...EMPTY_CONNECTION },
  liveState: {
    mt5Confirmed: false,
    manualBalance: "",
    manualEquity: "",
    connectedAt: null,
  },
  positions: [],
  pendingOrders: [],
  scanResults: [],
  riskSummary: EMPTY_RISK,
  aiStatus: EMPTY_AI,
  autoTrade: {
    enabled: false,
    intervalMinutes: 15,
    symbols: ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD"],
    lastScan: null,
    cycleCount: 0,
  },
  scanning: false,
  scanLog: ["System ready. Select your broker to start live trading."],
  fetchingAccount: false,

  // ── Connect Live (MT5 Web Terminal) ────────
  connectLive: async (brokerName: string, brokerId: string, mt5Server: string) => {
    const webTerminalUrl = getWebTerminalUrl(brokerId, mt5Server);
    const liveId = `live-${brokerId}-${Date.now()}`;

    // Show connected state immediately
    set({
      connection: {
        connected: true,
        sessionId: liveId,
        broker: brokerName,
        server: mt5Server,
        account: null,
        lastUpdate: new Date().toISOString(),
        mode: "live",
        selectedBrokerId: brokerId,
        mt5Server,
        webTerminalUrl,
        analysisSessionId: null,
      },
      positions: [],
      pendingOrders: [],
      scanResults: [],
      riskSummary: EMPTY_RISK,
      scanLog: [`[new Date().toLocaleTimeString()}] ✅ LIVE MODE: Connected to ${brokerName} | Server: ${mt5Server}`],
    });

    // Create a background paper session for AI analysis
    let analysisId: string | null = null;
    try {
      const res = await tradingApi.connect({
        broker: "paper",
        account_type: "paper",
        balance: 10000,
        leverage: 100,
      });
      if (res.success) {
        analysisId = res.session_id;
      }
    } catch {
      // Analysis engine unavailable
    }

    // Now update state with the analysis session ID
    const currentState = get();
    set({
      connection: { ...currentState.connection, analysisSessionId: analysisId },
      backendAvailable: analysisId !== null,
      scanLog: [
        ...currentState.scanLog,
        analysisId
          ? `[${new Date().toLocaleTimeString()}] AI analysis engine ready. Scan markets to get trading signals.`
          : `[${new Date().toLocaleTimeString()}] ⚠ AI engine could not start. Scanning will be unavailable.`,
      ],
    });

    get().checkBackendHealth();
    get().fetchAIStatus();
  },

  // ── Check Backend Health ─────────────────────────────────────────────────
  checkBackendHealth: async () => {
    set({ backendChecking: true });
    try {
      await tradingApi.getHealth();
      set({ backendAvailable: true, backendChecking: false });
      return true;
    } catch {
      set({ backendAvailable: false, backendChecking: false });
      return false;
    }
  },

  // ── Start Paper Trading ──────────────────────────────────────────────
  startPaperTrading: async (balance = 10000, leverage = 100) => {
    const state = get();
    set((s) => ({ scanLog: log(s, `Starting paper trading... Balance: $${balance.toLocaleString()} | Leverage: 1:${leverage}`) }));

    try {
      const res = await tradingApi.connect({
        broker: "paper",
        account_type: "paper",
        balance,
        leverage,
      });

      if (!res.success) {
        set((s) => ({ scanLog: log(s, `Failed to start: ${JSON.stringify(res)}`) }));
        return false;
      }

      const account: AccountInfo = {
        balance: res.account.balance,
        equity: res.account.equity,
        margin: res.account.margin || 0,
        free_margin: res.account.free_margin,
        leverage: res.account.leverage,
        profit: 0,
        margin_level: res.account.margin_level,
      };

      const conn: ConnectionState = {
        connected: true,
        sessionId: res.session_id,
        broker: res.broker,
        server: res.server,
        account,
        lastUpdate: new Date().toISOString(),
        mode: "paper",
        selectedBrokerId: null,
        mt5Server: null,
        webTerminalUrl: null,
        analysisSessionId: res.session_id,
      };

      set({
        connection: conn,
        backendAvailable: true,
        positions: [],
        scanResults: [],
        riskSummary: EMPTY_RISK,
        scanLog: log(
          { ...get(), connection: conn },
          `Paper trading started. Balance: $${account.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} | Mode: PAPER`
        ),
      });

      get().fetchAccount();
      get().fetchRiskStatus();
      get().fetchAIStatus();

      return true;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({
        backendAvailable: false,
        scanLog: log(s, `Start failed: ${msg}`),
      }));
      return false;
    }
  },

  // ── Connect (legacy MT5 via Python backend) ──────────────────────────────────────────────
  connect: async (broker, login, password, server) => {
    const state = get();
    set((s) => ({ scanLog: log(s, `Connecting to ${broker}...`) }));

    try {
      const res = await tradingApi.connect({
        broker: broker.toLowerCase(),
        account_type: "paper",
        login,
        password,
        server: server || undefined,
      });

      if (!res.success) {
        set((s) => ({ scanLog: log(s, `Connection FAILED: ${JSON.stringify(res)}`) }));
        return false;
      }

      const account: AccountInfo = {
        balance: res.account.balance,
        equity: res.account.equity,
        margin: res.account.margin || 0,
        free_margin: res.account.free_margin,
        leverage: res.account.leverage,
        profit: 0,
        margin_level: res.account.margin_level,
      };

      const conn: ConnectionState = {
        connected: true,
        sessionId: res.session_id,
        broker: res.broker,
        server: res.server,
        account,
        lastUpdate: new Date().toISOString(),
        mode: "paper",
        selectedBrokerId: null,
        mt5Server: null,
        webTerminalUrl: null,
      };

      set({
        connection: conn,
        backendAvailable: true,
        positions: [],
        scanResults: [],
        riskSummary: EMPTY_RISK,
        scanLog: log(
          { ...get(), connection: conn },
          `Connected to ${res.broker} (${res.server}). Balance: $${account.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        ),
      });

      get().fetchAccount();
      get().fetchRiskStatus();
      get().fetchAIStatus();

      return true;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({
        backendAvailable: false,
        scanLog: log(s, `Connection error: ${msg}`),
      }));
      return false;
    }
  },

  // ── Confirm / Unconfirm MT5 Connection (live mode) ─────────────────────
  confirmMT5Connection: (balance?: string, equity?: string) => {
    set((s) => ({
      liveState: {
        mt5Confirmed: true,
        manualBalance: balance || "",
        manualEquity: equity || "",
        connectedAt: new Date().toISOString(),
      },
      scanLog: log(s, "✅ MT5 connection confirmed. AI auto-trading now available."),
    }));
  },

  unconfirmMT5Connection: () => {
    set((s) => ({
      liveState: {
        mt5Confirmed: false,
        manualBalance: "",
        manualEquity: "",
        connectedAt: null,
      },
      autoTrade: { ...s.autoTrade, enabled: false },
      scanLog: log(s, "MT5 connection unconfirmed. Auto-trading paused."),
    }));
  },

  // ── Disconnect ────────────────────────────────────────────────────
  disconnect: async () => {
    const state = get();
    const wasLive = state.connection.mode === "live";

    if (state.connection.sessionId && !wasLive) {
      try {
        await tradingApi.disconnect(state.connection.sessionId);
      } catch {
        // ignore disconnect errors
      }
    }

    set({
      connection: { ...EMPTY_CONNECTION },
      liveState: {
        mt5Confirmed: false,
        manualBalance: "",
        manualEquity: "",
        connectedAt: null,
      },
      positions: [],
      pendingOrders: [],
      scanResults: [],
      riskSummary: EMPTY_RISK,
      autoTrade: { enabled: false, intervalMinutes: 15, symbols: ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD"], lastScan: null, cycleCount: 0 },
      scanLog: log(state, "Disconnected."),
    });
  },

  // ── Fetch Account (real data from trading engine, paper mode only) ─────────────────────────────────────────────
  fetchAccount: async () => {
    const state = get();
    if (!state.connection.sessionId || state.connection.mode === "live") return;

    set({ fetchingAccount: true });
    try {
      const data = await tradingApi.getAccount(state.connection.sessionId);
      const account: AccountInfo = {
        balance: data.balance as number,
        equity: data.equity as number,
        margin: data.margin as number,
        free_margin: data.free_margin as number,
        leverage: data.leverage as number,
        profit: data.profit as number,
        margin_level: data.margin_level as number,
      };

      const rawPositions = (data.positions as Record<string, unknown>[]) || [];
      const rawOrders = (data.orders as Record<string, unknown>[]) || [];

      set({
        connection: {
          ...state.connection,
          account,
          lastUpdate: new Date().toISOString(),
        },
        positions: rawPositions.map(parsePosition),
        pendingOrders: rawOrders.map(parsePosition),
        backendAvailable: true,
      });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      if (!msg.includes("502") && !msg.includes("fetch")) {
        set((s) => ({ scanLog: log(s, `Account fetch error: ${msg}`) }));
      }
    } finally {
      set({ fetchingAccount: false });
    }
  },

  // ── Fetch Risk Status (real data) ──────────────────────────────────────────────────────
  fetchRiskStatus: async () => {
    const state = get();
    if (!state.connection.sessionId || state.connection.mode === "live") return;

    try {
      const data = await tradingApi.getRiskStatus(state.connection.sessionId);
      const risk: DailyRiskSummary = {
        date: (data.date as string) || new Date().toISOString().split("T")[0],
        realized_pnl: (data.realized_pnl as number) || 0,
        trades_count: (data.trades_count as number) || 0,
        consecutive_losses: (data.consecutive_losses as number) || 0,
        remaining_trades: (data.remaining_trades as number) || 0,
        remaining_loss_limit: (data.remaining_loss_limit as number) || 0,
      };
      set({ riskSummary: risk });
    } catch {
      // Silent fail for risk polling
    }
  },

  // ── Fetch AI Status (real config from backend) ───────────────────────────────────────────────────
  fetchAIStatus: async () => {
    try {
      const data = await tradingApi.getAIStatus();
      set({
        aiStatus: {
          strategy: (data.strategy as string) || "—",
          patterns: (data.patterns as string[]) || [],
          structure_analysis: (data.structure_analysis as string[]) || [],
          mtf_timeframes: (data.mtf_timeframes as string[]) || [],
          symbols_focus: (data.symbols_focus as string[]) || [],
          brokers: (data.brokers as string[]) || [],
          confidence_threshold: (data.confidence_threshold as number) || 0,
          high_confidence: (data.high_confidence as number) || 0,
          risk_per_trade: (data.risk_per_trade as number) || 0,
          max_daily_loss_pct: (data.max_daily_loss_pct as number) || 0,
          max_consecutive_losses: (data.max_consecutive_losses as number) || 0,
          max_open_positions: (data.max_open_positions as number) || 0,
          max_trades_per_day: (data.max_trades_per_day as number) || 0,
          max_spread_points: (data.max_spread_points as number) || 0,
          min_risk_reward: (data.min_risk_reward as number) || 0,
          mode: "live",
          trailing_stop: (data.trailing_stop as boolean) || false,
        },
      });
    } catch {
      // Silent fail
    }
  },

  // ── Scan Markets (real analysis from backend) ─────────────────────────────────────────────
  scanMarkets: async (symbols) => {
    const state = get();
    // Use the analysis session ID (works for both paper and live modes)
    const sessionId = state.connection.analysisSessionId || state.connection.sessionId;
    if (!sessionId) return;

    set({ scanning: true });
    set((s) => ({ scanLog: log(s, `Scanning ${symbols?.join(", ") || "all symbols"}...`) }));

    try {
      const data = await tradingApi.scan(
        sessionId,
        { symbols }
      );
      const rawResults = (data.results as Record<string, unknown>[]) || [];

      const results: ScanResult[] = rawResults.map((r) => {
        const actionable = r.actionable_signal
          ? {
              symbol: (r.actionable_signal as Record<string, unknown>).symbol as string,
              direction: (r.actionable_signal as Record<string, unknown>).direction as "BUY" | "SELL" | "NO_TRADE",
              entry: (r.actionable_signal as Record<string, unknown>).entry as number,
              sl: (r.actionable_signal as Record<string, unknown>).sl as number,
              tp: (r.actionable_signal as Record<string, unknown>).tp as number,
              volume: (r.actionable_signal as Record<string, unknown>).volume as number,
              confidence: (r.actionable_signal as Record<string, unknown>).confidence as number,
              risk_reward: (r.actionable_signal as Record<string, unknown>).risk_reward as number,
              confirmation_factors: ((r.actionable_signal as Record<string, unknown>).confirmation_factors as string[]) || [],
              confluence: ((r.actionable_signal as Record<string, unknown>).confluence as ScanResult["confluence"]) || null,
            }
          : null;

        return {
          symbol: r.symbol as string,
          confluence: (r.confluence as ScanResult["confluence"]) || null,
          decisions_count: (r.decisions_count as number) || 0,
          actionable,
          errors: (r.errors as string[]) || [],
          risk_failures: (r.risk_failures as string[]) || undefined,
          timeframes: (r.timeframes as ScanResult["timeframes"]) || {},
        };
      });

      const actionableCount = results.filter((r) => r.actionable).length;
      const noTradeCount = results.length - actionableCount;

      set((s) => ({
        scanResults: results,
        scanning: false,
        autoTrade: { ...s.autoTrade, lastScan: new Date().toISOString(), cycleCount: s.autoTrade.cycleCount + 1 },
        scanLog: [
          ...log(s, `Scan complete: ${actionableCount} actionable, ${noTradeCount} NO TRADE`),
          ...results.flatMap((r) => {
            const msgs: string[] = [];
            if (r.actionable) {
              msgs.push(`${r.symbol}: ACTIONABLE ${r.actionable.direction} conf=${r.actionable.confidence.toFixed(2)} R:R=${r.actionable.risk_reward.toFixed(1)}`);
            } else if (r.risk_failures?.length) {
              msgs.push(`${r.symbol}: Signal rejected → ${r.risk_failures[0]}`);
            } else if (r.errors?.length) {
              msgs.push(`${r.symbol}: Error → ${r.errors[0]}`);
            } else {
              msgs.push(`${r.symbol}: NO TRADE`);
            }
            return msgs;
          }),
        ],
      }));

      get().fetchRiskStatus();
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({
        scanning: false,
        scanLog: log(s, `Scan error: ${msg}`),
      }));
    }
  },

  // ── Auto Trade ──────────────────────────────────────────────────────
  toggleAutoTrade: async (enabled, interval) => {
    const state = get();
    const intervalMin = interval ?? state.autoTrade.intervalMinutes;
    set((s) => ({
      autoTrade: { ...s.autoTrade, enabled, intervalMinutes: intervalMin },
      scanLog: log(s, `Auto-trade ${enabled ? "ENABLED" : "DISABLED"} (interval: ${intervalMin}min)`),
    }));

    // In live mode, scanning is client-driven — no backend toggle needed
    if (state.connection.mode === "live") return;

    const sessionId = state.connection.analysisSessionId || state.connection.sessionId;
    if (!sessionId) return;

    try {
      await tradingApi.toggleAutoTrade(sessionId, enabled, intervalMin);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({ scanLog: log(s, `Auto-trade error: ${msg}`) }));
    }
  },

  // ── Close Position (paper mode only — live trades are in the web terminal) ─────────────────
  closePosition: async (ticket: number) => {
    const state = get();
    if (!state.connection.sessionId || state.connection.mode === "live") return;

    const pos = state.positions.find((p) => p.ticket === ticket);
    set((s) => ({ scanLog: log(s, `Closing position #${ticket}...`) }));

    try {
      await tradingApi.closePosition(state.connection.sessionId, ticket);
      set((s) => ({
        positions: s.positions.filter((p) => p.ticket !== ticket),
        scanLog: log(
          { ...get(), positions: s.positions.filter((p) => p.ticket !== ticket) },
          `Closed #${ticket} (${pos?.symbol} ${pos?.type}) P&L: $${pos?.profit?.toFixed(2) || "0.00"}`
        ),
      }));
      get().fetchAccount();
      get().fetchRiskStatus();
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({ scanLog: log(s, `Close failed #${ticket}: ${msg}`) }));
    }
  },
}));
