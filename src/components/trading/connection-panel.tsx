"use client";

import { useState, useCallback, useEffect } from "react";
import { Wifi, Loader2, Wallet, Signal, ExternalLink, Monitor, Zap, CheckCircle2, Unplug } from "lucide-react";
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
import { Separator } from "@/components/ui/separator";
import { useTradingStore } from "@/lib/trading-store";
import { BROKERS, type BrokerConfig } from "@/lib/trading-types";

export function ConnectionPanel() {
  const {
    connection, liveState,
    startPaperTrading, connectLive, disconnect,
    confirmMT5Connection, unconfirmMT5Connection,
    backendAvailable, backendChecking, checkBackendHealth
  } = useTradingStore();

  const [activeTab, setActiveTab] = useState<"live" | "paper">("live");
  const [selectedBroker, setSelectedBroker] = useState<BrokerConfig | null>(null);
  const [selectedServer, setSelectedServer] = useState<string>("");
  const [customServer, setCustomServer] = useState<string>("");
  const [balance, setBalance] = useState<string>("10000");
  const [leverage, setLeverage] = useState<string>("100");
  const [starting, setStarting] = useState(false);
  const [confirmStep, setConfirmStep] = useState(false);
  const [confirmBalance, setConfirmBalance] = useState("");

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
    setConfirmStep(false);
    try {
      await connectLive(selectedBroker.name, selectedBroker.id, server);
      toast.success(`Opening ${selectedBroker.name} MT5 Web Terminal`);
    } catch {
      toast.error("Failed to start AI engine");
    } finally {
      setStarting(false);
    }
  }, [selectedBroker, selectedServer, customServer, connectLive]);

  const handleConfirmMT5 = useCallback(() => {
    confirmMT5Connection(confirmBalance);
    setConfirmStep(false);
    toast.success("MT5 connection confirmed! Auto-trading is now available.");
  }, [confirmMT5Connection, confirmBalance]);

  const handleUnconfirmMT5 = useCallback(() => {
    unconfirmMT5Connection();
    toast.info("MT5 connection unconfirmed.");
  }, [unconfirmMT5Connection]);

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
    setConfirmStep(false);
    toast.info("Disconnected from trading session");
  }, [disconnect]);

  return (
    <Card className="bg-card border-border py-4">
      <CardHeader className="px-4 md:px-6 pb-0 gap-1">
        <CardTitle className="flex items-center justify-between text-foreground text-sm">
          <span className="flex items-center gap-2">
            <Wallet className="size-4 text-emerald-500" />
            Trading Session
          </span>
          <div className="flex items-center gap-1.5">
            <Signal className={`size-3 ${backendAvailable ? "text-emerald-500 dark:text-emerald-400" : "text-muted-foreground"}`} />
            <span className={`text-[10px] uppercase tracking-wider ${backendChecking ? "text-muted-foreground" : backendAvailable ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"}`}>
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
            <div className="flex gap-1 p-1 bg-muted rounded-lg">
              <button
                onClick={() => setActiveTab("live")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  activeTab === "live"
                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Zap className="size-3.5" />
                Live Trading
              </button>
              <button
                onClick={() => setActiveTab("paper")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  activeTab === "paper"
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:text-foreground"
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
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Connect to your real MT5 account. Select your broker, then log in directly in the MT5 Web Terminal.
                  </p>

                  {/* Broker Selection */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs text-muted-foreground uppercase tracking-wider">
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
                              : "border-border bg-card hover:border-muted-foreground/30 hover:bg-accent/50"
                          }`}
                        >
                          <div
                            className={`size-8 rounded-full flex items-center justify-center text-sm font-bold ${
                              selectedBroker?.id === broker.id
                                ? "bg-emerald-600 text-white"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {broker.logo}
                          </div>
                          <span className="text-[11px] font-medium text-foreground">
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
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "border-border bg-card text-muted-foreground hover:border-muted-foreground/30 hover:text-foreground"
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
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        MT5 Server
                      </label>
                      {selectedBroker.id !== "custom" && selectedBroker.servers.length > 0 ? (
                        <select
                          value={selectedServer}
                          onChange={(e) => setSelectedServer(e.target.value)}
                          className="w-full bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
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
                          className="bg-background border-border text-foreground placeholder:text-muted-foreground"
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

                  <p className="text-[11px] text-muted-foreground text-center">
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
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Practice with virtual money. Real market data from Yahoo Finance.
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Balance ($)
                      </label>
                      <Input
                        type="number"
                        placeholder="10000"
                        value={balance}
                        onChange={(e) => setBalance(e.target.value)}
                        className="bg-background border-border text-foreground placeholder:text-muted-foreground"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs text-muted-foreground uppercase tracking-wider">
                        Leverage
                      </label>
                      <Input
                        type="number"
                        placeholder="100"
                        value={leverage}
                        onChange={(e) => setLeverage(e.target.value)}
                        className="bg-background border-border text-foreground placeholder:text-muted-foreground"
                      />
                    </div>
                  </div>

                  <Button
                    className="w-full font-semibold bg-secondary hover:bg-secondary/80 text-foreground"
                    disabled={starting || !backendAvailable}
                    onClick={handleStartPaper}
                  >
                    {starting && <Loader2 className="size-4 animate-spin" />}
                    {starting ? "Starting..." : "Start Paper Trading"}
                  </Button>

                  {!backendAvailable && (
                    <p className="text-[11px] text-amber-600 dark:text-amber-400 text-center">
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
                    ? "bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30"
                    : "bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30"
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
              {liveState.mt5Confirmed && (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[10px]">
                  <CheckCircle2 className="size-2.5 mr-0.5" /> MT5 CONNECTED
                </Badge>
              )}
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Broker</span>
                <span className="text-sm text-foreground font-medium">{connection.broker}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Server</span>
                <span className="text-sm text-foreground font-medium">{connection.server}</span>
              </div>
              {isLiveMode && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Terminal</span>
                  <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">MT5 Web</span>
                </div>
              )}
              {connection.lastUpdate && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Connected</span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(connection.lastUpdate).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

            {isLiveMode && !liveState.mt5Confirmed && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <p className="text-[11px] text-amber-600 dark:text-amber-400 leading-relaxed mb-2">
                  After logging into the MT5 terminal below, confirm your connection here to enable AI auto-trading.
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1 h-8 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                    onClick={() => setConfirmStep(true)}
                  >
                    <CheckCircle2 className="size-3 mr-1" />
                    Confirm MT5 Connected
                  </Button>
                </div>
              </div>
            )}

            {isLiveMode && liveState.mt5Confirmed && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                      MT5 Account Connected
                    </p>
                    {liveState.manualBalance && (
                      <p className="text-lg font-bold font-mono text-foreground mt-0.5">
                        ${parseFloat(liveState.manualBalance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-muted-foreground"
                    onClick={handleUnconfirmMT5}
                  >
                    <Unplug className="size-3 mr-1" />
                    Disconnect MT5
                  </Button>
                </div>
              </div>
            )}

            {isLiveMode && (
              <div className="p-3 rounded-lg bg-muted/50 border border-border">
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Your real account is connected via the MT5 Web Terminal below. Log in with your MT5 credentials to start trading.
                </p>
              </div>
            )}

            {/* Confirm MT5 Connection Modal */}
            <AnimatePresence>
              {confirmStep && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-3 rounded-lg bg-card border border-emerald-500/30 space-y-3">
                    <p className="text-xs text-foreground font-medium">
                      Confirm MT5 Connection
                    </p>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      Have you successfully logged into the MT5 Web Terminal below? Enter your account balance to confirm.
                    </p>
                    <Input
                      type="number"
                      placeholder="Enter your account balance (e.g. 14984.75)"
                      value={confirmBalance}
                      onChange={(e) => setConfirmBalance(e.target.value)}
                      className="bg-background border-border text-foreground placeholder:text-muted-foreground"
                    />
                    <div className="flex gap-2">
                      <Button
                        className="flex-1 h-8 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                        onClick={handleConfirmMT5}
                      >
                        <CheckCircle2 className="size-3 mr-1" />
                        Confirm
                      </Button>
                      <Button
                        variant="outline"
                        className="flex-1 h-8 border-border text-xs"
                        onClick={() => setConfirmStep(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

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
