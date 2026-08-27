"use client";

import { useEffect, useCallback, useRef } from "react";
import { Wallet, TrendingUp, DollarSign, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useTradingStore } from "@/lib/trading-store";
import type { AccountInfo } from "@/lib/trading-types";

interface MetricCard {
  label: string;
  icon: React.ElementType;
  getValue: (account: AccountInfo) => string;
  getSubtext: (account: AccountInfo) => string;
  colorClass: (account: AccountInfo) => string;
}

const metricDefs: MetricCard[] = [
  {
    label: "Balance",
    icon: Wallet,
    getValue: (a) => `$${a.balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    getSubtext: () => "",
    colorClass: () => "text-white",
  },
  {
    label: "Equity",
    icon: TrendingUp,
    getValue: (a) => `$${a.equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    getSubtext: () => "",
    colorClass: () => "text-white",
  },
  {
    label: "Floating P&L",
    icon: DollarSign,
    getValue: (a) => {
      const sign = a.profit >= 0 ? "+" : "";
      return `${sign}$${a.profit.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    getSubtext: (a) => {
      const pct = a.balance > 0 ? ((a.profit / a.balance) * 100).toFixed(2) : "0.00";
      return `${a.profit >= 0 ? "+" : ""}${pct}%`;
    },
    colorClass: (a) => (a.profit >= 0 ? "text-emerald-500" : "text-red-500"),
  },
  {
    label: "Margin Level",
    icon: Shield,
    getValue: (a) => `${a.margin_level.toFixed(2)}%`,
    getSubtext: (a) => `$${a.margin.toFixed(2)} used`,
    colorClass: (a) => (a.margin_level < 150 ? "text-red-500" : a.margin_level < 300 ? "text-amber-400" : "text-white"),
  },
];

function PlaceholderCard({ label, icon: Icon }: { label: string; icon: React.ElementType }) {
  return (
    <div className="p-4 rounded-xl border border-dashed border-zinc-700 bg-zinc-900/30">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500 uppercase tracking-wider">{label}</span>
        <Icon className="size-4 text-zinc-600" />
      </div>
      <div className="mt-2 text-2xl font-mono font-bold text-zinc-600">--</div>
    </div>
  );
}

function ActiveCard({ def, account }: { def: MetricCard; account: AccountInfo }) {
  const Icon = def.icon;
  const value = def.getValue(account);
  const subtext = def.getSubtext(account);
  const colorClass = def.colorClass(account);
  return (
    <motion.div
      className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 transition-colors"
      whileHover={{ scale: 1.01 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400 uppercase tracking-wider">{def.label}</span>
        <Icon className="size-4 text-zinc-500" />
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <motion.span
          key={value}
          className={cn("text-2xl font-mono font-bold", colorClass)}
          initial={{ y: 6, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -6, opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {value}
        </motion.span>
        {subtext && (
          <span className={cn("text-xs font-mono", colorClass)}>{subtext}</span>
        )}
      </div>
    </motion.div>
  );
}

export function AccountCards() {
  const { connection, fetchAccount } = useTradingStore();
  const { connected, account } = connection;
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = setInterval(() => {
      fetchAccount();
    }, 3000);
  }, [fetchAccount]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (connected) {
      fetchAccount();
      startPolling();
    } else {
      stopPolling();
    }
    return stopPolling;
  }, [connected, fetchAccount, startPolling, stopPolling]);

  return (
    <div className="grid grid-cols-2 gap-4">
      {metricDefs.map((def) =>
        connected && account ? (
          <ActiveCard key={def.label} def={def} account={account} />
        ) : (
          <PlaceholderCard key={def.label} label={def.label} icon={def.icon} />
        )
      )}
    </div>
  );
}
