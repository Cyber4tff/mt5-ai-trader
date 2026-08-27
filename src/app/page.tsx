"use client"

import { useEffect } from "react"
import { Header } from "@/components/trading/header"
import { ConnectionPanel } from "@/components/trading/connection-panel"
import { AutoTradePanel } from "@/components/trading/auto-trade-panel"
import { AIStatusPanel } from "@/components/trading/ai-status-panel"
import { AccountCards } from "@/components/trading/account-cards"
import { RiskPanel } from "@/components/trading/risk-panel"
import { ScannerPanel } from "@/components/trading/scanner-panel"
import { PositionsTable } from "@/components/trading/positions-table"
import { ScanLog } from "@/components/trading/scan-log"

export default function Home() {
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
            <AutoTradePanel />
            <AIStatusPanel />
          </div>

          {/* Main content - 9 cols on lg */}
          <div className="lg:col-span-9 space-y-4 md:space-y-6">
            <AccountCards />
            <RiskPanel />
            <ScannerPanel />
            <PositionsTable />
            <ScanLog />
          </div>
        </div>
      </main>
      <footer className="border-t border-zinc-800 bg-zinc-950 py-4 px-4 md:px-6 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-zinc-500">
          <span>MT5 AI Trader v2.0 — Naked Forex + Market Structure + Multi-Timeframe Analysis</span>
          <span>Strict NO TRADE default. All risk checks must pass.</span>
        </div>
      </footer>
    </div>
  )
}
