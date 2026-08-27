export type SignalDirection = "BUY" | "SELL" | "NO_TRADE";
export type MarketBias = "bullish" | "bearish" | "neutral";
export type TrendDirection = "UP" | "DOWN" | "RANGING";
export type VolatilityRegime = "high" | "normal" | "low";
export type TradingMode = "demo" | "live";
export type SessionMode = "paper" | "live";

export interface BrokerConfig {
  id: string;
  name: string;
  logo: string;
  servers: string[];
  webTerminalUrl: string;
}

export const BROKERS: BrokerConfig[] = [
  {
    id: "octafx",
    name: "OctaFX",
    logo: "O",
    servers: [
      "OctaFX-MT5-Real",
      "OctaFX-MT5-Real2",
      "OctaFX-MT5-Real3",
      "OctaFX-MT5-Real4",
      "OctaFX-MT5-Real5",
      "OctaFX-MT5-Demo",
    ],
    webTerminalUrl: "https://trade.mql5.com/trade",
  },
  {
    id: "exness",
    name: "Exness",
    logo: "E",
    servers: [
      "Exness-MT5Real",
      "Exness-MT5Real2",
      "Exness-MT5Real3",
      "Exness-MT5Real4",
      "Exness-MT5Real5",
      "Exness-MT5Real6",
      "Exness-MT5Real7",
      "Exness-MT5Real8",
      "Exness-MT5Real9",
      "Exness-MT5Demo",
    ],
    webTerminalUrl: "https://trade.mql5.com/trade",
  },
  {
    id: "headway",
    name: "Headway",
    logo: "H",
    servers: [
      "Headway-Demo",
      "Headway-Real",
      "Headway-Live",
    ],
    webTerminalUrl: "https://trade.mql5.com/trade",
  },
  {
    id: "custom",
    name: "Custom Broker",
    logo: "C",
    servers: [],
    webTerminalUrl: "https://trade.mql5.com/trade",
  },
];

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  leverage: number;
  profit: number;
  margin_level: number;
}

export interface Position {
  ticket: number;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  open_price: number;
  current_price: number;
  sl: number;
  tp: number;
  profit: number;
  swap: number;
  comment: string;
  time: string;
}

export interface PendingOrder {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price: number;
  sl: number;
  tp: number;
  comment: string;
}

export interface SRLevel {
  price: number;
  type: "support" | "resistance";
  strength: number;
  touches: number;
  zone_high: number;
  zone_low: number;
}

export interface StructureBreak {
  type: "BOS" | "CHOCH";
  direction: "bullish" | "bearish";
  price: number;
  time: string;
}

export interface TimeframeAnalysis {
  timeframe: string;
  trend: TrendDirection;
  bias: MarketBias;
  atr: number;
  atr_percentile: number;
  volatility: VolatilityRegime;
  structure_breaks: StructureBreak[];
  sr_levels: SRLevel[];
  signals_count: number;
  momentum: string;
}

export interface ConfluenceData {
  direction: string;
  score: number;
  higher_tf_bias: MarketBias;
  trend_alignment: boolean;
  factors: string[];
  bullish_ratio: number;
  bearish_ratio: number;
}

export interface ActionableSignal {
  symbol: string;
  direction: SignalDirection;
  entry: number;
  sl: number;
  tp: number;
  volume: number;
  confidence: number;
  risk_reward: number;
  confirmation_factors: string[];
  confluence: ConfluenceData;
}

export interface ScanResult {
  symbol: string;
  confluence: ConfluenceData | null;
  decisions_count: number;
  actionable: ActionableSignal | null;
  errors: string[];
  risk_failures?: string[];
  timeframes: Record<string, {
    trend: TrendDirection;
    bias: MarketBias;
    atr: number;
    volatility: VolatilityRegime;
    signals_count: number;
    structure_breaks: number;
    sr_levels: number;
  }>;
}

export interface DailyRiskSummary {
  date: string;
  realized_pnl: number;
  trades_count: number;
  consecutive_losses: number;
  remaining_trades: number;
  remaining_loss_limit: number;
}

export interface AIStatus {
  strategy: string;
  patterns: string[];
  structure_analysis: string[];
  mtf_timeframes: string[];
  symbols_focus: string[];
  brokers: string[];
  confidence_threshold: number;
  high_confidence: number;
  risk_per_trade: number;
  max_daily_loss_pct: number;
  max_consecutive_losses: number;
  max_open_positions: number;
  max_trades_per_day: number;
  max_spread_points: number;
  min_risk_reward: number;
  mode: TradingMode;
  trailing_stop: boolean;
}

export interface ConnectionState {
  connected: boolean;
  sessionId: string | null;
  broker: string | null;
  server: string | null;
  account: AccountInfo | null;
  lastUpdate: string | null;
  mode: SessionMode;
  selectedBrokerId: string | null;
  mt5Server: string | null;
}

export interface AutoTradeState {
  enabled: boolean;
  intervalMinutes: number;
  symbols: string[];
  lastScan: string | null;
  cycleCount: number;
}
