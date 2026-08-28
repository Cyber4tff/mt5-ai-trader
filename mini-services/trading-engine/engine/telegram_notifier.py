"""Telegram Instant Push Notification Module for Cloud Trading Engine.

Sends real-time push alerts to user's phone / iPad on Telegram when:
- Trades are executed (BUY/SELL, Symbol, Lot, Price, SL, TP)
- Positions move to Breakeven (Zero-loss lock)
- Trades close with profit / loss
- News blackout warnings trigger
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Optional


class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def configure(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    async def send_message(self, text: str) -> bool:
        """Send asynchronous Telegram message."""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, urllib.request.urlopen, req)
            return True
        except Exception as e:
            print(f"[TelegramAlert Error] Could not send message: {e}")
            return False

    async def notify_trade_opened(
        self,
        symbol: str,
        direction: str,
        volume: float,
        entry: float,
        sl: float,
        tp: float,
        broker: str = "MT5",
        ticket: Optional[int] = None,
    ):
        emoji = "🟢 BUY" if direction.upper() == "BUY" else "🔴 SELL"
        ticket_str = f"#{ticket} " if ticket else ""
        msg = (
            f"⚡ *NEW TRADE EXECUTED*\n\n"
            f"📈 *Symbol*: `{symbol}`\n"
            f"🎯 *Action*: {emoji}\n"
            f"📊 *Volume*: `{volume}` lots\n"
            f"💵 *Entry Price*: `{entry:.5f}`\n"
            f"🛑 *Stop Loss*: `{sl:.5f}`\n"
            f"🎯 *Take Profit*: `{tp:.5f}`\n"
            f"🏛 *Broker*: `{broker}` {ticket_str}\n"
            f"⏰ *Time*: 24/7 Naked Scalper AI"
        )
        await self.send_message(msg)

    async def notify_breakeven_lock(self, symbol: str, ticket: int, entry: float):
        msg = (
            f"🛡 *BREAKEVEN LOCKED (ZERO LOSS)*\n\n"
            f"📈 *Symbol*: `{symbol}` (Ticket #{ticket})\n"
            f"🔒 *New Stop Loss*: `{entry:.5f}` (Moved to Entry)\n"
            f"🎉 Trade is now completely RISK-FREE!"
        )
        await self.send_message(msg)

    async def notify_trade_closed(self, symbol: str, ticket: int, profit: float, reason: str = "TP Hit"):
        emoji = "💰" if profit >= 0 else "🔻"
        msg = (
            f"{emoji} *TRADE CLOSED*\n\n"
            f"📈 *Symbol*: `{symbol}` (Ticket #{ticket})\n"
            f"💵 *Profit/Loss*: `${profit:+.2f}`\n"
            f"📝 *Reason*: {reason}"
        )
        await self.send_message(msg)


# Global Telegram Notifier Singleton
telegram_notifier = TelegramNotifier()
