"""
Bot trading demo untuk Deriv (binary options RISE/FALL).

PENTING - BACA DULU:
- Bot ini didesain untuk akun DEMO. Trading options/binary punya risiko
  kehilangan modal yang tinggi dan bukan ini bukan strategi investasi yang
  terbukti profit jangka panjang. Jangan jalankan di akun real tanpa paham
  risikonya sepenuhnya.
- Ini bukan saran finansial. Kamu bertanggung jawab penuh atas keputusan
  trading kamu sendiri.

Cara pakai:
1. cp .env.example .env, lalu isi DERIV_API_TOKEN dengan token akun DEMO kamu
2. pip install -r requirements.txt
3. python deriv_bot.py
4. Buka dashboard: python dashboard.py (di terminal terpisah), lalu buka http://localhost:5000
"""
import asyncio
import json
import sys
import websockets

from config import (
    DERIV_API_TOKEN, APP_ID, SYMBOL, STAKE, DURATION, DURATION_UNIT,
    STRATEGY_MODE, DAILY_LOSS_LIMIT, DAILY_PROFIT_LIMIT,
    ENABLE_DAILY_LIMITS,
)
from strategy import SmaCrossoverStrategy
from trade_logger import log_open_trade, log_close_trade, get_today_pl
from dataset_logger import log_tick
import indicators as ind
from deriv_auth import get_demo_ws_url


def build_strategy():
    if STRATEGY_MODE == "AI":
        from ai_strategy import AiStrategy
        print("Mode: AI (pakai model.pkl)")
        return AiStrategy()
    print("Mode: SMA (rule-based)")
    return SmaCrossoverStrategy()


class DerivBot:
    def __init__(self):
        self.strategy = build_strategy()
        self.ws = None
        self.req_id = 0
        self.pending = {}  # req_id -> asyncio.Future
        self.open_contracts = {}  # contract_id -> entry info

    def _next_id(self):
        self.req_id += 1
        return self.req_id

    async def send(self, payload):
        rid = self._next_id()
        payload["req_id"] = rid
        fut = asyncio.get_event_loop().create_future()
        self.pending[rid] = fut
        await self.ws.send(json.dumps(payload))
        return await fut

    async def subscribe_ticks(self):
        await self.ws.send(json.dumps({
            "ticks": SYMBOL,
            "subscribe": 1,
            "req_id": self._next_id(),
        }))

    async def buy_contract(self, direction, price):
        """direction: 'CALL' or 'PUT'"""
        proposal = {
            "buy": 1,
            "price": STAKE,
            "parameters": {
                "amount": STAKE,
                "basis": "stake",
                "contract_type": direction,
                "currency": "USD",
                "duration": DURATION,
                "duration_unit": DURATION_UNIT,
                "symbol": SYMBOL,
            },
        }
        res = await self.send(proposal)
        if "error" in res:
            print(f"Gagal buy: {res['error'].get('message')}")
            return
        buy = res.get("buy", {})
        contract_id = buy.get("contract_id")
        print(f"[TRADE] {direction} {SYMBOL} stake={STAKE} @ {price} -> contract {contract_id}")
        log_open_trade(contract_id, SYMBOL, direction, STAKE, price)
        self.open_contracts[contract_id] = True
        await self.subscribe_contract(contract_id)

    async def subscribe_contract(self, contract_id):
        await self.ws.send(json.dumps({
            "proposal_open_contract": 1,
            "contract_id": contract_id,
            "subscribe": 1,
            "req_id": self._next_id(),
        }))

    async def handle_message(self, msg):
        data = json.loads(msg)

        if "req_id" in data and data["req_id"] in self.pending:
            fut = self.pending.pop(data["req_id"])
            if not fut.done():
                fut.set_result(data)
            # tick/contract subscriptions also carry req_id but we still want
            # to process them below, so don't return here

        msg_type = data.get("msg_type")

        if msg_type == "tick":
            tick = data["tick"]
            price = float(tick["quote"])
            self.strategy.update(price)
            signal = self.strategy.decide()

            # log SETIAP tick (bukan cuma yang ada sinyal) buat dataset AI
            fast = self.strategy._sma(self.strategy.fast)
            slow = self.strategy._sma(self.strategy.slow)
            tech_indicators = ind.all_indicators(list(self.strategy.prices))
            log_tick(SYMBOL, price, fast, slow, signal, tech_indicators)

            if signal and ENABLE_DAILY_LIMITS:
                today_pl = get_today_pl()
                if today_pl <= DAILY_LOSS_LIMIT:
                    print(f"[STOP] Daily loss limit tercapai ({today_pl}). Skip entry.")
                    signal = None
                elif today_pl >= DAILY_PROFIT_LIMIT:
                    print(f"[STOP] Daily profit target tercapai ({today_pl}). Skip entry.")
                    signal = None

            if signal:
                await self.buy_contract(signal, price)

        elif msg_type == "proposal_open_contract":
            poc = data["proposal_open_contract"]
            if poc.get("is_sold"):
                contract_id = poc["contract_id"]
                if contract_id in self.open_contracts:
                    pl = float(poc.get("profit", 0))
                    exit_price = float(poc.get("exit_tick", poc.get("sell_price", 0)))
                    won = pl > 0
                    log_close_trade(contract_id, exit_price, pl, won)
                    print(f"[SETTLED] contract {contract_id} P/L={pl:+.2f} {'WIN' if won else 'LOSS'}")
                    del self.open_contracts[contract_id]

    async def run(self):
        if not DERIV_API_TOKEN:
            print("ERROR: DERIV_API_TOKEN belum diisi di file .env")
            sys.exit(1)

        ws_url, account_id = get_demo_ws_url(DERIV_API_TOKEN, APP_ID)
        print(f"Akun demo ditemukan: {account_id}")

        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            await self.subscribe_ticks()
            print(f"Bot jalan di {SYMBOL}, mode DEMO. Menunggu sinyal SMA crossover...")
            async for message in ws:
                await self.handle_message(message)


if __name__ == "__main__":
    bot = DerivBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nBot dihentikan.")
