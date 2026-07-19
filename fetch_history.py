"""
Narik histori tick historis langsung dari Deriv (bukan nunggu real-time),
biar dataset training bisa langsung banyak tanpa nunggu bot jalan berhari-hari.

Cara pakai:
    python fetch_history.py [jumlah_tick]

Contoh:
    python fetch_history.py 5000
"""
import asyncio
import json
import sys
import websockets

from config import APP_ID, SYMBOL, TICKS_LOG_PATH
from dataset_logger import log_tick
from strategy import SmaCrossoverStrategy
import indicators as ind

WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"


async def fetch(count: int):
    async with websockets.connect(WS_URL, open_timeout=15) as ws:
        await ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "ticks",
        }))
        res = json.loads(await ws.recv())
        if "error" in res:
            print(f"[ERROR] {res['error'].get('message')}")
            sys.exit(1)
        prices = [float(p) for p in res["history"]["prices"]]
        print(f"Berhasil ambil {len(prices)} tick historis untuk {SYMBOL}.")
        return prices


def save_to_dataset(prices):
    strategy = SmaCrossoverStrategy()
    for i, p in enumerate(prices):
        strategy.update(p)
        fast = strategy._sma(strategy.fast)
        slow = strategy._sma(strategy.slow)
        signal = strategy.decide()
        tech_indicators = ind.all_indicators(prices[:i + 1])
        log_tick(SYMBOL, p, fast, slow, signal, tech_indicators)
    print(f"Data ditulis ke {TICKS_LOG_PATH}")
    print("Sekarang bisa langsung jalankan: python train_model.py")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    # Deriv membatasi ticks_history max ~5000 per request; kalau minta lebih,
    # ini akan otomatis dipangkas oleh API-nya sendiri.
    prices = asyncio.run(fetch(count))
    save_to_dataset(prices)
