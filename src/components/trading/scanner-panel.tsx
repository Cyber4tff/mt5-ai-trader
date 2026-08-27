'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ScanSearch,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  ArrowUp,
  ArrowDown,
  ArrowRight,
  Zap,
  Loader2,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useTradingStore } from '@/lib/trading-store';
import type { ScanResult, TrendDirection, MarketBias } from '@/lib/trading-types';

const TF_ORDER = ['D1', 'H1', 'M15'];

function TrendArrow({ trend }: { trend: TrendDirection }) {
  if (trend === 'UP') return <ArrowUp className="size-3.5 text-emerald-500" />;
  if (trend === 'DOWN') return <ArrowDown className="size-3.5 text-red-500" />;
  return <ArrowRight className="size-3.5 text-muted-foreground" />;
}

function biasBorderClass(bias: MarketBias) {
  if (bias === 'bullish') return 'border-emerald-500/50';
  if (bias === 'bearish') return 'border-red-500/50';
  return 'border-border';
}

function biasBgClass(bias: MarketBias) {
  if (bias === 'bullish') return 'bg-emerald-500/5';
  if (bias === 'bearish') return 'bg-red-500/5';
  return 'bg-card';
}

function isHigherTf(tf: string) {
  return tf === 'D1' || tf === 'H4';
}

function TFPill({
  tf,
  trend,
  bias,
  atr,
}: {
  tf: string;
  trend: TrendDirection;
  bias: MarketBias;
  atr: number;
}) {
  const higher = isHigherTf(tf);
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex flex-col items-center gap-1 rounded-md border p-2 transition-colors',
        biasBorderClass(bias),
        biasBgClass(bias),
        higher ? 'min-w-[72px]' : 'min-w-[56px]'
      )}
    >
      <span
        className={cn(
          'font-bold tabular-nums leading-none',
          higher ? 'text-xs' : 'text-[10px]'
        )}
      >
        {tf}
      </span>
      <TrendArrow trend={trend} />
      <span
        className={cn(
          'text-[9px] uppercase font-medium tracking-wider',
          bias === 'bullish'
            ? 'text-emerald-500'
            : bias === 'bearish'
              ? 'text-red-500'
              : 'text-muted-foreground'
        )}
      >
        {bias}
      </span>
      <span className="text-[10px] text-muted-foreground tabular-nums">
        ATR {atr.toFixed(atr >= 100 ? 0 : 1)}
      </span>
    </motion.div>
  );
}

function headerBgFromScore(score: number, direction: string) {
  if (!score) return 'bg-card';
  const absScore = Math.abs(score);
  if (direction === 'bullish' || direction === 'BUY') {
    if (absScore >= 0.7) return 'bg-emerald-500/10';
    if (absScore >= 0.5) return 'bg-emerald-500/5';
  }
  if (direction === 'bearish' || direction === 'SELL') {
    if (absScore >= 0.7) return 'bg-red-500/10';
    if (absScore >= 0.5) return 'bg-red-500/5';
  }
  return 'bg-card';
}

interface TradeDialogState {
  open: boolean;
  symbol: string;
  direction: string;
  entry: number;
  sl: number;
  tp: number;
  volume: number;
  confidence: number;
  riskReward: number;
  confirmationFactors: string[];
}

function TradeAuthDialog({
  state,
  onClose,
  onExecute,
  executing,
}: {
  state: TradeDialogState;
  onClose: () => void;
  onExecute: () => void;
  executing: boolean;
}) {
  const isBuy = state.direction === 'BUY';
  const pipRisk = Math.abs(state.entry - state.sl);
  const pipReward = Math.abs(state.tp - state.entry);

  return (
    <Dialog open={state.open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className={cn('size-5', isBuy ? 'text-emerald-500' : 'text-red-500')} />
            Authorize Trade Execution
          </DialogTitle>
          <DialogDescription>
            Review the trade details below and authorize to place this order on your MT5 account.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Signal Header */}
          <div className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            isBuy ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'
          )}>
            <div>
              <p className="text-lg font-bold text-foreground">{state.symbol}</p>
              <p className="text-xs text-muted-foreground">AI Signal</p>
            </div>
            <Badge className={cn(
              'text-sm font-bold px-3 py-1',
              isBuy ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
            )}>
              {state.direction}
            </Badge>
          </div>

          {/* Trade Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2.5 rounded-lg bg-secondary">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Entry Price</p>
              <p className="text-sm font-bold font-mono text-foreground">{state.entry.toFixed(state.entry >= 100 ? 2 : 5)}</p>
            </div>
            <div className="p-2.5 rounded-lg bg-secondary">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Volume</p>
              <p className="text-sm font-bold font-mono text-foreground">{state.volume.toFixed(2)} lots</p>
            </div>
            <div className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/20">
              <p className="text-[10px] text-red-500 uppercase tracking-wider">Stop Loss</p>
              <p className="text-sm font-bold font-mono text-red-500">{state.sl.toFixed(state.sl >= 100 ? 2 : 5)}</p>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
              <p className="text-[10px] text-emerald-500 uppercase tracking-wider">Take Profit</p>
              <p className="text-sm font-bold font-mono text-emerald-500">{state.tp.toFixed(state.tp >= 100 ? 2 : 5)}</p>
            </div>
          </div>

          {/* Risk/Reward & Confidence */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Risk : Reward</p>
              <p className="text-lg font-bold font-mono text-foreground">1 : {state.riskReward.toFixed(1)}</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Confidence</p>
              <p className="text-lg font-bold font-mono text-foreground">{(state.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>

          {state.confirmationFactors.length > 0 && (
            <>
              <Separator />
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Confirmation Factors</p>
                <div className="flex flex-wrap gap-1.5">
                  {state.confirmationFactors.map((f, i) => (
                    <Badge key={i} variant="outline" className="border-emerald-500/20 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 text-[10px]">
                      <Check className="size-2.5 mr-0.5" /> {f}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Warning */}
          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle className="size-4 text-amber-500 mt-0.5 shrink-0" />
            <p className="text-[11px] text-amber-600 dark:text-amber-400 leading-relaxed">
              This will place a real market order on your MT5 account. Make sure your MT5 connection is active and you have sufficient margin.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose} disabled={executing}>
            Cancel
          </Button>
          <Button
            className={cn(
              'flex-1 font-semibold',
              isBuy ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'
            )}
            onClick={onExecute}
            disabled={executing}
          >
            {executing ? (
              <>
                <Loader2 className="size-4 animate-spin mr-2" />
                Executing...
              </>
            ) : (
              <>
                <ShieldCheck className="size-4 mr-2" />
                Authorize & Execute
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TradeResultBanner() {
  const { lastTradeResult } = useTradingStore();

  if (!lastTradeResult) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border',
        lastTradeResult.success
          ? 'bg-emerald-500/10 border-emerald-500/30'
          : 'bg-red-500/10 border-red-500/30'
      )}
    >
      {lastTradeResult.success ? (
        <CheckCircle2 className="size-5 text-emerald-500 shrink-0" />
      ) : (
        <X className="size-5 text-red-500 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className={cn(
          'text-sm font-semibold',
          lastTradeResult.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
        )}>
          {lastTradeResult.success
            ? `Trade Executed — ${lastTradeResult.direction} ${lastTradeResult.symbol}`
            : `Trade Failed — ${lastTradeResult.direction} ${lastTradeResult.symbol}`
          }
        </p>
        {lastTradeResult.success && lastTradeResult.ticket && (
          <p className="text-xs text-muted-foreground">Ticket #{lastTradeResult.ticket}</p>
        )}
        {lastTradeResult.error && (
          <p className="text-xs text-red-500/80 truncate">{lastTradeResult.error}</p>
        )}
      </div>
    </motion.div>
  );
}

function ScanResultCard({ result, index }: { result: ScanResult; index: number }) {
  const [expanded, setExpanded] = useState(index === 0);
  const [tradeDialog, setTradeDialog] = useState<TradeDialogState>({
    open: false, symbol: '', direction: '', entry: 0, sl: 0, tp: 0,
    volume: 0, confidence: 0, riskReward: 0, confirmationFactors: [],
  });
  const { connection, liveState, autoExecute, executingTrade, executeMT5Trade } = useTradingStore();
  const isLiveMode = connection.mode === 'live';
  const mt5Ready = isLiveMode && liveState.mt5Confirmed;

  const toggle = useCallback(() => setExpanded((v) => !v), []);

  const { confluence, actionable, risk_failures, timeframes, symbol } = result;
  const score = confluence?.score ?? 0;
  const direction = confluence?.direction ?? '-';
  const hasActionable = !!actionable;
  const hasFailures = (risk_failures?.length ?? 0) > 0;

  const directionColor =
    direction === 'bullish' || direction === 'BUY'
      ? 'text-emerald-500'
      : direction === 'bearish' || direction === 'SELL'
        ? 'text-red-500'
        : 'text-muted-foreground';

  const directionBadgeClass =
    direction === 'bullish' || direction === 'BUY'
      ? 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
      : direction === 'bearish' || direction === 'SELL'
        ? 'bg-red-500/15 text-red-500 border-red-500/30'
        : 'bg-secondary text-muted-foreground border-border';

  const handleAuthorizeTrade = useCallback(() => {
    if (!actionable) return;
    setTradeDialog({
      open: true,
      symbol: actionable.symbol,
      direction: actionable.direction,
      entry: actionable.entry,
      sl: actionable.sl,
      tp: actionable.tp,
      volume: actionable.volume,
      confidence: actionable.confidence,
      riskReward: actionable.risk_reward,
      confirmationFactors: actionable.confirmation_factors,
    });
  }, [actionable]);

  const handleExecuteTrade = useCallback(async () => {
    if (!actionable) return;
    const success = await executeMT5Trade({
      symbol: actionable.symbol,
      direction: actionable.direction,
      volume: actionable.volume,
      sl: actionable.sl,
      tp: actionable.tp,
      comment: `AI Signal ${actionable.direction} ${actionable.symbol}`,
    });
    setTradeDialog((prev) => ({ ...prev, open: false }));
    if (success) {
      toast.success(`Trade executed`, {
        description: `${actionable.direction} ${actionable.symbol} placed successfully`,
      });
    } else {
      toast.error(`Trade failed`, {
        description: `Check the activity log for details`,
      });
    }
  }, [actionable, executeMT5Trade]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08 }}
      className="rounded-lg border border-border overflow-hidden"
    >
      <button
        onClick={toggle}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/50 text-left',
          headerBgFromScore(score, direction)
        )}
      >
        <span className="text-lg font-bold min-w-[80px] text-foreground">{symbol}</span>

        <Badge variant="outline" className={cn('text-[10px] font-semibold', directionBadgeClass)}>
          {direction.toUpperCase()}
        </Badge>

        {confluence && (
          <span className={cn('text-sm font-mono tabular-nums font-semibold', directionColor)}>
            {(score * 100).toFixed(0)}%
          </span>
        )}

        {hasActionable ? (
          <Badge className="bg-emerald-500/15 text-emerald-500 border-emerald-500/30 text-[10px]">
            <Check className="size-3" /> Actionable
          </Badge>
        ) : (
          <Badge variant="outline" className="border-red-500/30 text-red-500 text-[10px]">
            <X className="size-3" /> No Trade
          </Badge>
        )}

        <div className="ml-auto text-muted-foreground">
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 space-y-3 border-t border-border/50">
              <div>
                <p className="text-[10px] uppercase text-muted-foreground tracking-wider mb-2 font-medium">
                  Multi-Timeframe Analysis
                </p>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {TF_ORDER.map((tf) => {
                    const data = timeframes[tf];
                    if (!data) return null;
                    return (
                      <TFPill key={tf} tf={tf} trend={data.trend} bias={data.bias} atr={data.atr} />
                    );
                  })}
                </div>
              </div>

              {confluence && confluence.factors.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {confluence.factors.map((f, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">
                      {f}
                    </span>
                  ))}
                </div>
              )}

              {hasActionable && actionable && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 space-y-3">
                  <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                    <Zap className="size-3.5" /> Actionable Signal
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block">Direction</span>
                      <span className={cn('font-mono font-bold', actionable.direction === 'BUY' ? 'text-emerald-500' : 'text-red-500')}>
                        {actionable.direction}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Entry</span>
                      <span className="font-mono tabular-nums text-foreground">{actionable.entry.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">SL</span>
                      <span className="font-mono tabular-nums text-red-500">{actionable.sl.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">TP</span>
                      <span className="font-mono tabular-nums text-emerald-500">{actionable.tp.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Volume</span>
                      <span className="font-mono tabular-nums text-foreground">{actionable.volume.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">R:R</span>
                      <span className="font-mono tabular-nums font-semibold text-foreground">{actionable.risk_reward.toFixed(2)}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-muted-foreground block mb-1">Confidence</span>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                          <motion.div
                            className={cn(
                              'h-full rounded-full',
                              actionable.confidence >= 0.8 ? 'bg-emerald-500' : actionable.confidence >= 0.65 ? 'bg-amber-500' : 'bg-red-500'
                            )}
                            initial={{ width: 0 }}
                            animate={{ width: `${actionable.confidence * 100}%` }}
                            transition={{ duration: 0.6, ease: 'easeOut' }}
                          />
                        </div>
                        <span className="font-mono text-xs tabular-nums font-semibold text-foreground">
                          {(actionable.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {actionable.confirmation_factors.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {actionable.confirmation_factors.map((f, i) => (
                        <Badge key={i} variant="outline" className="border-emerald-500/20 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 text-[10px]">
                          {f}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Trade Execution Button */}
                  {mt5Ready ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className={cn(
                          'flex-1 font-semibold',
                          actionable.direction === 'BUY'
                            ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                            : 'bg-red-600 hover:bg-red-700 text-white'
                        )}
                        onClick={handleAuthorizeTrade}
                        disabled={executingTrade}
                      >
                        {executingTrade ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <ShieldCheck className="size-3" />
                        )}
                        Authorize & Execute Trade
                      </Button>
                      {autoExecute && (
                        <Badge className="bg-emerald-500/15 text-emerald-500 border-emerald-500/30 text-[10px] self-center whitespace-nowrap">
                          <Zap className="size-2.5" /> AUTO
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <p className="text-[10px] text-muted-foreground">
                        {isLiveMode
                          ? 'Connect your MT5 account to enable trade execution.'
                          : 'Switch to Live Trading mode to execute trades.'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {!hasActionable && hasFailures && risk_failures && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
                  <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">Signal Rejected</p>
                  <div className="flex flex-wrap gap-1.5">
                    {risk_failures.map((f, i) => (
                      <Badge key={i} variant="outline" className="border-red-500/30 text-red-500 bg-red-500/5 text-[10px]">
                        <X className="size-3" /> {f}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {!hasActionable && !hasFailures && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-border text-muted-foreground text-[10px]">
                    NO TRADE
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Insufficient confluence or no valid signal detected.
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Trade Authorization Dialog */}
      <TradeAuthDialog
        state={tradeDialog}
        onClose={() => setTradeDialog((prev) => ({ ...prev, open: false }))}
        onExecute={handleExecuteTrade}
        executing={executingTrade}
      />
    </motion.div>
  );
}

export function ScannerPanel() {
  const scanResults = useTradingStore((s) => s.scanResults);
  const scanning = useTradingStore((s) => s.scanning);
  const autoTrade = useTradingStore((s) => s.autoTrade);
  const scanMarkets = useTradingStore((s) => s.scanMarkets);

  const handleScan = useCallback(async () => {
    await scanMarkets(autoTrade.symbols);
    toast.success('Scan complete', {
      description: `Scanned ${autoTrade.symbols.length} symbols`,
    });
  }, [scanMarkets, autoTrade.symbols]);

  return (
    <Card className="bg-card border-border gap-4">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-base text-foreground">
          <ScanSearch className="size-4 text-purple-500" />
          Multi-Timeframe Scanner
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Trade Result Banner */}
        <TradeResultBanner />

        <div className="flex items-center gap-3 flex-wrap">
          <Button size="sm" onClick={handleScan} disabled={scanning}>
            {scanning ? <RefreshCw className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            {scanning ? 'Scanning...' : 'Scan Markets'}
          </Button>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] uppercase text-muted-foreground tracking-wider mr-1">
              Watching:
            </span>
            {autoTrade.symbols.map((s) => (
              <Badge key={s} variant="outline" className="border-border text-foreground text-[10px] bg-secondary/50">
                {s}
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <AnimatePresence>
            {scanResults.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-10 text-center"
              >
                <ScanSearch className="size-8 text-muted-foreground/30 mb-2" />
                <p className="text-sm text-muted-foreground">
                  No scan results yet. Click &quot;Scan Markets&quot; to begin.
                </p>
              </motion.div>
            ) : (
              scanResults.map((result, i) => (
                <ScanResultCard key={result.symbol} result={result} index={i} />
              ))
            )}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  );
}
