"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Bot, Timer, Hash, Activity } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

export function AutoTradePanel() {
  const { autoTrade, toggleAutoTrade, scanMarkets, connection } = useTradingStore()
  const localInterval = autoTrade.intervalMinutes

  const handleToggle = useCallback(
    async (checked: boolean) => {
      if (!connection.connected) {
        toast.error("Not connected", { description: "Connect to a broker first." })
        return
      }
      await toggleAutoTrade(checked, localInterval)
      toast.success(checked ? "Auto-trading enabled" : "Auto-trading disabled")
    },
    [connection.connected, toggleAutoTrade, localInterval]
  )

  const prevEnabledRef = useRef(autoTrade.enabled)

  // Trigger scan 1s after enabling
  useEffect(() => {
    if (autoTrade.enabled && !prevEnabledRef.current) {
      const timer = setTimeout(() => {
        scanMarkets()
      }, 1000)
      return () => clearTimeout(timer)
    }
    prevEnabledRef.current = autoTrade.enabled
  }, [autoTrade.enabled, scanMarkets])

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
      animate={autoTrade.enabled ? { borderColor: ["rgba(16,185,129,0)", "rgba(16,185,129,0.6)", "rgba(16,185,129,0)"] } : {}}
      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      className="rounded-xl"
    >
      <Card
        className={cn(
          "bg-zinc-900/50 border-zinc-800 transition-colors",
          autoTrade.enabled && "border-emerald-500/40"
        )}
      >
        <CardHeader className="pb-3 gap-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-300">
              <Bot className="size-4 text-zinc-400" />
              Auto Trading
            </CardTitle>
            {autoTrade.enabled ? (
              <motion.span
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400"
              >
                <span className="size-1.5 rounded-full bg-emerald-500" />
                ACTIVE
              </motion.span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                <span className="size-1.5 rounded-full bg-zinc-600" />
                PAUSED
              </span>
            )}
          </div>

          {/* Toggle Switch */}
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
        </CardHeader>

        <CardContent className="space-y-4 pt-0">
          {/* Scan Interval Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="flex items-center gap-1.5">
                <Timer className="size-3" />
                Scan Interval
              </span>
              <span className="font-mono text-white">{localInterval} min</span>
            </div>
            <Slider
              value={[localInterval]}
              onValueChange={handleSliderChange}
              min={15}
              max={120}
              step={5}
              disabled={!autoTrade.enabled}
            />
            <div className="flex justify-between text-[10px] text-zinc-600">
              <span>15m</span>
              <span>120m</span>
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          {/* Symbols */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
              Symbols
            </span>
            <div className="flex flex-wrap gap-1.5">
              {autoTrade.symbols.map((sym) => (
                <Badge
                  key={sym}
                  variant="secondary"
                  className="bg-zinc-800 text-zinc-300 border-zinc-700 text-xs"
                >
                  {sym}
                </Badge>
              ))}
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          {/* Last Scan & Cycle Count */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                <Timer className="size-2.5" />
                Last Scan
              </span>
              <p className="text-xs font-mono text-zinc-300">
                {formatTime(autoTrade.lastScan)}
              </p>
            </div>
            <div className="space-y-1">
              <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                <Hash className="size-2.5" />
                Cycles
              </span>
              <p className="text-xs font-mono text-zinc-300">
                {autoTrade.cycleCount}
              </p>
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          {/* Warning */}
          <p className="text-[10px] text-zinc-600 leading-relaxed">
            ⚠ Auto-trading executes trades automatically based on AI decisions and risk checks. Use DEMO mode first.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}
