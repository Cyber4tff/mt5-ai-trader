'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useTradingStore } from '@/lib/trading-store';

function ThinProgress({ value, color }: { value: number; color: string }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  );
}

function AnimatedValue({ value, className }: { value: string; className?: string }) {
  return (
    <AnimatePresence mode="popLayout">
      <motion.span
        key={value}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 8 }}
        transition={{ duration: 0.3 }}
        className={cn('text-lg font-mono tabular-nums', className)}
      >
        {value}
      </motion.span>
    </AnimatePresence>
  );
}

function MetricCard({
  label,
  value,
  valueColor,
  sub,
  progress,
  progressColor,
  icon: Icon,
}: {
  label: string;
  value: string;
  valueColor?: string;
  sub?: string;
  progress?: number;
  progressColor?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-2 rounded-lg bg-zinc-900/80 p-3 border border-zinc-800/50"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase text-muted-foreground tracking-wider">{label}</span>
        {Icon && <Icon className="size-3.5 text-muted-foreground" />}
      </div>
      <AnimatedValue value={value} className={valueColor} />
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      {progress !== undefined && progressColor && (
        <div className="mt-1">
          <ThinProgress value={progress} color={progressColor} />
        </div>
      )}
    </motion.div>
  );
}

export function RiskPanel() {
  const riskSummary = useTradingStore((s) => s.riskSummary);
  const aiStatus = useTradingStore((s) => s.aiStatus);
  const connection = useTradingStore((s) => s.connection);

  const balance = connection.account?.balance ?? 0;
  const maxDailyLoss = balance * aiStatus.max_daily_loss_pct;
  const maxTrades = aiStatus.max_trades_per_day;
  const maxConsecutiveLosses = aiStatus.max_consecutive_losses;

  // Daily P&L calculations
  const pnl = riskSummary.realized_pnl;
  const pnlColor = pnl >= 0 ? 'text-emerald-500' : 'text-red-500';
  const pnlSign = pnl >= 0 ? '+' : '';
  const pnlValue = `${pnlSign}$${Math.abs(pnl).toFixed(2)}`;
  // Progress: how much of the loss limit has been used (0 if in profit)
  const lossUsage = pnl < 0 ? (Math.abs(pnl) / maxDailyLoss) * 100 : 0;
  const pnlProgressColor =
    pnl >= 0
      ? '#10b981'
      : lossUsage > 80
        ? '#ef4444'
        : lossUsage > 50
          ? '#f59e0b'
          : '#10b981';

  // Trades today
  const tradesUsed = riskSummary.trades_count;
  const tradesProgress = (tradesUsed / maxTrades) * 100;
  const tradesProgressColor =
    tradesUsed >= maxTrades
      ? '#ef4444'
      : tradesUsed >= maxTrades * 0.8
        ? '#f59e0b'
        : '#10b981';

  // Consecutive losses
  const consLosses = riskSummary.consecutive_losses;
  const consLossProgress = (consLosses / maxConsecutiveLosses) * 100;
  const consLossColor =
    consLosses >= maxConsecutiveLosses
      ? 'text-red-500'
      : consLosses >= maxConsecutiveLosses * 0.6
        ? 'text-amber-500'
        : 'text-emerald-500';
  const consLossProgressColor =
    consLosses >= maxConsecutiveLosses ? '#ef4444' : '#f59e0b';

  // Remaining loss limit
  const remainingPct = riskSummary.remaining_loss_limit * 100;
  const remainingColor =
    remainingPct > 50
      ? 'text-emerald-500'
      : remainingPct > 20
        ? 'text-amber-500'
        : 'text-red-500';
  const remainingProgressColor =
    remainingPct > 50
      ? '#10b981'
      : remainingPct > 20
        ? '#f59e0b'
        : '#ef4444';

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 gap-4">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="size-4 text-emerald-500" />
          Risk Management
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Daily P&L"
          value={pnlValue}
          valueColor={pnlColor}
          sub={`$${Math.abs(pnl).toFixed(2)} / $${maxDailyLoss.toFixed(2)} limit`}
          progress={lossUsage}
          progressColor={pnlProgressColor}
          icon={pnl >= 0 ? TrendingUp : TrendingDown}
        />

        <MetricCard
          label="Trades Today"
          value={`${tradesUsed} / ${maxTrades}`}
          sub={`${riskSummary.remaining_trades} remaining`}
          progress={tradesProgress}
          progressColor={tradesProgressColor}
        />

        <MetricCard
          label="Consecutive Losses"
          value={`${consLosses} / ${maxConsecutiveLosses}`}
          valueColor={consLossColor}
          sub={
            consLosses >= maxConsecutiveLosses
              ? 'LIMIT REACHED'
              : `${maxConsecutiveLosses - consLosses} remaining`
          }
          progress={consLossProgress}
          progressColor={consLossProgressColor}
          icon={consLosses >= maxConsecutiveLosses ? AlertTriangle : undefined}
        />

        <MetricCard
          label="Remaining Loss Limit"
          value={`${remainingPct.toFixed(1)}%`}
          valueColor={remainingColor}
          sub={
            remainingPct < 20
              ? 'CRITICAL'
              : remainingPct < 50
                ? 'CAUTION'
                : 'HEALTHY'
          }
          progress={remainingPct}
          progressColor={remainingProgressColor}
        />
      </CardContent>

      <CardFooter className="flex-col items-center gap-2 pt-0">
        <Badge
          variant="outline"
          className="border-amber-500/50 text-amber-500 bg-amber-500/10 text-xs font-semibold tracking-wider"
        >
          NO TRADE DEFAULT
        </Badge>
        <p className="text-xs text-muted-foreground text-center">
          A trade only executes when ALL risk checks pass.
        </p>
      </CardFooter>
    </Card>
  );
}
