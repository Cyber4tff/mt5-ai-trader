"use client"

import { motion, AnimatePresence } from "framer-motion"
import { TrendingUp } from "lucide-react"

export function LaunchScreen({ visible }: { visible: boolean }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="launch"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="fixed inset-0 z-[200] bg-zinc-950 flex flex-col items-center justify-center"
        >
          {/* Background grid pattern */}
          <div className="absolute inset-0 opacity-[0.03]">
            <div
              className="w-full h-full"
              style={{
                backgroundImage:
                  "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
                backgroundSize: "40px 40px",
              }}
            />
          </div>

          {/* Glow effect behind logo */}
          <motion.div
            className="absolute w-40 h-40 rounded-full"
            style={{ background: "radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%)" }}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1.5, opacity: 1 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />

          {/* Logo container */}
          <motion.div
            className="relative flex flex-col items-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {/* Logo icon */}
            <motion.div
              className="size-20 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-6"
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ duration: 0.8, delay: 0.3, type: "spring", stiffness: 120, damping: 12 }}
            >
              <TrendingUp className="size-10 text-emerald-500" />
            </motion.div>

            {/* Title */}
            <motion.h1
              className="text-3xl font-bold tracking-tight text-white mb-2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.7 }}
            >
              Cloud AI Trader
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              className="text-sm text-zinc-500 tracking-widest uppercase"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.9 }}
            >
              MT5 Live & Paper Trading
            </motion.p>
          </motion.div>

          {/* Loading bar */}
          <motion.div
            className="mt-12 w-64 h-0.5 bg-zinc-800 rounded-full overflow-hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: 1.1 }}
          >
            <motion.div
              className="h-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-emerald-500 rounded-full"
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: 1.5, delay: 1.2, ease: "easeInOut" }}
            />
          </motion.div>

          {/* Loading text */}
          <motion.p
            className="mt-4 text-xs text-zinc-600"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0.5, 1] }}
            transition={{ duration: 2, delay: 1.3 }}
          >
            Initializing trading engine...
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
