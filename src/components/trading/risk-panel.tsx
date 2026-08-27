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
    <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
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
  placeholder = false,
}: {
  label: string;
  value: string;
  valueColor?: string;
  sub?: string;
  progress?: number;
  progressColor?: string;
  icon?: React.ComponentType<{ className?: string }>;
  placeholder?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex flex-col gap-2 rounded-lg p-3 border",
        placeholder
          ? "border-dashed border-border bg-card/50"
          : "border-border bg-card"
      )}
    >
      <div className="flex items-center justify-between">
        <span className={cn("text-xs uppercase tracking-wider", placeholder ? "text-muted-foreground/60" : "text-muted-foreground")}>{label}</span>
        {Icon && <Icon className={cn("size-3.5", placeholder ? "text-muted-foreground/60" : "text-muted-foreground")} />}
      </div>
      <AnimatedValue value={value} className={placeholder ? "text-muted-foreground/60" : (valueColor || 'text-foreground')} />
      {sub && <span className={cn("text-xs", placeholder ? "text-muted-foreground/60" : "text-muted-foreground")}>{sub}</span>}
      {progress !== undefined && progressColor && !placeholder && (
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
  const isConnected = connection.connected;

  const balance = connection.account?.balance ?? 0;
  const maxDailyLoss = balance * (aiStatus.max_daily_loss_pct || 0.06);
  const maxTrades = aiStatus.max_trades_per_day || 10;
  const maxConsecutiveLosses = aiStatus.max_consecutive_losses || 3;

  // Daily P&L calculations
  const pnl = riskSummary.realized_pnl;
  const pnlColor = pnl >= 0 ? 'text-emerald-500' : 'text-red-500';
  const pnlSign = pnl >= 0 ? '+' : '';
  const pnlValue = `${pnlSign}$${Math.abs(pnl).toFixed(2)}`;
  const lossUsage = maxDailyLoss > 0 && pnl < 0 ? (Math.abs(pnl) / maxDailyLoss) * 100 : 0;
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
  const tradesProgress = maxTrades > 0 ? (tradesUsed / maxTrades) * 100 : 0;
  const tradesProgressColor =
    tradesUsed >= maxTrades
      ? '#ef4444'
      : tradesUsed >= maxTrades * 0.8
        ? '#f59e0b'
        : '#10b981';

  // Consecutive losses
  const consLosses = riskSummary.consecutive_losses;
  const consLossProgress = maxConsecutiveLosses > 0 ? (consLosses / maxConsecutiveLosses) * 100 : 0;
  const consLossColor =
    consLosses >= maxConsecutiveLosses
      ? 'text-red-500'
      : consLosses >= maxConsecutiveLosses * 0.6
        ? 'text-amber-500'
        : 'text-emerald-500';
  const consLossProgressColor =
    consLosses >= maxConsecutiveLosses ? '#ef4444' : '#f59e0b';

  // Remaining loss limit (dollar amount to percentage of balance)
  const remainingLossLimit = riskSummary.remaining_loss_limit;
  const remainingPct = balance > 0 ? (remainingLossLimit / balance) * 100 : 100;
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
    <Card className="bg-card border-border gap-4">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-base text-foreground">
          <ShieldCheck className="size-4 text-emerald-500" />
          Risk Management
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Daily P&L"
          value={isConnected ? pnlValue : "$0.00"}
          valueColor={isConnected ? pnlColor : 'text-muted-foreground/60'}
          sub={isConnected ? `$${Math.abs(pnl).toFixed(2)} / $${maxDailyLoss.toFixed(2)} limit` : undefined}
          progress={isConnected ? lossUsage : undefined}
          progressColor={pnlProgressColor}
          icon={isConnected ? (pnl >= 0 ? TrendingUp : TrendingDown) : undefined}
          placeholder={!isConnected}
        />

        <MetricCard
          label="Trades Today"
          value={isConnected ? `${tradesUsed} / ${maxTrades}` : `0 / ${maxTrades || 10}`}
          sub={isConnected ? `${riskSummary.remaining_trades} remaining` : undefined}
          progress={isConnected ? tradesProgress : undefined}
          progressColor={tradesProgressColor}
          placeholder={!isConnected}
        />

        <MetricCard
          label="Consecutive Losses"
          value={isConnected ? `${consLosses} / ${maxConsecutiveLosses}` : `0 / ${maxConsecutiveLosses || 3}`}
          valueColor={isConnected ? consLossColor : 'text-muted-foreground/60'}
          sub={
            isConnected
              ? (consLosses >= maxConsecutiveLosses
                  ? 'LIMIT REACHED'
                  : `${maxConsecutiveLosses - consLosses} remaining`)
              : undefined
          }
          progress={isConnected ? consLossProgress : undefined}
          progressColor={consLossProgressColor}
          icon={isConnected && consLosses >= maxConsecutiveLosses ? AlertTriangle : undefined}
          placeholder={!isConnected}
        />

        <MetricCard
          label="Remaining Loss Limit"
          value={isConnected ? `$${remainingLossLimit.toFixed(2)}` : "$--"}
          valueColor={isConnected ? remainingColor : 'text-muted-foreground/60'}
          sub={
            isConnected
              ? (remainingPct < 20
                  ? 'CRITICAL'
                  : remainingPct < 50
                    ? 'CAUTION'
                    : 'HEALTHY')
              : undefined
          }
          progress={isConnected ? remainingPct : undefined}
          progressColor={remainingProgressColor}
          placeholder={!isConnected}
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
          A trade only executes when ALL 9 risk checks pass.
        </p>
      </CardFooter>
    </Card>
  );
}
