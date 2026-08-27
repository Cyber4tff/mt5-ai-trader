"use client";

import { useState, useCallback, useEffect } from "react";
import { Wifi, Loader2, Wallet, Signal } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useTradingStore } from "@/lib/trading-store";

export function ConnectionPanel() {
  const { connection, startPaperTrading, disconnect, backendAvailable, backendChecking, checkBackendHealth } = useTradingStore();

  const [balance, setBalance] = useState<string>("10000");
  const [leverage, setLeverage] = useState<string>("100");
  const [starting, setStarting] = useState(false);

  const isConnected = connection.connected;

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(() => checkBackendHealth(), 30000);
    return () => clearInterval(interval);
  }, [checkBackendHealth]);

  const handleStart = useCallback(async () => {
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
    toast.info("Disconnected from trading session");
  }, [disconnect]);

  const truncateId = (id: string) => {
    if (id.length <= 16) return id;
    return `${id.slice(0, 8)}...${id.slice(-6)}`;
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 py-4">
      <CardHeader className="px-4 md:px-6 pb-0 gap-1">
        <CardTitle className="flex items-center justify-between text-white text-sm">
          <span className="flex items-center gap-2">
            <Wallet className="size-4 text-emerald-500" />
            Paper Trading
          </span>
          <div className="flex items-center gap-1.5">
            <Signal className={`size-3 ${backendAvailable ? "text-emerald-400" : "text-red-400"}`} />
            <span className={`text-[10px] uppercase tracking-wider ${backendAvailable ? "text-emerald-400" : "text-red-400"}`}>
              {backendChecking ? "Checking..." : backendAvailable ? "Engine Online" : "Engine Offline"}
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
            <p className="text-xs text-zinc-400 leading-relaxed">
              Cloud-based trading with real market data. No MT5 or PC required. Start a paper trading session to begin analysis.
            </p>

            <div className="grid grid-cols-2 gap-4">
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
              className="w-full mt-1 font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
              disabled={starting || !backendAvailable}
              onClick={handleStart}
            >
              {starting && <Loader2 className="size-4 animate-spin" />}
              {starting ? "Starting..." : "Start Paper Trading"}
            </Button>

            {!backendAvailable && (
              <p className="text-[11px] text-amber-400/80 text-center">
                Trading engine is starting up... Please wait.
              </p>
            )}
            {backendAvailable && (
              <p className="text-[11px] text-zinc-500 text-center">
                Real market data from Yahoo Finance. Virtual positions only.
              </p>
            )}
          </motion.div>
        ) : (
          <motion.div
            className="flex flex-col gap-4"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-zinc-400 uppercase tracking-wider">Mode</span>
                <span className="text-sm text-emerald-400 font-medium">Paper Trading</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-zinc-400 uppercase tracking-wider">Server</span>
                <span className="text-sm text-white font-medium">{connection.server}</span>
              </div>
              {connection.sessionId && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-400 uppercase tracking-wider">Session ID</span>
                  <span className="text-xs text-zinc-300 font-mono">
                    {truncateId(connection.sessionId)}
                  </span>
                </div>
              )}
              {connection.lastUpdate && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-400 uppercase tracking-wider">Last Update</span>
                  <span className="text-xs text-zinc-400">
                    {new Date(connection.lastUpdate).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

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
