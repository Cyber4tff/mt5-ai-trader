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
import { TrendingUp, Wallet, CheckCircle2 } from "lucide-react"
import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
  const { liveState, connection } = useTradingStore()
  const [editing, setEditing] = useState(false)
  const [balInput, setBalInput] = useState(liveState.manualBalance)
  const [eqInput, setEqInput] = useState(liveState.manualEquity)

  const balance = parseFloat(liveState.manualBalance)
  const hasBalance = !isNaN(balance) && balance > 0

  if (!liveState.mt5Confirmed) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className="bg-card border-emerald-500/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Wallet className="size-4 text-emerald-500" />
              <span className="text-sm font-semibold text-foreground">Account Balance</span>
              <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[10px]">
                CONNECTED
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={() => setEditing(!editing)}
            >
              {editing ? "Save" : "Update"}
            </Button>
          </div>

          {editing ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider">Balance ($)</label>
                <Input
                  type="number"
                  value={balInput}
                  onChange={(e) => setBalInput(e.target.value)}
                  className="mt-1 h-8 bg-background border-border text-foreground"
                  placeholder="e.g. 14984.75"
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider">Equity ($)</label>
                <Input
                  type="number"
                  value={eqInput}
                  onChange={(e) => setEqInput(e.target.value)}
                  className="mt-1 h-8 bg-background border-border text-foreground"
                  placeholder="e.g. 15000.00"
                />
              </div>
              <Button
                className="col-span-2 h-8 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                onClick={() => {
                  useTradingStore.getState().confirmMT5Connection(balInput, eqInput)
                  setEditing(false)
                }}
              >
                <CheckCircle2 className="size-3 mr-1" />
                Save Balance
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Balance</p>
                <p className={cn("text-lg font-bold font-mono", hasBalance ? "text-foreground" : "text-muted-foreground")}>
                  {hasBalance ? `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Equity</p>
                <p className={cn("text-lg font-bold font-mono", eqInput ? "text-foreground" : "text-muted-foreground")}>
                  {eqInput ? `$${parseFloat(eqInput).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                </p>
              </div>
              {connection.broker && (
                <div className="col-span-2 pt-1 border-t border-border">
                  <p className="text-[10px] text-muted-foreground">
                    {connection.broker} — {connection.server}
                    {liveState.connectedAt && (
                      <span className="ml-2">
                        Connected {new Date(liveState.connectedAt).toLocaleTimeString()}
                      </span>
                    )}
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function Home() {
  const { connection, liveState } = useTradingStore()
  const [showLaunch, setShowLaunch] = useState(true)
  const isLiveMode = connection.connected && connection.mode === "live"
  const isPaperMode = connection.connected && connection.mode === "paper"
  const isConnected = connection.connected

  // Launch animation: show for 2.5 seconds
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
            {/* Left sidebar - 3 cols on lg */}
            <div className="lg:col-span-3 space-y-4 md:space-y-6">
              <ConnectionPanel />
              <AIStatusPanel />
              {isConnected && <AutoTradePanel />}
            </div>

            {/* Main content - 9 cols on lg */}
            <div className="lg:col-span-9 space-y-4 md:space-y-6">
              {/* LIVE MODE */}
              {isLiveMode && <LiveInfoBanner />}
              {isLiveMode && <WebTerminalPanel />}
              {isLiveMode && <LiveBalanceCard />}
              {isLiveMode && <ScannerPanel />}

              {/* PAPER MODE */}
              {isPaperMode && <AccountCards />}
              {isPaperMode && <RiskPanel />}
              {isPaperMode && <ScannerPanel />}
              {isPaperMode && <PositionsTable />}

              {/* NOT CONNECTED */}
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

              {/* Scan Log - shown in all modes */}
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
