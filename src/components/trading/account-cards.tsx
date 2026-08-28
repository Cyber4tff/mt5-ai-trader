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
    getValue: (a) => `$${(a?.balance ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    getSubtext: () => "",
    colorClass: () => "text-foreground",
  },
  {
    label: "Equity",
    icon: TrendingUp,
    getValue: (a) => `$${(a?.equity ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    getSubtext: () => "",
    colorClass: () => "text-foreground",
  },
  {
    label: "Floating P&L",
    icon: DollarSign,
    getValue: (a) => {
      const p = a?.profit ?? 0;
      const sign = p >= 0 ? "+" : "";
      return `${sign}$${p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    getSubtext: (a) => {
      const b = a?.balance ?? 0;
      const p = a?.profit ?? 0;
      const pct = b > 0 ? ((p / b) * 100).toFixed(2) : "0.00";
      return `${p >= 0 ? "+" : ""}${pct}%`;
    },
    colorClass: (a) => ((a?.profit ?? 0) >= 0 ? "text-emerald-500" : "text-red-500"),
  },
  {
    label: "Margin Level",
    icon: Shield,
    getValue: (a) => `${(a?.margin_level ?? 0).toFixed(2)}%`,
    getSubtext: (a) => `$${(a?.margin ?? 0).toFixed(2)} used`,
    colorClass: (a) => ((a?.margin_level ?? 0) < 150 ? "text-red-500" : (a?.margin_level ?? 0) < 300 ? "text-amber-500" : "text-foreground"),
  },
];

function PlaceholderCard({ label, icon: Icon }: { label: string; icon: React.ElementType }) {
  return (
    <div className="p-4 rounded-xl border border-dashed border-border bg-card/50">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
        <Icon className="size-4 text-muted-foreground/60" />
      </div>
      <div className="mt-2 text-2xl font-mono font-bold text-muted-foreground/60">--</div>
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
      className="p-4 rounded-xl border border-border bg-card hover:border-muted-foreground/30 transition-colors"
      whileHover={{ scale: 1.01 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground uppercase tracking-wider">{def.label}</span>
        <Icon className="size-4 text-muted-foreground" />
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
