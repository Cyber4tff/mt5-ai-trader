"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Bot, Timer, Hash, Lock } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

export function AutoTradePanel() {
  const { autoTrade, toggleAutoTrade, scanMarkets, connection, liveState } = useTradingStore()
  const localInterval = autoTrade.intervalMinutes
  const isLiveMode = connection.mode === "live"
  const mt5Ready = isLiveMode ? liveState.mt5Confirmed : true

  // ── Auto-scan interval timer ─────────────────────────────
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (autoTrade.enabled && mt5Ready) {
      if (timerRef.current) clearInterval(timerRef.current)
      timerRef.current = setInterval(() => {
        scanMarkets()
      }, localInterval * 60 * 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [autoTrade.enabled, localInterval, scanMarkets, mt5Ready])

  const handleToggle = useCallback(
    async (checked: boolean) => {
      if (!connection.connected) {
        toast.error("Not connected", { description: "Connect to a broker first." })
        return
      }
      if (isLiveMode && !liveState.mt5Confirmed) {
        toast.error("MT5 not confirmed", { description: "Please confirm your MT5 connection in the Trading Session panel first." })
        return
      }
      await toggleAutoTrade(checked, localInterval)
      toast.success(checked ? "Auto-trading enabled" : "Auto-trading disabled")
    },
    [connection.connected, isLiveMode, liveState.mt5Confirmed, toggleAutoTrade, localInterval]
  )

  const prevEnabledRef = useRef(autoTrade.enabled)

  // Trigger scan 1s after enabling
  useEffect(() => {
    if (autoTrade.enabled && !prevEnabledRef.current && mt5Ready) {
      const timer = setTimeout(() => {
        scanMarkets()
      }, 1000)
      return () => clearTimeout(timer)
    }
    prevEnabledRef.current = autoTrade.enabled
  }, [autoTrade.enabled, scanMarkets, mt5Ready])

  const handleSliderChange = useCallback(
    (value: number[]) => {
      const v = value[0]
      if (autoTrade.enabled) {
        toggleAutoTrade(true, v)
      }
    },
    [autoTrade.enabled, toggleAutoTrade]
  )

  const formatTime = (iso: string | null) => {
    if (!iso) return "Never"
    try {
      return new Date(iso).toLocaleTimeString()
    } catch {
      return "Never"
    }
  }

  return (
    <motion.div
      animate={autoTrade.enabled && mt5Ready ? { borderColor: ["rgba(16,185,129,0)", "rgba(16,185,129,0.6)", "rgba(16,185,129,0)"] } : {}}
      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      className="rounded-xl"
    >
      <Card
        className={cn(
          "bg-card border-border transition-colors",
          autoTrade.enabled && mt5Ready && "border-emerald-500/40"
        )}
      >
        <CardHeader className="pb-3 gap-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Bot className="size-4 text-muted-foreground" />
              {isLiveMode ? "AI Signal Scanner" : "Auto Trading"}
            </CardTitle>
            {autoTrade.enabled && mt5Ready ? (
              <motion.span
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-500"
              >
                <span className="size-1.5 rounded-full bg-emerald-500" />
                ACTIVE
              </motion.span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                PAUSED
              </span>
            )}
          </div>

          {/* MT5 Confirmation Lock (Live Mode Only) */}
          {isLiveMode && !liveState.mt5Confirmed && (
            <div className="flex flex-col items-center gap-2 py-3">
              <div className="size-10 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                <Lock className="size-4 text-amber-500" />
              </div>
              <p className="text-[11px] text-amber-600 dark:text-amber-400 text-center leading-relaxed">
                MT5 connection required. Log into the terminal and confirm your connection to enable AI scanning.
              </p>
              <Button
                size="sm"
                className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => {
                  // Scroll to the connection panel - use the confirm button there
                  document.querySelector('[data-confirm-mt5]')?.scrollIntoView({ behavior: 'smooth' })
                  toast.info('Scroll down in the sidebar to confirm your MT5 connection.')
                }}
              >
                Go to Connection Panel
              </Button>
            </div>
          )}

          {/* Toggle Switch (only show if MT5 ready or paper mode) */}
          {(mt5Ready || !isLiveMode) && (
            <div className="flex items-center justify-center py-1">
              <Switch
                checked={autoTrade.enabled}
                onCheckedChange={handleToggle}
                className={cn(
                  "scale-[2] origin-center",
                  "data-[state=checked]:bg-emerald-500"
                )}
              />
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-4 pt-0">
          {/* Scan Interval Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Timer className="size-3" />
                Scan Interval
              </span>
              <span className="font-mono text-foreground">{localInterval} min</span>
            </div>
            <Slider
              value={[localInterval]}
              onValueChange={handleSliderChange}
              min={15}
              max={120}
              step={5}
              disabled={!autoTrade.enabled || !mt5Ready}
            />
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>15m</span>
              <span>120m</span>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Symbols */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Symbols
            </span>
            <div className="flex flex-wrap gap-1.5">
              {autoTrade.symbols.map((sym) => (
                <Badge
                  key={sym}
                  variant="secondary"
                  className="bg-secondary text-secondary-foreground border-border text-xs"
                >
                  {sym}
                </Badge>
              ))}
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Last Scan & Cycle Count */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                <Timer className="size-2.5" />
                Last Scan
              </span>
              <p className="text-xs font-mono text-foreground">
                {formatTime(autoTrade.lastScan)}
              </p>
            </div>
            <div className="space-y-1">
              <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                <Hash className="size-2.5" />
                Cycles
              </span>
              <p className="text-xs font-mono text-foreground">
                {autoTrade.cycleCount}
              </p>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Mode-specific warning */}
          {isLiveMode ? (
            <p className="text-[10px] text-amber-600 dark:text-amber-400/80 leading-relaxed">
              AI scans run automatically and show signals below. Trade them manually in your MT5 Web Terminal.
            </p>
          ) : (
            <p className="text-[10px] text-muted-foreground leading-relaxed">
              Auto-trading executes trades automatically based on AI decisions and risk checks. Use DEMO mode first.
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
