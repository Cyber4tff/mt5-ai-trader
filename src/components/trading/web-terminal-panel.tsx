"use client";

import { useState, useRef, useCallback } from "react";
import { Maximize2, Minimize2, RefreshCw, ExternalLink, Monitor, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/lib/trading-store";

export function WebTerminalPanel() {
  const connection = useTradingStore((s) => s.connection);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const isLiveMode = connection.connected && connection.mode === "live";

  // Use the pre-computed URL from the store (broker-specific, MT5-only)
  const terminalUrl = connection.webTerminalUrl || "";

  const handleRefresh = useCallback(() => {
    setLoadFailed(false);
    setIframeKey((k) => k + 1);
  }, []);

  const handleOpenExternal = useCallback(() => {
    if (terminalUrl) {
      window.open(terminalUrl, "_blank", "noopener,noreferrer");
    }
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

  if (!isLiveMode || !terminalUrl) return null;

  // Determine if this is a broker-specific URL (Headway) or generic
   const isBrokerSpecific = !terminalUrl.includes("metatraderweb.app") && !terminalUrl.includes("trade.mql5.com");

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
              MetaTrader 5 Web Terminal
              <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-[10px] font-bold ml-2">
                LIVE
              </Badge>
              <span className="text-xs text-zinc-500 font-normal ml-2">
                {connection.broker} — {connection.server}
              </span>
              {isBrokerSpecific && (
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[10px] ml-1">
                  MT5 ONLY
                </Badge>
              )}
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
                size="sm"
                variant="outline"
                className="h-8 text-xs text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                onClick={handleOpenExternal}
                title="Open in new browser tab"
              >
                <ExternalLink className="size-3 mr-1" />
                Open in Tab
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
            {/* Fallback if iframe can't load (e.g. embedded preview) */}
            {loadFailed && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-zinc-900/95 gap-4">
                <AlertTriangle className="size-10 text-amber-400" />
                <div className="text-center max-w-sm">
                  <h3 className="text-white font-semibold text-sm mb-1">
                    Terminal can't load here
                  </h3>
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    The MT5 Web Terminal needs to open in a full browser window.
                    Click below to open it in a new tab with your broker pre-selected.
                  </p>
                </div>
                <Button
                  onClick={handleOpenExternal}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6"
                >
                  <ExternalLink className="size-4 mr-2" />
                  Open MT5 Terminal
                </Button>
                <p className="text-[10px] text-zinc-500">
                  Server: <span className="text-zinc-300 font-mono">{connection.mt5Server}</span>
                </p>
              </div>
            )}

            <iframe
              key={iframeKey}
              src={terminalUrl}
              className="w-full h-full border-0"
              style={{ minHeight: "600px" }}
              allow="clipboard-read; clipboard-write"
              title="MetaTrader 5 Web Terminal — Live Trading"
              sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals allow-popups-to-escape-sandbox allow-top-navigation"
            />
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
