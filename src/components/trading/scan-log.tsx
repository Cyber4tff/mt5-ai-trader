"use client"

import { useEffect, useRef, useCallback } from "react"
import { ScrollText } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useTradingStore } from "@/lib/trading-store"

function colorizeLogLine(line: string): React.ReactNode {
  if (line.includes("ACTIONABLE")) {
    return <span className="text-emerald-600 dark:text-emerald-400">{line}</span>
  }
  if (line.toLowerCase().includes("rejected")) {
    return <span className="text-amber-600 dark:text-amber-400">{line}</span>
  }
  if (line.toLowerCase().includes("error")) {
    return <span className="text-red-600 dark:text-red-400">{line}</span>
  }
  if (line.includes("NO TRADE")) {
    return <span className="text-muted-foreground/60">{line}</span>
  }

  const tsMatch = line.match(/^(\[\d{2}:\d{2}:\d{2}(?: [AP]M)?])/)
  if (tsMatch) {
    const ts = tsMatch[1]
    const rest = line.slice(ts.length)
    return (
      <>
        <span className="text-muted-foreground/50">{ts}</span>
        <span className="text-foreground/80">{rest}</span>
      </>
    )
  }

  return <span className="text-foreground/80">{line}</span>
}

export function ScanLog() {
  const { scanLog } = useTradingStore()
  const bottomRef = useRef<HTMLDivElement>(null)
  const prevLengthRef = useRef(scanLog.length)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    if (scanLog.length > prevLengthRef.current) {
      scrollToBottom()
    }
    prevLengthRef.current = scanLog.length
  }, [scanLog.length, scrollToBottom])

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
          <ScrollText className="size-4 text-muted-foreground" />
          Activity Log
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="max-h-48">
          <div className="space-y-0.5 bg-secondary/50 rounded-lg border border-border p-3">
            {scanLog.map((entry, i) => (
              <div
                key={`${entry}-${i}`}
                className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-all"
              >
                {colorizeLogLine(entry)}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
