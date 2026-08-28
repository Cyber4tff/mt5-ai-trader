"use client";

import { useState, useRef, useCallback } from "react";
import { Maximize2, Minimize2, RefreshCw, ExternalLink, Monitor, AlertTriangle, Info, ShieldCheck, WifiOff } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/lib/trading-store";

export function WebTerminalPanel() {
  const connection = useTradingStore((s) => s.connection);
  const liveState = useTradingStore((s) => s.liveState);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showEmbed, setShowEmbed] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const isLiveMode = connection.connected && connection.mode === "live";
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
        <Card className="bg-card border-border flex-1 flex flex-col overflow-hidden">
          <CardHeader className="px-4 md:px-6 py-3 flex-row items-center justify-between flex-shrink-0">
            <CardTitle className="flex items-center gap-2 text-foreground text-sm">
              <Monitor className="size-4 text-emerald-500" />
              MetaTrader 5 Web Terminal
              <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30 text-[10px] font-bold ml-2">
                LIVE
              </Badge>
              {liveState.mt5Confirmed && (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[10px] ml-1">
                  CONNECTED
                </Badge>
              )}
              <span className="text-xs text-muted-foreground font-normal ml-2">
                {connection.broker} — {connection.server}
              </span>
              {isBrokerSpecific && (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[10px] ml-1">
                  MT5 ONLY
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent"
                onClick={() => setShowHelp(!showHelp)}
                title="Troubleshooting help"
              >
                <Info className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent"
                onClick={handleRefresh}
                title="Refresh terminal"
              >
                <RefreshCw className="size-3.5" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                onClick={handleOpenExternal}
                title="Open in new browser tab"
              >
                <ExternalLink className="size-3 mr-1" />
                Open in Tab
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent"
                onClick={toggleFullscreen}
                title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              >
                {isFullscreen ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex-1 p-0 relative overflow-hidden">
            {/* Error 10 Troubleshooting Guide */}
            <AnimatePresence>
              {showHelp && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="absolute inset-x-0 top-0 z-20 bg-card border-b border-border overflow-hidden"
                >
                  <div className="p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="size-4 text-amber-500" />
                      <h3 className="text-sm font-semibold text-foreground">Troubleshooting Connection Issues</h3>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="ml-auto h-6 text-xs text-muted-foreground"
                        onClick={() => setShowHelp(false)}
                      >
                        Close
                      </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <WifiOff className="size-3.5 text-red-500" />
                          <span className="font-semibold text-red-600 dark:text-red-400">Error 10 — No Connection</span>
                        </div>
                        <p className="text-muted-foreground leading-relaxed">
                          The MT5 terminal cannot reach the broker&apos;s trade server. This is a network/connectivity issue on MetaTrader&apos;s side, not our platform.
                        </p>
                        <ul className="mt-2 space-y-1 text-muted-foreground">
                          <li>• Try clicking &quot;Open in Tab&quot; — the terminal may work better in a full browser tab</li>
                          <li>• Check your internet connection is stable</li>
                          <li>• Try again later — broker servers may be temporarily down</li>
                          <li>• Verify your broker credentials are correct</li>
                          <li>• Clear your browser cache and cookies</li>
                        </ul>
                      </div>

                      <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <ShieldCheck className="size-3.5 text-emerald-500" />
                          <span className="font-semibold text-emerald-600 dark:text-emerald-400">Best Practice</span>
                        </div>
                        <p className="text-muted-foreground leading-relaxed">
                          For the most reliable experience, we recommend opening the MT5 terminal in a separate browser tab.
                        </p>
                        <ul className="mt-2 space-y-1 text-muted-foreground">
                          <li>• Click &quot;Open in Tab&quot; button above</li>
                          <li>• Log in with your MT5 credentials there</li>
                          <li>• Come back here and click &quot;Confirm MT5 Connected&quot; in the sidebar</li>
                          <li>• AI signals will then be available for you to trade manually</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Embedded Terminal Frame or Safe Gateway Card */}
            {!showEmbed ? (
              <div className="p-6 md:p-8 flex flex-col items-center justify-center text-center space-y-4 bg-gradient-to-b from-card to-secondary/30 min-h-[400px]">
                <div className="size-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-1">
                  <Monitor className="size-8 text-emerald-500" />
                </div>
                <div className="max-w-md space-y-2">
                  <h3 className="text-lg font-bold text-foreground tracking-tight">
                    {connection.broker} Web Terminal Gateway
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Server: <span className="font-mono text-emerald-400 font-semibold">{connection.server}</span>
                  </p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    To connect your MT5 account securely on mobile/iPad without browser blocking, launch the terminal in a clean tab below.
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                  <Button
                    onClick={handleOpenExternal}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 shadow-lg shadow-emerald-600/20"
                    size="lg"
                  >
                    <ExternalLink className="size-4 mr-2" />
                    Launch MT5 Web Terminal
                  </Button>

                  <Button
                    onClick={() => setShowEmbed(true)}
                    variant="outline"
                    className="border-border text-foreground hover:bg-accent text-xs"
                    size="lg"
                  >
                    Try Embedded View
                  </Button>
                </div>

                <div className="pt-4 border-t border-border/50 max-w-sm text-center">
                  <p className="text-[11px] text-muted-foreground">
                    💡 After logging into MT5 in the terminal window, return here and enter your MT5 Account # in the sidebar to enable 24/7 autonomous auto-trading.
                  </p>
                </div>
              </div>
            ) : (
              <iframe
                key={iframeKey}
                src={terminalUrl}
                className="w-full h-full border-0"
                style={{ minHeight: "600px" }}
                allow="clipboard-read; clipboard-write; autoplay; camera; microphone"
                title="MetaTrader 5 Web Terminal — Live Trading"
                onError={() => setLoadFailed(true)}
              />
            )}
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
