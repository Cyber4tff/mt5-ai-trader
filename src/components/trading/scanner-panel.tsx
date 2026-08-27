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
  Play,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTradingStore } from '@/lib/trading-store';
import type { ScanResult, TrendDirection, MarketBias } from '@/lib/trading-types';

const TF_ORDER = ['D1', 'H1', 'M15'];

function TrendArrow({ trend }: { trend: TrendDirection }) {
  if (trend === 'UP') return <ArrowUp className="size-3.5 text-emerald-500" />;
  if (trend === 'DOWN') return <ArrowDown className="size-3.5 text-red-500" />;
  return <ArrowRight className="size-3.5 text-zinc-500" />;
}

function biasBorderClass(bias: MarketBias) {
  if (bias === 'bullish') return 'border-emerald-500/50';
  if (bias === 'bearish') return 'border-red-500/50';
  return 'border-zinc-600/50';
}

function biasBgClass(bias: MarketBias) {
  if (bias === 'bullish') return 'bg-emerald-500/5';
  if (bias === 'bearish') return 'bg-red-500/5';
  return 'bg-zinc-900';
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
            ? 'text-emerald-400'
            : bias === 'bearish'
              ? 'text-red-400'
              : 'text-zinc-500'
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
  if (!score) return 'bg-zinc-900/50';
  const absScore = Math.abs(score);
  if (direction === 'bullish' || direction === 'BUY') {
    if (absScore >= 0.7) return 'bg-emerald-500/10';
    if (absScore >= 0.5) return 'bg-emerald-500/5';
  }
  if (direction === 'bearish' || direction === 'SELL') {
    if (absScore >= 0.7) return 'bg-red-500/10';
    if (absScore >= 0.5) return 'bg-red-500/5';
  }
  return 'bg-zinc-900/50';
}

function ScanResultCard({ result, index }: { result: ScanResult; index: number }) {
  const [expanded, setExpanded] = useState(index === 0);
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
        : 'text-zinc-400';

  const directionBadgeClass =
    direction === 'bullish' || direction === 'BUY'
      ? 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
      : direction === 'bearish' || direction === 'SELL'
        ? 'bg-red-500/15 text-red-500 border-red-500/30'
        : 'bg-zinc-700/30 text-zinc-400 border-zinc-600/30';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08 }}
      className="rounded-lg border border-zinc-800 overflow-hidden"
    >
      {/* Header row */}
      <button
        onClick={toggle}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 transition-colors hover:bg-zinc-800/30 text-left',
          headerBgFromScore(score, direction)
        )}
      >
        <span className="text-lg font-bold min-w-[80px]">{symbol}</span>

        <Badge variant="outline" className={cn('text-[10px] font-semibold', directionBadgeClass)}>
          {direction.toUpperCase()}
        </Badge>

        {confluence && (
          <span
            className={cn(
              'text-sm font-mono tabular-nums font-semibold',
              directionColor
            )}
          >
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

      {/* Expandable body */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 space-y-3 border-t border-zinc-800/50">
              {/* MTF Grid */}
              <div>
                <p className="text-[10px] uppercase text-muted-foreground tracking-wider mb-2 font-medium">
                  Multi-Timeframe Analysis
                </p>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {TF_ORDER.map((tf) => {
                    const data = timeframes[tf];
                    if (!data) return null;
                    return (
                      <TFPill
                        key={tf}
                        tf={tf}
                        trend={data.trend}
                        bias={data.bias}
                        atr={data.atr}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Confluence factors */}
              {confluence && confluence.factors.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {confluence.factors.map((f, i) => (
                    <span
                      key={i}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-muted-foreground"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              )}

              {/* Actionable signal details */}
              {hasActionable && actionable && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 space-y-3">
                  <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                    <Zap className="size-3.5" /> Actionable Signal
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block">Direction</span>
                      <span
                        className={cn(
                          'font-mono font-bold',
                          actionable.direction === 'BUY' ? 'text-emerald-500' : 'text-red-500'
                        )}
                      >
                        {actionable.direction}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Entry</span>
                      <span className="font-mono tabular-nums">{actionable.entry.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">SL</span>
                      <span className="font-mono tabular-nums text-red-400">
                        {actionable.sl.toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">TP</span>
                      <span className="font-mono tabular-nums text-emerald-400">
                        {actionable.tp.toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Volume</span>
                      <span className="font-mono tabular-nums">{actionable.volume.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">R:R</span>
                      <span className="font-mono tabular-nums font-semibold">{actionable.risk_reward.toFixed(2)}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-muted-foreground block mb-1">Confidence</span>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 rounded-full bg-zinc-800 overflow-hidden">
                          <motion.div
                            className={cn(
                              'h-full rounded-full',
                              actionable.confidence >= 0.8
                                ? 'bg-emerald-500'
                                : actionable.confidence >= 0.65
                                  ? 'bg-amber-500'
                                  : 'bg-red-500'
                            )}
                            initial={{ width: 0 }}
                            animate={{ width: `${actionable.confidence * 100}%` }}
                            transition={{ duration: 0.6, ease: 'easeOut' }}
                          />
                        </div>
                        <span className="font-mono text-xs tabular-nums font-semibold">
                          {(actionable.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Confirmation factors */}
                  {actionable.confirmation_factors.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {actionable.confirmation_factors.map((f, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className="border-emerald-500/20 text-emerald-400 bg-emerald-500/5 text-[10px]"
                        >
                          {f}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => {
                      toast.success(`Trade execution queued for ${symbol}`, {
                        description: `${actionable.direction} @ ${actionable.entry} | R:R ${actionable.risk_reward.toFixed(2)}`,
                      });
                    }}
                  >
                    <Play className="size-3" /> Execute Trade
                  </Button>
                </div>
              )}

              {/* Risk failures */}
              {!hasActionable && hasFailures && risk_failures && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
                  <p className="text-xs font-semibold text-amber-400">Signal Rejected</p>
                  <div className="flex flex-wrap gap-1.5">
                    {risk_failures.map((f, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className="border-red-500/30 text-red-400 bg-red-500/5 text-[10px]"
                      >
                        <X className="size-3" /> {f}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* No trade with reason */}
              {!hasActionable && !hasFailures && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-zinc-600 text-zinc-400 text-[10px]">
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
    <Card className="bg-zinc-900/50 border-zinc-800 gap-4">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <ScanSearch className="size-4 text-purple-400" />
          Multi-Timeframe Scanner
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Toolbar */}
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            size="sm"
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? (
              <RefreshCw className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            {scanning ? 'Scanning...' : 'Scan Markets'}
          </Button>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] uppercase text-muted-foreground tracking-wider mr-1">
              Watching:
            </span>
            {autoTrade.symbols.map((s) => (
              <Badge
                key={s}
                variant="outline"
                className="border-zinc-700 text-zinc-300 text-[10px] bg-zinc-800/50"
              >
                {s}
              </Badge>
            ))}
          </div>
        </div>

        {/* Scan results */}
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
