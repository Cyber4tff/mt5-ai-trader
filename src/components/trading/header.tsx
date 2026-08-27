"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { TrendingUp, Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/lib/trading-store";

export function Header() {
  const { theme, setTheme } = useTheme();
  const { connection } = useTradingStore();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const isConnected = connection.connected;
  const brokerName = connection.broker ?? "Not connected";
  const isLiveMode = connection.mode === "live";
  const isPaperMode = connection.mode === "paper";

  return (
    <header
      className={cn(
        "sticky top-0 z-50 h-14 flex items-center justify-between px-4 md:px-6",
        "bg-zinc-950 text-white border-b border-zinc-800"
      )}
    >
      {/* Left: Logo */}
      <div className="flex items-center gap-2">
        <TrendingUp className="size-5 text-emerald-500" />
        <span className="text-sm font-semibold tracking-tight">
          Cloud AI Trader
        </span>
      </div>

      {/* Center: Connection Status */}
      <div className="hidden sm:flex items-center gap-2">
        {isConnected && isLiveMode && (
          <motion.div
            className="size-2 rounded-full bg-red-500"
            animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {isConnected && !isLiveMode && (
          <motion.div
            className="size-2 rounded-full bg-green-500"
            animate={{ scale: [1, 1.4, 1], opacity: [1, 0.6, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {!isConnected && (
          <div className="size-2 rounded-full bg-zinc-600" />
        )}
        <span className="text-xs text-zinc-400">
          {isConnected
            ? `${brokerName} — ${isLiveMode ? "Live" : "Paper"}`
            : "Disconnected"}
        </span>
      </div>

      {/* Right: Mode Badge + Theme Toggle */}
      <div className="flex items-center gap-3">
        {isConnected && (
          <Badge
            className={cn(
              "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5",
              isLiveMode
                ? "bg-red-500/20 text-red-400 border-red-500/30"
                : "bg-amber-500/20 text-amber-400 border-amber-500/30"
            )}
          >
            {isLiveMode ? "LIVE" : "PAPER"}
          </Badge>
        )}

        {mounted && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-zinc-800"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? (
              <Sun className="size-4" />
            ) : (
              <Moon className="size-4" />
            )}
          </Button>
        )}
      </div>
    </header>
  );
}
