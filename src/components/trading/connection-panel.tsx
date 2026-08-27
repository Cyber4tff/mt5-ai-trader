"use client";

import { useState, useCallback, useEffect } from "react";
import { Wifi, Loader2, Wallet, Signal, ExternalLink, Monitor, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTradingStore } from "@/lib/trading-store";
import { BROKERS, type BrokerConfig } from "@/lib/trading-types";

export function ConnectionPanel() {
  const { connection, startPaperTrading, connectLive, disconnect, backendAvailable, backendChecking, checkBackendHealth } = useTradingStore();

  const [activeTab, setActiveTab] = useState<"live" | "paper">("live");
  const [selectedBroker, setSelectedBroker] = useState<BrokerConfig | null>(null);
  const [selectedServer, setSelectedServer] = useState<string>("");
  const [customServer, setCustomServer] = useState<string>("");
  const [balance, setBalance] = useState<string>("10000");
  const [leverage, setLeverage] = useState<string>("100");
  const [starting, setStarting] = useState(false);

  const isConnected = connection.connected;
  const isLiveMode = connection.mode === "live";

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(() => checkBackendHealth(), 30000);
    return () => clearInterval(interval);
  }, [checkBackendHealth]);

  const handleBrokerSelect = useCallback((broker: BrokerConfig) => {
    setSelectedBroker(broker);
    if (broker.servers.length > 0) {
      setSelectedServer(broker.servers[0]);
    } else {
      setSelectedServer("");
    }
    setCustomServer("");
  }, []);

  const handleLiveConnect = useCallback(async () => {
    if (!selectedBroker) {
      toast.error("Please select a broker");
      return;
    }
    const server = selectedBroker.id === "custom" ? customServer.trim() : selectedServer;
    if (!server) {
      toast.error("Please select or enter a server");
      return;
    }
    setStarting(true);
    try {
      await connectLive(selectedBroker.name, selectedBroker.id, server);
      toast.success(`Opening ${selectedBroker.name} MT5 Web Terminal`);
    } catch {
      toast.error("Failed to start AI engine");
    } finally {
      setStarting(false);
    }
  }, [selectedBroker, selectedServer, customServer, connectLive]);

  const handleStartPaper = useCallback(async () => {
    const bal = parseFloat(balance);
    const lev = parseInt(leverage, 10);

    if (isNaN(bal) || bal <= 0) {
      toast.error("Enter a valid balance amount");
      return;
    }
    if (isNaN(lev) || lev < 1) {
      toast.error("Enter a valid leverage");
      return;
    }

    setStarting(true);
    try {
      const success = await startPaperTrading(bal, lev);
      if (success) {
        toast.success(`Paper trading started with $${bal.toLocaleString()}`);
      } else {
        toast.error("Failed to start. Check if the trading engine is running.");
      }
    } catch {
      toast.error("Connection error occurred");
    } finally {
      setStarting(false);
    }
  }, [balance, leverage, startPaperTrading]);

  const handleDisconnect = useCallback(async () => {
    await disconnect();
    setSelectedBroker(null);
    setSelectedServer("");
    toast.info("Disconnected from trading session");
  }, [disconnect]);

  const truncateId = (id: string) => {
    if (!id || id.length <= 16) return id || "";
    return `${id.slice(0, 8)}...${id.slice(-6)}`;
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 py-4">
      <CardHeader className="px-4 md:px-6 pb-0 gap-1">
        <CardTitle className="flex items-center justify-between text-white text-sm">
          <span className="flex items-center gap-2">
            <Wallet className="size-4 text-emerald-500" />
            Trading Session
          </span>
          <div className="flex items-center gap-1.5">
            <Signal className={`size-3 ${backendAvailable ? "text-emerald-400" : "text-zinc-500"}`} />
            <span className={`text-[10px] uppercase tracking-wider ${backendChecking ? "text-zinc-400" : backendAvailable ? "text-emerald-400" : "text-zinc-500"}`}>
              {backendChecking ? "Checking..." : backendAvailable ? "AI Engine Online" : "AI Engine Starting"}
            </span>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="px-4 md:px-6 pt-2">
        {!isConnected ? (
          <motion.div
            className="flex flex-col gap-4"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            {/* Mode Tabs */}
            <div className="flex gap-1 p-1 bg-zinc-800/50 rounded-lg">
              <button
                onClick={() => setActiveTab("live")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  activeTab === "live"
                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Zap className="size-3.5" />
                Live Trading
              </button>
              <button
                onClick={() => setActiveTab("paper")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  activeTab === "paper"
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Monitor className="size-3.5" />
                Paper Trading
              </button>
            </div>

            <AnimatePresence mode="wait">
              {activeTab === "live" ? (
                <motion.div
                  key="live"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex flex-col gap-3"
                >
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    Connect to your real MT5 account. Select your broker, then log in directly in the MT5 Web Terminal.
                  </p>

                  {/* Broker Selection */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs text-zinc-400 uppercase tracking-wider">
                      Select Broker
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {BROKERS.filter((b) => b.id !== "custom").map((broker) => (
                        <button
                          key={broker.id}
                          onClick={() => handleBrokerSelect(broker)}
                          className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all ${
                            selectedBroker?.id === broker.id
                              ? "border-emerald-500 bg-emerald-500/10"
                              : "border-zinc-700 bg-zinc-900/50 hover:border-zinc-600 hover:bg-zinc-800/50"
                          }`}
                        >
                          <div
                            className={`size-8 rounded-full flex items-center justify-center text-sm font-bold ${
                              selectedBroker?.id === broker.id
                                ? "bg-emerald-600 text-white"
                                : "bg-zinc-800 text-zinc-400"
                            }`}
                          >
                            {broker.logo}
                          </div>
                          <span className="text-[11px] font-medium text-zinc-300">
                            {broker.name}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Custom Broker */}
                  <button
                    onClick={() => handleBrokerSelect(BROKERS.find((b) => b.id === "custom")!)}
                    className={`w-full flex items-center justify-center gap-2 py-2 rounded-lg border text-xs font-medium transition-all ${
                      selectedBroker?.id === "custom"
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                        : "border-zinc-700 bg-zinc-900/30 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300"
                    }`}
                  >
                    <ExternalLink className="size-3" />
                    Other Broker (MT5)
                  </button>

                  {/* Server Selection */}
                  {selectedBroker && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="flex flex-col gap-1.5"
                    >
                      <label className="text-xs text-zinc-400 uppercase tracking-wider">
                        MT5 Server
                      </label>
                      {selectedBroker.id !== "custom" && selectedBroker.servers.length > 0 ? (
                        <select
                          value={selectedServer}
                          onChange={(e) => setSelectedServer(e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-700 text-zinc-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        >
                          {selectedBroker.servers.map((srv) => (
                            <option key={srv} value={srv}>
                              {srv}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <Input
                          placeholder="e.g. BrokerName-MT5-Real"
                          value={customServer}
                          onChange={(e) => setCustomServer(e.target.value)}
                          className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
                        />
                      )}
                    </motion.div>
                  )}

                  <Button
                    className="w-full font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
                    disabled={!selectedBroker || (!selectedServer && !customServer.trim())}
                    onClick={handleLiveConnect}
                  >
                    <Zap className="size-4 mr-2" />
                    Connect & Open MT5 Terminal
                  </Button>

                  <p className="text-[11px] text-zinc-500 text-center">
                    Your credentials are entered directly in the MT5 Web Terminal. We never see your password.
                  </p>
                </motion.div>
              ) : (
                <motion.div
                  key="paper"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="flex flex-col gap-3"
                >
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    Practice with virtual money. Real market data from Yahoo Finance.
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs text-zinc-400 uppercase tracking-wider">
                        Balance ($)
                      </label>
                      <Input
                        type="number"
                        placeholder="10000"
                        value={balance}
                        onChange={(e) => setBalance(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs text-zinc-400 uppercase tracking-wider">
                        Leverage
                      </label>
                      <Input
                        type="number"
                        placeholder="100"
                        value={leverage}
                        onChange={(e) => setLeverage(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
                      />
                    </div>
                  </div>

                  <Button
                    className="w-full font-semibold bg-zinc-700 hover:bg-zinc-600 text-white"
                    disabled={starting || !backendAvailable}
                    onClick={handleStartPaper}
                  >
                    {starting && <Loader2 className="size-4 animate-spin" />}
                    {starting ? "Starting..." : "Start Paper Trading"}
                  </Button>

                  {!backendAvailable && (
                    <p className="text-[11px] text-amber-400/80 text-center">
                      AI engine is starting up... Please wait.
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ) : (
          <motion.div
            className="flex flex-col gap-4"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="flex items-center gap-2 mb-1">
              <Badge
                className={`text-[10px] font-bold uppercase tracking-wider ${
                  isLiveMode
                    ? "bg-red-500/20 text-red-400 border-red-500/30"
                    : "bg-amber-500/20 text-amber-400 border-amber-500/30"
                }`}
              >
                {isLiveMode ? "LIVE" : "PAPER"}
              </Badge>
              {isLiveMode && (
                <motion.div
                  className="size-2 rounded-full bg-red-500"
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-zinc-400 uppercase tracking-wider">Broker</span>
                <span className="text-sm text-white font-medium">{connection.broker}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-zinc-400 uppercase tracking-wider">Server</span>
                <span className="text-sm text-white font-medium">{connection.server}</span>
              </div>
              {isLiveMode && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-400 uppercase tracking-wider">Terminal</span>
                  <span className="text-sm text-emerald-400 font-medium">MT5 Web</span>
                </div>
              )}
              {connection.lastUpdate && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-400 uppercase tracking-wider">Connected</span>
                  <span className="text-xs text-zinc-400">
                    {new Date(connection.lastUpdate).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

            {isLiveMode && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <p className="text-[11px] text-emerald-400 leading-relaxed">
                  Your real account is connected via the MT5 Web Terminal below. Log in with your MT5 credentials to start trading.
                </p>
              </div>
            )}

            <Button
              variant="destructive"
              className="w-full font-semibold"
              onClick={handleDisconnect}
            >
              End Session
            </Button>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
