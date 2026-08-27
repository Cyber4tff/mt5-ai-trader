"use client"

import { useEffect, useRef, useCallback } from "react"
import { ScrollText } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useTradingStore } from "@/lib/trading-store"
import { cn } from "@/lib/utils"

function colorizeLogLine(line: string): React.ReactNode {
  if (line.includes("ACTIONABLE")) {
    return <span className="text-emerald-400">{line}</span>
  }
  if (line.toLowerCase().includes("rejected")) {
    return <span className="text-amber-400">{line}</span>
  }
  if (line.toLowerCase().includes("error")) {
    return <span className="text-red-400">{line}</span>
  }
  if (line.includes("NO TRADE")) {
    return <span className="text-zinc-500">{line}</span>
  }

  // Split into timestamp + message
  const tsMatch = line.match(/^(\[\d{2}:\d{2}:\d{2}(?: [AP]M)?])/)
  if (tsMatch) {
    const ts = tsMatch[1]
    const rest = line.slice(ts.length)
    return (
      <>
        <span className="text-zinc-600">{ts}</span>
        <span className="text-zinc-300">{rest}</span>
      </>
    )
  }

  return <span className="text-zinc-300">{line}</span>
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
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-300">
          <ScrollText className="size-4 text-zinc-400" />
          Activity Log
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="max-h-48">
          <div className="space-y-0.5 bg-zinc-950/80 rounded-lg border border-zinc-800/50 p-3">
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
