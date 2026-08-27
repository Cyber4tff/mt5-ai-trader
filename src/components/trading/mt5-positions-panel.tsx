"use client"

import { Loader2, X, ArrowUp, ArrowDown } from "lucide-react"
import { motion } from "framer-motion"
import { toast } from "sonner"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

export function MT5PositionsPanel() {
  const { mt5Positions, closeMT5Position, executingTrade } = useTradingStore()

  const handleClose = async (ticket: number, symbol: string) => {
    const success = await closeMT5Position(ticket)
    if (success) {
      toast.success(`Position #${ticket} closed`, { description: `${symbol} trade closed successfully` })
    } else {
      toast.error(`Failed to close #${ticket}`, { description: "Check the activity log for details" })
    }
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm text-foreground">
          <span className="flex items-center gap-2">
            MT5 Open Positions
          </span>
          <Badge variant="secondary" className="text-[10px]">
            {mt5Positions.length} {mt5Positions.length === 1 ? "position" : "positions"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {mt5Positions.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">
            No open positions on MT5. Execute a trade from a signal to open one.
          </p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {mt5Positions.map((pos, i) => (
              <motion.div
                key={pos.ticket}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg border",
                  pos.type === "BUY"
                    ? "border-emerald-500/20 bg-emerald-500/5"
                    : "border-red-500/20 bg-red-500/5"
                )}
              >
                <div className={cn(
                  "size-8 rounded-full flex items-center justify-center shrink-0",
                  pos.type === "BUY" ? "bg-emerald-500/20" : "bg-red-500/20"
                )}>
                  {pos.type === "BUY" ? (
                    <ArrowUp className="size-4 text-emerald-500" />
                  ) : (
                    <ArrowDown className="size-4 text-red-500" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground">{pos.symbol}</span>
                    <Badge className={cn(
                      "text-[9px] font-bold",
                      pos.type === "BUY"
                        ? "bg-emerald-500/20 text-emerald-500"
                        : "bg-red-500/20 text-red-500"
                    )}>
                      {pos.type}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      #{pos.ticket}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs">
                    <span className="text-muted-foreground">
                      {pos.volume} lots @ <span className="font-mono text-foreground">{pos.open_price.toFixed(pos.open_price >= 100 ? 2 : 5)}</span>
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <p className={cn(
                    "text-sm font-bold font-mono",
                    pos.profit >= 0 ? "text-emerald-500" : "text-red-500"
                  )}>
                    {pos.profit >= 0 ? "+" : ""}{pos.profit.toFixed(2)}
                  </p>
                </div>

                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 shrink-0"
                  onClick={() => handleClose(pos.ticket, pos.symbol)}
                  disabled={executingTrade}
                >
                  {executingTrade ? <Loader2 className="size-3 animate-spin" /> : <X className="size-3" />}
                </Button>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
