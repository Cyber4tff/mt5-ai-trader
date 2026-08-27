"use client"

import { useEffect, useState } from "react"
import { Header } from "@/components/trading/header"
import { ConnectionPanel } from "@/components/trading/connection-panel"
import { WebTerminalPanel } from "@/components/trading/web-terminal-panel"
import { AutoTradePanel } from "@/components/trading/auto-trade-panel"
import { AIStatusPanel } from "@/components/trading/ai-status-panel"
import { AccountCards } from "@/components/trading/account-cards"
import { RiskPanel } from "@/components/trading/risk-panel"
import { ScannerPanel } from "@/components/trading/scanner-panel"
import { PositionsTable } from "@/components/trading/positions-table"
import { ScanLog } from "@/components/trading/scan-log"
import { LaunchScreen } from "@/components/trading/launch-screen"
import { useTradingStore } from "@/lib/trading-store"
import { TrendingUp, Wallet, RefreshCw, WifiOff } from "lucide-react"
import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

function LiveInfoBanner() {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 dark:bg-emerald-500/10 dark:border-emerald-500/20">
      <div className="flex-1">
        <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          MT5 Web Terminal Active — AI Scanning Enabled
        </p>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          Log in with your MT5 credentials in the terminal below. The AI engine scans markets and shows signals.
        </p>
      </div>
    </div>
  )
}

function LiveBalanceCard() {
  const { liveState, connection, fetchMT5Account } = useTradingStore()

  if (!liveState.mt5Confirmed) return null

  const hasBalance = liveState.balance > 0
  const hasEquity = liveState.equity > 0
  const currency = liveState.mt5Currency || "USD"

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Wallet className="size-4 text-emerald-500" />
              <span className="text-sm font-semibold text-foreground">MT5 Account</span>
              {liveState.mt5Available ? (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[10px]">
                  AUTO-SYNC
                </Badge>
              ) : (
                <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30 text-[10px]">
                  TERMINAL ONLY
                </Badge>
              )}
            </div>
            {liveState.mt5Available && (
              <button
                onClick={() => fetchMT5Account()}
                className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                title="Refresh balance from MT5"
              >
                <RefreshCw className="size-3.5" />
              </button>
            )}
          </div>

          {liveState.mt5Available && hasBalance ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Balance</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {currency} {liveState.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Equity</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {currency} {liveState.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Floating P&L</p>
                <p className={cn(
                  "text-sm font-bold font-mono",
                  liveState.profit >= 0 ? "text-emerald-500" : "text-red-500"
                )}>
                  {liveState.profit >= 0 ? "+" : ""}{currency} {liveState.profit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Free Margin</p>
                <p className="text-sm font-bold font-mono text-foreground">
                  {currency} {liveState.freeMargin.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          ) : liveState.mt5Available && !hasBalance ? (
            <div className="flex flex-col items-center py-3 text-center">
              <RefreshCw className="size-5 text-muted-foreground animate-spin mb-2" />
              <p className="text-xs text-muted-foreground">Fetching account data from MT5...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-2">
              <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                <WifiOff className="size-4" />
                <span className="text-xs font-medium">Auto-balance unavailable</span>
              </div>
              <p className="text-[11px] text-muted-foreground text-center leading-relaxed">
                Your account balance is visible in the MT5 Web Terminal above.
                Auto-sync requires the MT5 desktop app on a Windows server.
              </p>
              {liveState.mt5Login && (
                <p className="text-[10px] text-muted-foreground">
                  Account #{liveState.mt5Login} · {connection.server}
                </p>
              )}
            </div>
          )}

          {liveState.lastFetch && liveState.mt5Available && (
            <p className="text-[10px] text-muted-foreground mt-2 pt-2 border-t border-border">
              Last sync: {new Date(liveState.lastFetch).toLocaleTimeString()}
              {liveState.mt5Name && ` · ${liveState.mt5Name}`}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

function LiveBalancePoller() {
  const { liveState, fetchMT5Account } = useTradingStore()

  useEffect(() => {
    if (!liveState.mt5Confirmed || !liveState.mt5Available) return

    // Poll every 5 seconds when MT5 auto-sync is active
    const interval = setInterval(() => {
      fetchMT5Account()
    }, 5000)

    return () => clearInterval(interval)
  }, [liveState.mt5Confirmed, liveState.mt5Available, fetchMT5Account])

  return null
}

export default function Home() {
  const { connection, liveState } = useTradingStore()
  const [showLaunch, setShowLaunch] = useState(true)
  const isLiveMode = connection.connected && connection.mode === "live"
  const isPaperMode = connection.connected && connection.mode === "paper"
  const isConnected = connection.connected

  useEffect(() => {
    const timer = setTimeout(() => setShowLaunch(false), 2500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <>
      <LaunchScreen visible={showLaunch} />
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
            {/* Left sidebar */}
            <div className="lg:col-span-3 space-y-4 md:space-y-6">
              <ConnectionPanel />
              <AIStatusPanel />
              {isConnected && <AutoTradePanel />}
            </div>

            {/* Main content */}
            <div className="lg:col-span-9 space-y-4 md:space-y-6">
              {isLiveMode && <LiveInfoBanner />}
              {isLiveMode && <WebTerminalPanel />}
              {isLiveMode && <LiveBalanceCard />}
              <LiveBalancePoller />
              {isLiveMode && <ScannerPanel />}

              {isPaperMode && <AccountCards />}
              {isPaperMode && <RiskPanel />}
              {isPaperMode && <ScannerPanel />}
              {isPaperMode && <PositionsTable />}

              {!isConnected && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="size-16 rounded-full bg-muted border border-border flex items-center justify-center mb-4">
                    <TrendingUp className="size-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-muted-foreground mb-1">No Active Trading Session</h3>
                  <p className="text-sm text-muted-foreground/70 max-w-md">
                    Select a broker and connect to start live trading with your real MT5 account, or start a paper trading session to practice with virtual funds.
                  </p>
                </div>
              )}

              {isConnected && <ScanLog />}
            </div>
          </div>
        </main>
        <footer className="border-t border-border bg-background py-4 px-4 md:px-6 mt-auto">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Cloud AI Trader v2.0 — Live & Paper Trading</span>
            <span>Supports OctaFX, Exness, Headway & any MT5 broker</span>
          </div>
        </footer>
      </div>
    </>
  )
}
