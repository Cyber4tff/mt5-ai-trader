"use client"

import { useEffect } from "react"
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
import { useTradingStore } from "@/lib/trading-store"

function LiveInfoBanner() {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 mb-4">
      <div className="flex-1">
        <p className="text-xs text-emerald-400 font-medium">
          MT5 Web Terminal Active
        </p>
        <p className="text-[11px] text-zinc-400 mt-0.5">
          Log in with your MT5 credentials in the terminal below. Your account data, positions, and trades are managed directly by your broker.
        </p>
      </div>
    </div>
  )
}

export default function Home() {
  const { connection } = useTradingStore()
  const isLiveMode = connection.connected && connection.mode === "live"
  const isPaperMode = connection.connected && connection.mode === "paper"
  const isConnected = connection.connected

  useEffect(() => {
    document.documentElement.classList.add('dark')
  }, [])

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <Header />
      <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
          {/* Left sidebar - 3 cols on lg */}
          <div className="lg:col-span-3 space-y-4 md:space-y-6">
            <ConnectionPanel />
            {/* Show AI analysis panels in sidebar for both modes */}
            <AIStatusPanel />
            {isPaperMode && <AutoTradePanel />}
          </div>

          {/* Main content - 9 cols on lg */}
          <div className="lg:col-span-9 space-y-4 md:space-y-6">
            {/* LIVE MODE: Show MT5 Web Terminal */}
            {isLiveMode && <LiveInfoBanner />}
            {isLiveMode && <WebTerminalPanel />}

            {/* PAPER MODE: Show account cards, risk, scanner, positions */}
            {isPaperMode && <AccountCards />}
            {isPaperMode && <RiskPanel />}
            {isPaperMode && <ScannerPanel />}
            {isPaperMode && <PositionsTable />}

            {/* NOT CONNECTED: Show empty state */}
            {!isConnected && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="size-16 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
                  <svg className="size-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-zinc-400 mb-1">No Active Trading Session</h3>
                <p className="text-sm text-zinc-500 max-w-md">
                  Select a broker and connect to start live trading with your real MT5 account, or start a paper trading session to practice with virtual funds.
                </p>
              </div>
            )}

            {/* Scan Log - shown in all modes */}
            {isConnected && <ScanLog />}
          </div>
        </div>
      </main>
      <footer className="border-t border-zinc-800 bg-zinc-950 py-4 px-4 md:px-6 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-zinc-500">
          <span>Cloud AI Trader v2.0 — Live & Paper Trading</span>
          <span>Supports OctaFX, Exness, Headway & any MT5 broker</span>
        </div>
      </footer>
    </div>
  )
}
