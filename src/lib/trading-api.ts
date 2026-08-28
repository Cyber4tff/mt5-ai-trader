/*
 * API client for the Cloud Trading Engine.
 * All requests go through Next.js API routes which proxy
 * to the Python FastAPI server on port 8001.
 */

const API_BASE = "/api/trading";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export interface ConnectParams {
  broker?: string;
  account_type?: string;
  login?: number;
  password?: string;
  server?: string;
  balance?: number;
  leverage?: number;
}

export interface ConnectResponse {
  success: boolean;
  session_id: string;
  broker: string;
  server: string;
  mode: string;
  account: {
    balance: number;
    equity: number;
    margin: number;
    free_margin: number;
    leverage: number;
    profit: number;
    margin_level: number;
  };
}

export interface MT5AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  leverage: number;
  profit: number;
  margin_level: number;
  login: number;
  name: string;
  server: string;
  currency: string;
}

export interface MT5ConnectResponse {
  success: boolean;
  mt5_available: boolean;
  account?: MT5AccountInfo;
  error?: string;
  error_code?: number;
}

export interface MT5AccountResponse {
  success: boolean;
  account?: MT5AccountInfo;
  error?: string;
}

export interface MT5TradeResponse {
  success: boolean;
  mt5_available?: boolean;
  deal?: number;
  order?: number;
  price?: number;
  volume?: number;
  comment?: string;
  error?: string;
  retcode?: number;
  position?: {
    ticket: number;
    symbol: string;
    type: string;
    volume: number;
    open_price: number;
    current_price: number;
    sl: number;
    tp: number;
    profit: number;
    swap: number;
    comment: string;
    time: string;
  };
}

export interface MT5CloseResponse {
  success: boolean;
  deal?: number;
  order?: number;
  price?: number;
  profit?: number;
  error?: string;
  retcode?: number;
}

export const tradingApi = {
  // ── Connection ──────────────────────────────────────────
  connect(data: ConnectParams) {
    return apiFetch<ConnectResponse>("/connect", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  disconnect(sessionId: string) {
    return apiFetch<{ success: boolean }>(`/disconnect/${sessionId}`, { method: "POST" });
  },

  // ── Account ────────────────────────────────────────────
  getAccount(sessionId: string) {
    return apiFetch<Record<string, unknown>>(`/account/${sessionId}`);
  },

  getPositions(sessionId: string) {
    return apiFetch<{ positions: Record<string, unknown>[]; orders: Record<string, unknown>[] }>(`/positions/${sessionId}`);
  },

  // ── MT5 Real Connect / Trade ──────────────────────────────────────────
  mt5Connect: (login: number, password: string, server: string) =>
    apiFetch<MT5ConnectResponse>("/mt5-connect", {
      method: "POST",
      body: JSON.stringify({ login, password, server }),
    }),

  mt5Account: () => apiFetch<MT5AccountResponse>("/mt5-account"),

  mt5Positions: () => apiFetch<{ success: boolean; positions: Array<{ ticket: number; symbol: string; type: string; volume: number; open_price: number; current_price: number; sl: number; tp: number; profit: number; swap: number; comment: string; time: string }>; error?: string }>("/mt5-positions"),

  mt5Trade: (params: { symbol: string; direction: string; volume: number; sl: number; tp: number; comment?: string }) =>
    apiFetch<MT5TradeResponse>("/mt5-trade", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  mt5ClosePosition: (ticket: number) =>
    apiFetch<{ success: boolean; deal?: number; order?: number; price?: number; profit?: number; error?: string }>("/mt5-close-position", {
      method: "POST",
      body: JSON.stringify({ ticket }),
    }),

  mt5Status: () => apiFetch<{ mt5_available: boolean; connected: boolean; account_login?: number; server?: string }>("/mt5-status"),

  // ── Deriv Broker WebSocket API ──────────────────────────────────────────
  derivConnect: (api_token: string) =>
    apiFetch<{ success: boolean; account?: { login?: string; email?: string; currency?: string; balance?: number; account_type?: string }; error?: string }>("/deriv-connect", {
      method: "POST",
      body: JSON.stringify({ api_token }),
    }),

  derivAccount: () =>
    apiFetch<{ success: boolean; balance?: number; currency?: string; error?: string }>("/deriv-account"),

  derivStatus: () =>
    apiFetch<{ connected: boolean; account?: { login?: string; balance?: number; currency?: string; account_type?: string } }>("/deriv-status"),

  derivTrade: (params: { symbol: string; direction: string; amount: number; duration?: number; duration_unit?: string }) =>
    apiFetch<{ success: boolean; contract_id?: number; symbol?: string; direction?: string; amount?: number; error?: string }>("/deriv-trade", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  // ── Scanning ────────────────────────────────────────────
  scan(sessionId: string, data?: { symbols?: string[]; entry_timeframe?: string }) {
    return apiFetch<{ results: Record<string, unknown>[] }>(`/scan/${sessionId}`, {
      method: "POST",
      body: JSON.stringify(data || {}),
    });
  },

  // ── Trading ─────────────────────────────────────────────
  closePosition(sessionId: string, ticket: number) {
    return apiFetch<{ success: boolean }>(`/close/${sessionId}/${ticket}`, { method: "POST" });
  },

  // ── Auto Trade ──────────────────────────────────────────
  toggleAutoTrade(sessionId: string, enabled: boolean, intervalMinutes: number = 15) {
    return apiFetch<{ success: boolean; auto_trade: boolean }>(`/auto-trade/${sessionId}`, {
      method: "POST",
      body: JSON.stringify({ enabled, interval_minutes: intervalMinutes }),
    });
  },

  // ── Risk & Status ───────────────────────────────────────
  getRiskStatus(sessionId: string) {
    return apiFetch<Record<string, unknown>>(`/risk-status/${sessionId}`);
  },

  getAIStatus() {
    return apiFetch<Record<string, unknown>>("/ai-status");
  },

  // ── Symbols & Health ───────────────────────────────────
  getSymbols() {
    return apiFetch<{ symbols: { name: string; price: number }[] }>('/symbols');
  },

  getHealth() {
    return apiFetch<{ status: string; engine: string; version: string }>('/health');
  },
};
