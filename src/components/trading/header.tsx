"use client";

import { useTheme } from "next-themes";
import { useState, useEffect } from "react";
import { TrendingUp, Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/lib/trading-store";

export function Header() {
  const { theme, setTheme } = useTheme();
  const { connection, demoMode } = useTradingStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isConnected = connection.connected;
  const brokerName = connection.broker ?? "Exness";

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
          MT5 AI Trader v2.0
        </span>
      </div>

      {/* Center: Connection Status */}
      <div className="hidden sm:flex items-center gap-2">
        <motion.div
          className={cn(
            "size-2 rounded-full",
            isConnected ? "bg-green-500" : "bg-red-500"
          )}
          animate={
            isConnected
              ? { scale: [1, 1.4, 1], opacity: [1, 0.6, 1] }
              : undefined
          }
          transition={
            isConnected
              ? { duration: 2, repeat: Infinity, ease: "easeInOut" }
              : undefined
          }
        />
        <span className="text-xs text-zinc-400">
          {isConnected
            ? `Connected to ${brokerName}`
            : "Disconnected"}
        </span>
      </div>

      {/* Right: Mode Badge + Theme Toggle */}
      <div className="flex items-center gap-3">
        <Badge
          className={cn(
            "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5",
            demoMode
              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
              : "bg-red-500/20 text-red-400 border-red-500/30"
          )}
        >
          {demoMode ? "Demo Mode" : "Live"}
        </Badge>

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
