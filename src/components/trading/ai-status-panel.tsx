"use client"

import { Cpu, ChevronRight, ShieldCheck, Target, TrendingUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

export function AIStatusPanel() {
  const { aiStatus } = useTradingStore()

  const riskParams = [
    { label: "Risk/Trade", value: `${(aiStatus.risk_per_trade * 100).toFixed(1)}%` },
    { label: "Max Daily Loss", value: `${(aiStatus.max_daily_loss_pct * 100).toFixed(1)}%` },
    { label: "Max Consec. Losses", value: String(aiStatus.max_consecutive_losses) },
    { label: "Max Open Positions", value: String(aiStatus.max_open_positions) },
    { label: "Max Trades/Day", value: String(aiStatus.max_trades_per_day) },
    { label: "Min R:R", value: `${aiStatus.min_risk_reward.toFixed(1)}` },
  ]

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Cpu className="size-4 text-muted-foreground" />
          AI Engine Status
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 pt-0 text-xs">
        {/* 1. Strategy Info */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1.5">
            <Target className="size-3" />
            Strategy
          </p>
          <p className="text-xs text-foreground font-medium leading-tight">
            {aiStatus.strategy}
          </p>
          <div className="space-y-1.5 mt-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Patterns</span>
            <div className="flex flex-wrap gap-1">
              {aiStatus.patterns.map((p) => (
                <Badge
                  key={p}
                  variant="outline"
                  className="border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-[10px] px-1.5 py-0 h-5"
                >
                  {p}
                </Badge>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Structure Analysis</span>
            <div className="flex flex-wrap gap-1">
              {aiStatus.structure_analysis.map((s) => (
                <Badge
                  key={s}
                  variant="outline"
                  className="border-sky-500/30 text-sky-600 dark:text-sky-400 text-[10px] px-1.5 py-0 h-5"
                >
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        <Separator className="bg-border" />

        {/* 2. MTF Timeframes */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1.5">
            <TrendingUp className="size-3" />
            MTF Timeframes
          </p>
          <div className="flex items-center gap-1">
            {aiStatus.mtf_timeframes.map((tf, i) => (
              <span key={tf} className="flex items-center gap-1">
                <span className="bg-secondary border border-border px-2 py-1 text-center text-[10px] font-mono text-foreground rounded">
                  {tf}
                </span>
                {i < aiStatus.mtf_timeframes.length - 1 && (
                  <ChevronRight className="size-3 text-muted-foreground" />
                )}
              </span>
            ))}
          </div>
        </div>

        <Separator className="bg-border" />

        {/* 3. Risk Configuration */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1.5">
            <ShieldCheck className="size-3" />
            Risk Configuration
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {riskParams.map((rp) => (
              <div
                key={rp.label}
                className="bg-secondary/50 border border-border rounded-lg p-2"
              >
                <p className="text-[10px] text-muted-foreground truncate">{rp.label}</p>
                <p className="text-sm font-mono font-semibold text-foreground mt-0.5">
                  {rp.value}
                </p>
              </div>
            ))}
          </div>
        </div>

        <Separator className="bg-border" />

        {/* 4. Confidence Thresholds */}
        <div className="space-y-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
            Confidence Thresholds
          </p>
          <div className="space-y-2.5">
            <ConfidenceBar
              label="Min Confidence"
              value={Math.round(aiStatus.confidence_threshold * 100)}
              color="emerald"
            />
            <ConfidenceBar
              label="High Confidence"
              value={Math.round(aiStatus.high_confidence * 100)}
              color="sky"
            />
          </div>
        </div>

        <Separator className="bg-border" />

        {/* 5. Mode & Trailing */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge
            className={cn(
              "text-[10px] font-bold uppercase tracking-wider",
              aiStatus.mode === "demo"
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                : "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30"
            )}
          >
            {aiStatus.mode === "demo" ? "DEMO" : "LIVE"}
          </Badge>
          <Badge
            className={cn(
              "text-[10px] font-bold uppercase tracking-wider",
              aiStatus.trailing_stop
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                : "bg-secondary text-muted-foreground border border-border"
            )}
          >
            Trailing Stop: {aiStatus.trailing_stop ? "ON" : "OFF"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

function ConfidenceBar({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color: "emerald" | "sky"
}) {
  const barColor =
    color === "emerald"
      ? "bg-emerald-500"
      : "bg-sky-500"

  const markerColor =
    color === "emerald"
      ? "text-emerald-500 border-emerald-500"
      : "text-sky-500 border-sky-500"

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground">{label}</span>
        <span className={cn("text-xs font-mono font-semibold", markerColor)}>
          {value}%
        </span>
      </div>
      <div className="relative h-1.5 w-full rounded-full bg-secondary">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${value}%` }}
        />
        <div
          className={cn(
            "absolute top-1/2 -translate-y-1/2 -translate-x-1/2 transition-all",
            markerColor
          )}
          style={{ left: `${value}%` }}
        >
          <div
            className={cn(
              "w-0 h-0",
              "border-l-[4px] border-l-transparent",
              "border-r-[4px] border-r-transparent",
              color === "emerald"
                ? "border-b-[6px] border-b-emerald-400"
                : "border-b-[6px] border-b-sky-400"
            )}
          />
        </div>
      </div>
    </div>
  )
}