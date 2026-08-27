"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Bot, Timer, Hash, Lock, ShieldCheck, AlertTriangle } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

export function AutoTradePanel() {
  const {
    autoTrade, toggleAutoTrade, scanMarkets, connection, liveState,
    autoExecute, setAutoExecute,
  } = useTradingStore()
  const localInterval = autoTrade.intervalMinutes
  const isLiveMode = connection.mode === "live"
  const mt5Ready = isLiveMode ? liveState.mt5Confirmed : true

  // Auto-execute confirmation dialog
  const [showAutoExecDialog, setShowAutoExecDialog] = useState(false)
  const [pendingAutoExec, setPendingAutoExec] = useState(false)

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
      toast.success(checked ? "AI scanning enabled" : "AI scanning disabled")
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

  const handleAutoExecToggle = useCallback((checked: boolean) => {
    if (checked) {
      setShowAutoExecDialog(true)
      setPendingAutoExec(true)
    } else {
      setAutoExecute(false)
      toast.info("Auto-execute disabled")
    }
  }, [setAutoExecute])

  const confirmAutoExec = useCallback(() => {
    setAutoExecute(true)
    setShowAutoExecDialog(false)
    setPendingAutoExec(false)
    toast.success("Auto-execute authorized", {
      description: "All actionable signals will be automatically placed as trades on your MT5 account.",
    })
  }, [setAutoExecute])

  const cancelAutoExec = useCallback(() => {
    setShowAutoExecDialog(false)
    setPendingAutoExec(false)
  }, [])

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
          {/* Auto-Execute Toggle (Live Mode Only) */}
          {isLiveMode && mt5Ready && autoTrade.enabled && (
            <>
              <Separator className="bg-border" />
              <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className={cn("size-4", autoExecute ? "text-emerald-500" : "text-muted-foreground")} />
                    <div>
                      <p className="text-xs font-semibold text-foreground">Auto-Execute Trades</p>
                      <p className="text-[10px] text-muted-foreground">Automatically place authorized signals</p>
                    </div>
                  </div>
                  <Switch
                    checked={autoExecute}
                    onCheckedChange={handleAutoExecToggle}
                    disabled={pendingAutoExec}
                  />
                </div>
                {autoExecute && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="flex items-center gap-2"
                  >
                    <Badge className="bg-emerald-500/15 text-emerald-500 border-emerald-500/30 text-[10px]">
                      <ShieldCheck className="size-2.5 mr-0.5" /> AUTO-EXECUTE ON
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      Signals will be placed as real trades automatically
                    </span>
                  </motion.div>
                )}
                {!autoExecute && (
                  <p className="text-[10px] text-muted-foreground leading-relaxed">
                    When OFF, signals are displayed for manual review. Click &quot;Authorize & Execute&quot; on each signal to place the trade.
                  </p>
                )}
              </div>
            </>
          )}

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
              AI scans run automatically and show signals. {autoExecute
                ? "Authorized trades are placed automatically on your MT5 account."
                : "Click 'Authorize & Execute' on each signal to place the trade manually."
              }
            </p>
          ) : (
            <p className="text-[10px] text-muted-foreground leading-relaxed">
              Auto-trading executes trades automatically based on AI decisions and risk checks. Use DEMO mode first.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Auto-Execute Confirmation Dialog */}
      <Dialog open={showAutoExecDialog} onOpenChange={(v) => !v && cancelAutoExec()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldCheck className="size-5 text-amber-500" />
              Authorize Auto-Execution
            </DialogTitle>
            <DialogDescription>
              This will allow the system to automatically place real trades on your MT5 account whenever an actionable signal is detected.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="size-4 text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-red-600 dark:text-red-400">Risk Warning</p>
                <p className="text-[11px] text-red-500/80 leading-relaxed mt-1">
                  Auto-execution places REAL trades with REAL money. Losses can exceed your expectations.
                  Ensure you understand the risks and have appropriate risk management in place.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">When auto-execute is ON:</p>
              <ul className="text-xs text-foreground space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  Every actionable signal is automatically placed as a market order
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  Stop Loss and Take Profit are set from the AI signal
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  You can turn it off at any time to review signals manually
                </li>
              </ul>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-2">
            <Button variant="outline" className="flex-1" onClick={cancelAutoExec}>
              Cancel
            </Button>
            <Button
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 font-semibold"
              onClick={confirmAutoExec}
            >
              <ShieldCheck className="size-4 mr-2" />
              Authorize Auto-Execute
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
