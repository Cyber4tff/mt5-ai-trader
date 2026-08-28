"""Deriv WebSocket API Client for Python Trading Engine.

Supports 24/7 Forex and Synthetic Indices trading (Volatility 100/75, Boom/Crash, Jump, etc.) via Deriv WebSocket API v3.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Dict, List, Optional
import websockets

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"


class DerivClient:
    def __init__(self, api_token: Optional[str] = None, app_id: int = 1089):
        self.api_token = api_token
        self.app_id = app_id
        self.ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
        self.connected = False
        self.authorized = False
        self.account_info: Dict = {}
        self.positions: List[Dict] = []
        self._req_id = 0

    def _next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _send_and_receive(self, payload: dict, timeout: float = 10.0) -> dict:
        """Send a single JSON request over WebSocket and return the response."""
        async with websockets.connect(self.ws_url) as ws:
            req_id = self._next_req_id()
            payload["req_id"] = req_id
            await ws.send(json.dumps(payload))

            while True:
                resp_text = await asyncio.wait_for(ws.recv(), timeout=timeout)
                resp = json.loads(resp_text)
                if resp.get("req_id") == req_id or "error" in resp or resp.get("msg_type") == payload.get("msg_type"):
                    return resp

    async def connect_and_authorize(self, token: str) -> dict:
        """Connect to Deriv WebSocket and authorize with API Token."""
        self.api_token = token
        try:
            resp = await self._send_and_receive({"authorize": token})
            if "error" in resp:
                self.authorized = False
                return {"success": False, "error": resp["error"]["message"]}

            auth_data = resp.get("authorize", {})
            self.authorized = True
            self.connected = True
            self.account_info = {
                "login": auth_data.get("loginid"),
                "email": auth_data.get("email"),
                "currency": auth_data.get("currency", "USD"),
                "balance": float(auth_data.get("balance", 0.0)),
                "is_virtual": bool(auth_data.get("is_virtual", 1)),
                "account_type": "Demo" if auth_data.get("is_virtual") else "Real",
                "landing_company_name": auth_data.get("landing_company_name"),
            }
            return {"success": True, "account": self.account_info}
        except Exception as e:
            self.authorized = False
            self.connected = False
            return {"success": False, "error": str(e)}

    async def get_balance(self) -> dict:
        """Get latest Deriv account balance."""
        if not self.api_token:
            return {"success": False, "error": "No Deriv token provided"}
        try:
            async with websockets.connect(self.ws_url) as ws:
                await ws.send(json.dumps({"authorize": self.api_token}))
                auth_resp = json.loads(await ws.recv())
                if "error" in auth_resp:
                    return {"success": False, "error": auth_resp["error"]["message"]}

                await ws.send(json.dumps({"balance": 1}))
                bal_resp = json.loads(await ws.recv())
                if "error" in bal_resp:
                    return {"success": False, "error": bal_resp["error"]["message"]}

                balance_data = bal_resp.get("balance", {})
                self.account_info["balance"] = float(balance_data.get("balance", 0.0))
                return {"success": True, "balance": self.account_info["balance"], "currency": balance_data.get("currency")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def fetch_candles(self, symbol: str, granularity: int = 900, count: int = 100) -> Optional[List[Dict]]:
        """Fetch OHLC candles from Deriv (granularity in seconds: 60=1m, 300=5m, 900=15m, 3600=1h, 86400=1d)."""
        try:
            payload = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "style": "candles",
                "granularity": granularity,
            }
            resp = await self._send_and_receive(payload)
            if "error" in resp:
                print(f"[Deriv] Candle fetch error for {symbol}: {resp['error']['message']}")
                return None
            candles = resp.get("candles", [])
            return [
                {
                    "time": c["epoch"],
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                }
                for c in candles
            ]
        except Exception as e:
            print(f"[Deriv] Exception fetching candles for {symbol}: {e}")
            return None

    async def execute_trade(
        self,
        symbol: str,
        direction: str,  # "BUY" (CALL/MULTUP) or "SELL" (PUT/MULTDOWN)
        amount: float = 10.0,
        duration: int = 15,
        duration_unit: str = "m",  # "m" for minutes, "h" for hours, "d" for days
    ) -> dict:
        """Place a trade contract on Deriv."""
        if not self.api_token:
            return {"success": False, "error": "Deriv API Token required to place live trades."}

        contract_type = "CALL" if direction.upper() == "BUY" else "PUT"
        try:
            async with websockets.connect(self.ws_url) as ws:
                # 1. Authorize
                await ws.send(json.dumps({"authorize": self.api_token}))
                auth_resp = json.loads(await ws.recv())
                if "error" in auth_resp:
                    return {"success": False, "error": auth_resp["error"]["message"]}

                # 2. Request Contract Proposal
                proposal_req = {
                    "proposal": 1,
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": self.account_info.get("currency", "USD"),
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol,
                }
                await ws.send(json.dumps(proposal_req))
                prop_resp = json.loads(await ws.recv())
                if "error" in prop_resp:
                    return {"success": False, "error": prop_resp["error"]["message"]}

                proposal_id = prop_resp.get("proposal", {}).get("id")
                proposal_ask = prop_resp.get("proposal", {}).get("ask_price", amount)

                # 3. Execute Buy Contract
                buy_req = {"buy": proposal_id, "price": proposal_ask}
                await ws.send(json.dumps(buy_req))
                buy_resp = json.loads(await ws.recv())
                if "error" in buy_resp:
                    return {"success": False, "error": buy_resp["error"]["message"]}

                buy_info = buy_resp.get("buy", {})
                contract_id = buy_info.get("contract_id")
                purchase_price = buy_info.get("buy_price")

                return {
                    "success": True,
                    "contract_id": contract_id,
                    "symbol": symbol,
                    "direction": direction,
                    "amount": purchase_price,
                    "balance_after": buy_info.get("balance_after"),
                    "longcode": buy_info.get("longcode"),
                }
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}


# Global Deriv Singleton
deriv_client = DerivClient()
