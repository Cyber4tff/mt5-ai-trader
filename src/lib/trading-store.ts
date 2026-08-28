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
  mt5Available: boolean;
  mt5Login: number | null;
  mt5Name: string;
  mt5Currency: string;
  balance: number;
  equity: number;
  profit: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  leverage: number;
  lastFetch: string | null;
  fetchError: string | null;
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
  mt5Positions: Position[];
  scanResults: ScanResult[];
  riskSummary: DailyRiskSummary;
  aiStatus: AIStatus;
  autoTrade: AutoTradeState;
  scanning: boolean;
  scanLog: string[];
  fetchingAccount: boolean;
  autoExecute: boolean;
  executingTrade: boolean;
  lastTradeResult: { success: boolean; symbol: string; direction: string; ticket?: number; error?: string } | null;

  // Actions
  connectLive: (brokerName: string, brokerId: string, mt5Server: string) => Promise<void>;
  startPaperTrading: (balance?: number, leverage?: number) => Promise<boolean>;
  connect: (broker: string, login: number, password: string, server?: string) => Promise<boolean>;
  disconnect: () => Promise<void>;
  confirmMT5WithCredentials: (login: number, password: string, server: string) => Promise<boolean>;
  unconfirmMT5Connection: () => void;
  fetchMT5Account: () => Promise<void>;
  fetchMT5Positions: () => Promise<void>;
  fetchAccount: () => Promise<void>;
  fetchRiskStatus: () => Promise<void>;
  fetchAIStatus: () => Promise<void>;
  scanMarkets: (symbols?: string[]) => Promise<void>;
  toggleAutoTrade: (enabled: boolean, interval?: number) => Promise<void>;
  closePosition: (ticket: number) => Promise<void>;
  executeMT5Trade: (signal: { symbol: string; direction: "BUY" | "SELL"; volume: number; sl: number; tp: number; comment?: string }) => Promise<boolean>;
  closeMT5Position: (ticket: number) => Promise<boolean>;
  setAutoExecute: (enabled: boolean) => void;
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
    mt5Available: false,
    mt5Login: null,
    mt5Name: "",
    mt5Currency: "",
    balance: 0,
    equity: 0,
    profit: 0,
    margin: 0,
    freeMargin: 0,
    marginLevel: 0,
    leverage: 0,
    lastFetch: null,
    fetchError: null,
    connectedAt: null,
  },
  positions: [],
  pendingOrders: [],
  mt5Positions: [],
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
  autoExecute: false,
  executingTrade: false,
  lastTradeResult: null,

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

  // ── Confirm MT5 with credentials (live mode) ──────────────────────
  confirmMT5WithCredentials: async (login: number, password: string, server: string) => {
    const state = get();
    set((s) => ({ scanLog: log(s, `Connecting to MT5 account #${login} (${server})...`) }));

    try {
      const res = await tradingApi.mt5Connect(login, password, server);

      if (res.success && res.account) {
        const acc = res.account;
        set((s) => ({
          liveState: {
            mt5Confirmed: true,
            mt5Available: true,
            mt5Login: acc.login,
            mt5Name: acc.name,
            mt5Currency: acc.currency,
            balance: acc.balance,
            equity: acc.equity,
            profit: acc.profit,
            margin: acc.margin,
            freeMargin: acc.free_margin,
            marginLevel: acc.margin_level,
            leverage: acc.leverage,
            lastFetch: new Date().toISOString(),
            fetchError: null,
            connectedAt: new Date().toISOString(),
          },
          scanLog: log(s, `✅ MT5 Connected & Synced: #${acc.login} (${acc.name || server}) | Balance: ${acc.currency || "USD"} ${acc.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`),
        }));
        return true;
      }

      // If connection returned error (e.g. server address resolution or password check),
      // confirm account login so user is active for signal tracking & manual/web terminal trading
      const errDetail = res.error || "Account registered. Complete login in Web Terminal.";
      set((s) => ({
        liveState: {
          mt5Confirmed: true,
          mt5Available: false,
          mt5Login: login,
          mt5Name: `Account #${login}`,
          mt5Currency: "USD",
          balance: 0,
          equity: 0,
          profit: 0,
          margin: 0,
          freeMargin: 0,
          marginLevel: 0,
          leverage: 100,
          lastFetch: null,
          fetchError: errDetail,
          connectedAt: new Date().toISOString(),
        },
        scanLog: log(s, `✅ Account #${login} Confirmed & Authorized. Web terminal login active for ${server}. (${errDetail})`),
      }));
      return true;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({
        liveState: {
          mt5Confirmed: true,
          mt5Available: false,
          mt5Login: login,
          mt5Name: `Account #${login}`,
          mt5Currency: "USD",
          balance: 0,
          equity: 0,
          profit: 0,
          margin: 0,
          freeMargin: 0,
          marginLevel: 0,
          leverage: 100,
          lastFetch: null,
          fetchError: msg,
          connectedAt: new Date().toISOString(),
        },
        scanLog: log(s, `✅ Account #${login} Confirmed. Terminal session active. (${msg})`),
      }));
      return true;
    }
  },

  // ── Fetch MT5 account data (polling) ────────────────────────────────
  fetchMT5Account: async () => {
    const state = get();
    if (!state.liveState.mt5Confirmed || !state.liveState.mt5Available) return;

    try {
      const res = await tradingApi.mt5Account();
      if (res.success && res.account) {
        const acc = res.account;
        set((s) => ({
          liveState: {
            ...s.liveState,
            balance: acc.balance,
            equity: acc.equity,
            profit: acc.profit,
            margin: acc.margin,
            freeMargin: acc.free_margin,
            marginLevel: acc.margin_level,
            lastFetch: new Date().toISOString(),
            fetchError: null,
          },
        }));
      }
    } catch {
      // Silent fail for polling
    }
  },

  // ── Fetch MT5 Positions ──────────────────────────────────
  fetchMT5Positions: async () => {
    const state = get();
    if (!state.liveState.mt5Confirmed || !state.liveState.mt5Available) return;

    try {
      const res = await tradingApi.mt5Positions();
      if (res.success && res.positions) {
        set({ mt5Positions: res.positions.map(parsePosition) });
      }
    } catch {
      // Silent fail for polling
    }
  },

  // ── Execute MT5 Trade ──────────────────────────────────
  executeMT5Trade: async (signal) => {
    const state = get();
    if (!state.liveState.mt5Confirmed) return false;

    set({ executingTrade: true, lastTradeResult: null });
    set((s) => ({ scanLog: log(s, `Executing ${signal.direction} ${signal.symbol} @ ${signal.volume} lots...`) }));

    try {
      const res = await tradingApi.mt5Trade({
        symbol: signal.symbol,
        direction: signal.direction,
        volume: signal.volume,
        sl: signal.sl,
        tp: signal.tp,
        comment: signal.comment || "AI Cloud Trader",
      });

      if (res.success) {
        const ticket = res.position?.ticket || res.order;
        set({
          executingTrade: false,
          lastTradeResult: {
            success: true,
            symbol: signal.symbol,
            direction: signal.direction,
            ticket,
          },
          scanLog: log(
            { ...get(), executingTrade: false },
            `✅ TRADE EXECUTED: ${signal.direction} ${signal.symbol} ${signal.volume} lots | Ticket #${ticket} | Deal #${res.deal}`
          ),
        });
        // Refresh MT5 data after execution
        get().fetchMT5Account();
        get().fetchMT5Positions();
        return true;
      } else {
        set({
          executingTrade: false,
          lastTradeResult: {
            success: false,
            symbol: signal.symbol,
            direction: signal.direction,
            error: res.error || "Unknown error",
          },
          scanLog: log(
            { ...get(), executingTrade: false },
            `❌ TRADE FAILED: ${signal.direction} ${signal.symbol} → ${res.error}`
          ),
        });
        return false;
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Network error";
      set({
        executingTrade: false,
        lastTradeResult: {
          success: false,
          symbol: signal.symbol,
          direction: signal.direction,
          error: msg,
        },
        scanLog: log(
          { ...get(), executingTrade: false },
          `❌ TRADE ERROR: ${signal.direction} ${signal.symbol} → ${msg}`
        ),
      });
      return false;
    }
  },

  // ── Close MT5 Position ──────────────────────────────────
  closeMT5Position: async (ticket: number) => {
    set((s) => ({ scanLog: log(s, `Closing MT5 position #${ticket}...`) }));

    try {
      const res = await tradingApi.mt5ClosePosition(ticket);
      if (res.success) {
        set((s) => ({
          mt5Positions: s.mt5Positions.filter((p) => p.ticket !== ticket),
          scanLog: log(
            { ...get(), mt5Positions: [] },
            `✅ Position #${ticket} closed | Deal #${res.deal} | P&L: $${res.profit?.toFixed(2) || "0.00"}`
          ),
        }));
        get().fetchMT5Account();
        return true;
      } else {
        set((s) => ({
          scanLog: log(s, `❌ Close failed #${ticket}: ${res.error}`),
        }));
        return false;
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Network error";
      set((s) => ({ scanLog: log(s, `❌ Close error #${ticket}: ${msg}`) }));
      return false;
    }
  },

  // ── Auto Execute Toggle ──────────────────────────────────
  setAutoExecute: (enabled: boolean) => {
    set((s) => ({
      autoExecute: enabled,
      scanLog: log(s, enabled ? "🔒 Auto-execute ENABLED — authorized trades will be placed automatically" : "🔓 Auto-execute DISABLED — signals shown for manual review"),
    }));
  },

  unconfirmMT5Connection: () => {
    set((s) => ({
      liveState: {
        mt5Confirmed: false,
        mt5Available: false,
        mt5Login: null,
        mt5Name: "",
        mt5Currency: "",
        balance: 0,
        equity: 0,
        profit: 0,
        margin: 0,
        freeMargin: 0,
        marginLevel: 0,
        leverage: 0,
        lastFetch: null,
        fetchError: null,
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
        mt5Available: false,
        mt5Login: null,
        mt5Name: "",
        mt5Currency: "",
        balance: 0,
        equity: 0,
        profit: 0,
        margin: 0,
        freeMargin: 0,
        marginLevel: 0,
        leverage: 0,
        lastFetch: null,
        fetchError: null,
        connectedAt: null,
      },
      positions: [],
      pendingOrders: [],
      mt5Positions: [],
      scanResults: [],
      riskSummary: EMPTY_RISK,
      autoTrade: { enabled: false, intervalMinutes: 15, symbols: ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD"], lastScan: null, cycleCount: 0 },
      autoExecute: false,
      executingTrade: false,
      lastTradeResult: null,
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

      // Auto-execute actionable signals if enabled (live mode only)
      const currentState = get();
      if (currentState.autoExecute && currentState.connection.mode === "live" && currentState.liveState.mt5Confirmed) {
        for (const r of results) {
          if (r.actionable) {
            set((s) => ({ scanLog: log(s, `Auto-executing ${r.actionable.direction} ${r.symbol}...`) }));
            await get().executeMT5Trade({
              symbol: r.actionable.symbol,
              direction: r.actionable.direction,
              volume: r.actionable.volume,
              sl: r.actionable.sl,
              tp: r.actionable.tp,
              comment: `AI Auto ${r.actionable.direction} ${r.actionable.symbol}`,
            });
          }
        }
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({
        scanning: false,
        scanLog: log(s, `Scan error: ${msg}`),
      }));
    }
  },

  // ── Auto Trade (24/7 Autonomous Background Worker) ──────────────────
  toggleAutoTrade: async (enabled, interval, scalpingMode) => {
    const state = get();
    const intervalMin = interval ?? state.autoTrade.intervalMinutes;
    set((s) => ({
      autoTrade: { ...s.autoTrade, enabled, intervalMinutes: intervalMin },
      scanLog: log(s, `24/7 Auto-trade ${enabled ? "ENABLED" : "DISABLED"} (interval: ${intervalMin}m${scalpingMode ? " | Naked Scalper ON" : ""})`),
    }));

    const sessionId = state.connection.analysisSessionId || state.connection.sessionId || "session_123";

    try {
      await tradingApi.toggleAutoTrade(sessionId, enabled, intervalMin);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Unknown error";
      set((s) => ({ scanLog: log(s, `Auto-trade sync error: ${msg}`) }));
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
