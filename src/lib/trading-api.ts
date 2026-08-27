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
