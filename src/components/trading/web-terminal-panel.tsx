"use client";

import { useMemo } from "react";
import { Maximize2, Minimize2, RefreshCw, ExternalLink, Monitor } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/lib/trading-store";
import { useState, useRef, useCallback } from "react";

export function WebTerminalPanel() {
  const connection = useTradingStore((s) => s.connection);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  const isLiveMode = connection.connected && connection.mode === "live";
  const mt5Server = connection.mt5Server;

  // Build the MT5 Web Terminal URL
  const terminalUrl = useMemo(() => {
    if (!mt5Server) return "https://trade.mql5.com/trade";
    // Pre-select the server in the web terminal
    return `https://trade.mql5.com/trade?server=${encodeURIComponent(mt5Server)}`;
  }, [mt5Server]);

  const handleRefresh = useCallback(() => {
    setIframeKey((k) => k + 1);
  }, []);

  const handleOpenExternal = useCallback(() => {
    window.open(terminalUrl, "_blank", "noopener,noreferrer");
  }, [terminalUrl]);

  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen && panelRef.current) {
      if (panelRef.current.requestFullscreen) {
        panelRef.current.requestFullscreen();
      }
    } else if (document.fullscreenElement) {
      document.exitFullscreen();
    }
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  if (!isLiveMode) return null;

  return (
    <AnimatePresence>
      <motion.div
        ref={panelRef}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={`flex flex-col ${isFullscreen ? "fixed inset-0 z-[100] bg-black" : ""}`}
      >
        <Card className="bg-zinc-900/50 border-zinc-800 flex-1 flex flex-col overflow-hidden">
          <CardHeader className="px-4 md:px-6 py-3 flex-row items-center justify-between flex-shrink-0">
            <CardTitle className="flex items-center gap-2 text-white text-sm">
              <Monitor className="size-4 text-emerald-500" />
              MT5 Web Terminal
              <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-[10px] font-bold ml-2">
                LIVE
              </Badge>
              <span className="text-xs text-zinc-500 font-normal ml-2">
                {connection.broker} — {connection.server}
              </span>
            </CardTitle>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-zinc-800"
                onClick={handleRefresh}
                title="Refresh terminal"
              >
                <RefreshCw className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-zinc-800"
                onClick={handleOpenExternal}
                title="Open in new tab"
              >
                <ExternalLink className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-zinc-800"
                onClick={toggleFullscreen}
                title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              >
                {isFullscreen ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex-1 p-0 relative overflow-hidden">
            <iframe
              key={iframeKey}
              src={terminalUrl}
              className="w-full h-full border-0"
              style={{ minHeight: "600px" }}
              allow="clipboard-read; clipboard-write"
              title="MT5 Web Terminal — Live Trading"
              sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals allow-popups-to-escape-sandbox"
            />
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
