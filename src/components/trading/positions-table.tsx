'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { List, ShieldOff, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useTradingStore } from '@/lib/trading-store';
import type { Position } from '@/lib/trading-types';

function formatPrice(price: number, symbol: string) {
  if (symbol.includes('XAU')) return price.toFixed(2);
  if (symbol.includes('BTC')) return price.toFixed(2);
  return price.toFixed(5);
}

function formatPnl(profit: number) {
  const sign = profit >= 0 ? '+' : '';
  return `${sign}$${profit.toFixed(2)}`;
}

function PositionRow({ position, index }: { position: Position; index: number }) {
  const closePosition = useTradingStore((s) => s.closePosition);
  const [closing, setClosing] = useState(false);

  const isBuy = position.type === 'BUY';
  const pnlColor = position.profit >= 0 ? 'text-emerald-500' : 'text-red-500';

  const handleClose = useCallback(async () => {
    setClosing(true);
    try {
      await closePosition(position.ticket);
      toast.success(`Closed ${position.symbol} ${position.type} #${position.ticket}`, {
        description: `P&L: ${formatPnl(position.profit)}`,
      });
    } catch {
      toast.error('Failed to close position', {
        description: `Ticket #${position.ticket}`,
      });
    } finally {
      setClosing(false);
    }
  }, [closePosition, position]);

  return (
    <motion.tr
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 12 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
      className={cn(
        'border-b border-zinc-800/50 transition-colors hover:bg-zinc-800/30',
        index % 2 === 1 && 'bg-zinc-900/30'
      )}
    >
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">{position.symbol}</span>
          <Badge
            className={cn(
              'text-[10px] px-1.5 py-0 font-bold',
              isBuy
                ? 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
                : 'bg-red-500/15 text-red-500 border-red-500/30'
            )}
            variant="outline"
          >
            {position.type}
          </Badge>
        </div>
      </td>

      <td className="px-3 py-2.5">
        <Badge variant="secondary" className="text-[10px]">
          {position.type}
        </Badge>
      </td>

      <td className="px-3 py-2.5 font-mono text-xs tabular-nums">
        {position.volume.toFixed(2)}
      </td>

      <td className="px-3 py-2.5 font-mono text-xs tabular-nums text-muted-foreground hidden md:table-cell">
        {formatPrice(position.open_price, position.symbol)}
      </td>

      <td className="px-3 py-2.5 font-mono text-sm tabular-nums">
        {formatPrice(position.current_price, position.symbol)}
      </td>

      <td className="px-3 py-2.5 font-mono text-xs tabular-nums text-muted-foreground hidden md:table-cell">
        {formatPrice(position.sl, position.symbol)}
      </td>

      <td className="px-3 py-2.5 font-mono text-xs tabular-nums text-muted-foreground hidden md:table-cell">
        {formatPrice(position.tp, position.symbol)}
      </td>

      <td className={cn('px-3 py-2.5 font-mono text-sm tabular-nums font-bold', pnlColor)}>
        {formatPnl(position.profit)}
      </td>

      <td className="px-3 py-2.5">
        <Button
          variant="destructive"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={handleClose}
          disabled={closing}
        >
          {closing ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <X className="size-3" />
          )}
        </Button>
      </td>
    </motion.tr>
  );
}

export function PositionsTable() {
  const positions = useTradingStore((s) => s.positions);

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 gap-4">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <List className="size-4 text-blue-400" />
          Open Positions
          <Badge variant="secondary" className="ml-auto text-xs tabular-nums">
            {positions.length}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0">
        <ScrollArea className="max-h-80 overflow-y-auto">
          {positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 px-6 text-center">
              <ShieldOff className="size-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                No open positions. System defaults to NO TRADE.
              </p>
            </div>
          ) : (
            <div className="min-w-[640px]">
              <table className="w-full text-left">
                <thead className="sticky top-0 z-10 bg-zinc-950/90 backdrop-blur-sm">
                  <tr className="border-b border-zinc-800">
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium">
                      Symbol
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium">
                      Type
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium">
                      Volume
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium hidden md:table-cell">
                      Open Price
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium">
                      Current
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium hidden md:table-cell">
                      SL
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium hidden md:table-cell">
                      TP
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium">
                      P&L
                    </th>
                    <th className="px-3 py-2 text-xs uppercase text-muted-foreground tracking-wider font-medium w-12">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {positions.map((pos, i) => (
                      <PositionRow key={pos.ticket} position={pos} index={i} />
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
