"use client";

import { useState, useCallback } from "react";
import { Wifi, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/lib/trading-store";

type AccountType = "demo" | "real";

export function ConnectionPanel() {
  const { connection, connect, disconnect, backendAvailable } = useTradingStore();

  const [broker, setBroker] = useState<string>("Exness");
  const [accountType, setAccountType] = useState<AccountType>("demo");
  const [login, setLogin] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [server, setServer] = useState<string>("");
  const [connecting, setConnecting] = useState(false);

  const isConnected = connection.connected;

  const handleConnect = useCallback(async () => {
    if (!login || !password) {
      toast.error("Login and password are required");
      return;
    }

    setConnecting(true);
    try {
      const success = await connect(
        broker.toLowerCase(),
        Number(login),
        password,
        server || undefined
      );
      if (success) {
        toast.success(`Connected to ${broker}`);
      } else {
        toast.error("Connection failed. Is the Python trading engine running?");
      }
    } catch {
      toast.error("Connection error occurred");
    } finally {
      setConnecting(false);
    }
  }, [broker, login, password, server, connect]);

  const handleDisconnect = useCallback(async () => {
    await disconnect();
    toast.info("Disconnected from broker");
  }, [disconnect]);

  const truncateId = (id: string) => {
    if (id.length <= 16) return id;
    return `${id.slice(0, 8)}...${id.slice(-6)}`;
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 py-4">
      <CardHeader className="px-4 md:px-6 pb-0 gap-1">
        <CardTitle className="flex items-center gap-2 text-white text-sm">
          <Wifi className="size-4 text-emerald-500" />
          MT5 Connection
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-zinc-400 uppercase tracking-wider">
                  Broker
                </label>
                <Select value={broker} onValueChange={setBroker}>
                  <SelectTrigger className="w-full bg-zinc-900 border-zinc-700 text-zinc-200">
                    <SelectValue placeholder="Select broker" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-700">
                    <SelectItem value="Exness">Exness</SelectItem>
                    <SelectItem value="OctaFX">OctaFX</SelectItem>
                    <SelectItem value="Headway">Headway</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-zinc-400 uppercase tracking-wider">
                  Account Type
                </label>
                <Select
                  value={accountType}
                  onValueChange={(v) => setAccountType(v as AccountType)}
                >
                  <SelectTrigger className="w-full bg-zinc-900 border-zinc-700 text-zinc-200">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-700">
                    <SelectItem value="demo">Demo</SelectItem>
                    <SelectItem value="real">Real</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-zinc-400 uppercase tracking-wider">
                Login
              </label>
              <Input
                type="number"
                placeholder="Account login ID"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-zinc-400 uppercase tracking-wider">
                Password
              </label>
              <Input
                type="password"
                placeholder="Trading password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-zinc-400 uppercase tracking-wider">
                Server <span className="normal-case text-zinc-600">(optional)</span>
              </label>
              <Input
                type="text"
                placeholder="Auto-detect from broker"
                value={server}
                onChange={(e) => setServer(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-200 placeholder:text-zinc-600"
              />
            </div>

            <Button
              className={cn(
                "w-full mt-1 font-semibold",
                accountType === "real"
                  ? "border-amber-500 text-amber-400 hover:bg-amber-500/10"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
              )}
              variant={accountType === "real" ? "outline" : "default"}
              disabled={connecting || !login || !password}
              onClick={handleConnect}
            >
              {connecting && <Loader2 className="size-4 animate-spin" />}
              {connecting ? "Connecting..." : "Connect"}
            </Button>

            <p className="text-[11px] text-zinc-500 text-center">
              {!backendAvailable
                ? "Python trading engine must be running to connect"
                : accountType === "real"
                  ? "LIVE account — real money at risk"
                  : "Demo account — safe for testing"}
            </p>
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
                <span className="text-xs text-zinc-400 uppercase tracking-wider">Broker</span>
                <span className="text-sm text-white font-medium">{connection.broker}</span>
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
            </div>

            <Button
              variant="destructive"
              className="w-full font-semibold"
              onClick={handleDisconnect}
            >
              Disconnect
            </Button>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
