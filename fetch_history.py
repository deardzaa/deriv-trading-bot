"""
Narik histori tick historis langsung dari Deriv (bukan nunggu real-time),
biar dataset training bisa langsung banyak tanpa nunggu bot jalan berhari-hari.

PENTING: Deriv membatasi MAX 1000 tick per request (bukan 5000 seperti dugaan
awal). Buat narik lebih dari itu, script ini otomatis minta berkali-kali
secara berurutan, tiap kali minta data yang LEBIH LAMA dari batch sebelumnya
(pakai parameter waktu 'end'), lalu digabung semua.

Cara pakai:
    python fetch_history.py [jumlah_tick]

Contoh:
    python fetch_history.py 5000
"""
import asyncio
import json
import sys
import time
import websockets

from config import SYMBOL, TICKS_LOG_PATH
from dataset_logger import log_tick
from strategy import SmaCrossoverStrategy
import indicators as ind

# Data harga (ticks_history) itu public, nggak butuh token/akun - jadi pakai
# endpoint public langsung, nggak perlu autentikasi apa pun.
WS_URL = "wss://api.derivws.com/trading/v1/options/ws/public"
MAX_PER_REQUEST = 1000


async def fetch_batch(ws, count, end):
    await ws.send(json.dumps({
        "ticks_history": SYMBOL,
        "adjust_start_time": 1,
        "count": count,
        "end": end,
        "style": "ticks",
    }))
    res = json.loads(await ws.recv())
    if "error" in res:
        raise RuntimeError(res["error"].get("message"))
    history = res["history"]
    prices = [float(p) for p in history["prices"]]
    times = [int(t) for t in history["times"]]
    return prices, times


async def fetch(total_count: int):
    all_prices = []
    all_times = []
    end = "latest"

    async with websockets.connect(WS_URL, open_timeout=15) as ws:
        while len(all_prices) < total_count:
            remaining = total_count - len(all_prices)
            batch_size = min(MAX_PER_REQUEST, remaining)

            prices, times = await fetch_batch(ws, batch_size, end)
            if not prices:
                print("Deriv nggak ngasih data lagi (kemungkinan udah mentok "
                      "histori paling lama yang tersedia). Berhenti di sini.")
                break

            # batch berikutnya minta data SEBELUM tick paling lama di batch ini
            end = times[0] - 1

            # gabung di depan, karena batch baru ini lebih lama (lebih awal)
            all_prices = prices + all_prices
            all_times = times + all_times

            print(f"Progress: {len(all_prices)}/{total_count} tick terkumpul...")

            # jeda dikit biar nggak kena rate limit
            await asyncio.sleep(0.5)

    print(f"Berhasil ambil total {len(all_prices)} tick historis untuk {SYMBOL}.")
    return all_prices


def save_to_dataset(prices):
    strategy = SmaCrossoverStrategy()
    # Window terbatas buat hitung indikator (sama kayak yang dipakai bot live
    # di ai_strategy.py) - biar konsisten DAN jauh lebih cepat. Ngitung dari
    # SELURUH histori tiap baris itu O(n^2), bisa timeout buat dataset besar.
    WINDOW = 60
    for i, p in enumerate(prices):
        strategy.update(p)
        fast = strategy._sma(strategy.fast)
        slow = strategy._sma(strategy.slow)
        signal = strategy.decide()
        window_prices = prices[max(0, i + 1 - WINDOW):i + 1]
        tech_indicators = ind.all_indicators(window_prices)
        log_tick(SYMBOL, p, fast, slow, signal, tech_indicators)
        if (i + 1) % 500 == 0:
            print(f"Diproses {i + 1}/{len(prices)} baris...")
    print(f"Data ditulis ke {TICKS_LOG_PATH}")
    print("Sekarang bisa langsung jalankan: python train_model.py")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    prices = asyncio.run(fetch(count))
    save_to_dataset(prices)
