"""Economic News Calendar Filter for Cloud Trading Engine.

Fetches high-impact economic news events (NFP, CPI, FOMC, Rate Decisions)
and pauses trading 15 minutes before & after high-impact releases to prevent slippage.
"""

from __future__ import annotations

import asyncio
import time
import urllib.request
import json
from typing import Dict, List, Optional

# Cache news events for 1 hour
_news_cache: List[Dict] = []
_news_cache_time: float = 0.0
NEWS_CACHE_TTL = 3600  # 1 hour


class NewsFilter:
    def __init__(self, blackout_minutes_before: int = 15, blackout_minutes_after: int = 15):
        self.blackout_before = blackout_minutes_before * 60
        self.blackout_after = blackout_minutes_after * 60

    def fetch_high_impact_news(self) -> List[Dict]:
        """Fetch economic news events from free financial news endpoint."""
        global _news_cache, _news_cache_time
        now = time.time()

        if _news_cache and (now - _news_cache_time < NEWS_CACHE_TTL):
            return _news_cache

        try:
            # Free financial calendar endpoint
            url = "https://nfp-cpi-calendar.free.beacon-api.workers.dev/events"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                events = data.get("events", [])
                high_impact = [
                    e for e in events
                    if e.get("impact") in ["HIGH", "CRITICAL"] or any(k in e.get("title", "").upper() for k in ["NFP", "CPI", "FOMC", "RATE", "FED", "NON-FARM"])
                ]
                _news_cache = high_impact
                _news_cache_time = now
                return high_impact
        except Exception as e:
            print(f"[NewsFilter] Notice: News API offline or unreachable ({e}). Defaulting to normal market operation.")
            return _news_cache

    def is_news_blackout(self, symbol: str) -> tuple[bool, str]:
        """Check if trading is currently in a high-impact news blackout period."""
        now = time.time()
        events = self.fetch_high_impact_news()

        for ev in events:
            ev_time = ev.get("time_epoch", 0)
            if ev_time <= 0:
                continue

            title = ev.get("title", "High Impact News")
            currency = ev.get("currency", "")

            # Match symbol currency (e.g. USD for EURUSD/XAUUSD/BTCUSD, GBP for GBPUSD)
            if currency and currency.upper() not in symbol.upper():
                continue

            if (ev_time - self.blackout_before) <= now <= (ev_time + self.blackout_after):
                return True, f"High-Impact News Blackout: {title} ({currency})"

        return False, ""


# Singleton instance
news_filter = NewsFilter()
