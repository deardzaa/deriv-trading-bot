"""
Versi bot yang jalan SEKALI lalu selesai (bukan streaming terus-terusan).
Didesain buat dipicu berkala oleh GitHub Actions (cron), bukan proses yang
tetap hidup di device/server kamu.

Alur tiap run:
1. Connect ke Deriv, authorize
2. Tarik histori tick terakhir (bukan nunggu tick baru real-time)
3. Hitung sinyal (SMA atau AI, sesuai STRATEGY_MODE)
4. Kalau ada sinyal, buka posisi
5. Log semuanya, lalu tutup koneksi dan selesai

Fail-open: kalau ada error (koneksi putus, API lambat, dll), bot retry
beberapa kali. Kalau tetap gagal, bot log error dan berhenti dengan aman
(exit code 0) — TIDAK bikin GitHub Actions workflow gagal terus-menerus,
biar nggak spam notifikasi error ke email kamu.
"""
import asyncio
import json
import sys
import websockets

from config import (
    DERIV_API_TOKEN, APP_ID, SYMBOL, STAKE, DURATION, DURATION_UNIT,
    ALLOW_REAL_ACCOUNT, STRATEGY_MODE, MAX_RETRIES, RETRY_DELAY_SECONDS,
    HISTORY_TICKS_COUNT, DAILY_LOSS_LIMIT, DAILY_PROFIT_LIMIT, ENABLE_DAILY_LIMITS,
)
from strategy import SmaCrossoverStrategy
from trade_logger import log_open_trade, log_close_trade, get_today_pl
from dataset_logger import log_tick
import indicators as ind

WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"


def build_strategy():
    """Coba pakai AI kalau diminta & modelnya ada, kalau nggak fallback ke SMA
    (fail-open: jangan sampai run gagal total cuma gara-gara model belum ada)."""
    if STRATEGY_MODE == "AI":
        try:
            from ai_strategy import AiStrategy
            print("Mode: AI (pakai model.pkl)")
            return AiStrategy()
        except FileNotFoundError as e:
            print(f"[WARN] {e}")
            print("Fallback ke mode SMA buat run ini.")
    print("Mode: SMA (rule-based)")
    return SmaCrossoverStrategy()


async def buy_contract(ws, direction, price):
    payload = {
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
    await ws.send(json.dumps(payload))
    res = json.loads(await ws.recv())
    if "error" in res:
        print(f"[WARN] Gagal buy: {res['error'].get('message')}")
        return
    buy = res.get("buy", {})
    contract_id = buy.get("contract_id")
    print(f"[TRADE] {direction} {SYMBOL} stake={STAKE} @ {price} -> contract {contract_id}")
    log_open_trade(contract_id, SYMBOL, direction, STAKE, price)


async def fetch_history(ws):
    await ws.send(json.dumps({
        "ticks_history": SYMBOL,
        "adjust_start_time": 1,
        "count": HISTORY_TICKS_COUNT,
        "end": "latest",
        "style": "ticks",
    }))
    res = json.loads(await ws.recv())
    if "error" in res:
        raise RuntimeError(res["error"].get("message"))
    return [float(p) for p in res["history"]["prices"]]


async def authorize(ws):
    await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
    res = json.loads(await ws.recv())
    if "error" in res:
        raise RuntimeError(res["error"].get("message"))
    auth = res["authorize"]
    is_virtual = auth.get("is_virtual", 0)
    print(f"Login: {auth.get('loginid')} | Demo: {bool(is_virtual)}")
    if not is_virtual and not ALLOW_REAL_ACCOUNT:
        raise RuntimeError("Akun REAL terdeteksi, bot dikunci demo-only. Berhenti.")
    return auth


async def single_run():
    if not DERIV_API_TOKEN:
        print("[FATAL] DERIV_API_TOKEN kosong. Cek GitHub Secrets.")
        sys.exit(1)

    async with websockets.connect(WS_URL, open_timeout=15) as ws:
        await authorize(ws)
        prices = await fetch_history(ws)
        print(f"Ambil {len(prices)} tick historis.")

        strategy = build_strategy()
        for p in prices:
            strategy.update(p)
        signal = strategy.decide()
        last_price = prices[-1]

        fast = strategy._sma(strategy.fast)
        slow = strategy._sma(strategy.slow)
        tech_indicators = ind.all_indicators(prices)
        log_tick(SYMBOL, last_price, fast, slow, signal, tech_indicators)

        print(f"Harga terakhir: {last_price} | Sinyal: {signal or '(tidak ada)'}")

        if signal and ENABLE_DAILY_LIMITS:
            today_pl = get_today_pl()
            if today_pl <= DAILY_LOSS_LIMIT:
                print(f"[STOP] Daily loss limit tercapai (P&L hari ini: {today_pl}, "
                      f"limit: {DAILY_LOSS_LIMIT}). Skip entry, coba lagi besok.")
                signal = None
            elif today_pl >= DAILY_PROFIT_LIMIT:
                print(f"[STOP] Daily profit target tercapai (P&L hari ini: {today_pl}, "
                      f"target: {DAILY_PROFIT_LIMIT}). Skip entry, coba lagi besok.")
                signal = None

        if signal:
            await buy_contract(ws, signal, last_price)
        else:
            print("Nggak ada sinyal entry di run ini. Selesai.")


async def run_with_retries():
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await single_run()
            return
        except Exception as e:
            last_err = e
            print(f"[WARN] Percobaan {attempt}/{MAX_RETRIES} gagal: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    print(f"[FAIL-OPEN] Semua percobaan gagal di run ini. Error terakhir: {last_err}")
    print("Bot akan coba lagi di run berikutnya (jadwal berikutnya), bukan berhenti permanen.")
    # exit 0 (bukan 1) supaya GitHub Actions nggak nge-flag run ini sebagai
    # failure yang bikin notifikasi spam - ini kegagalan sementara yang wajar
    # (misal Deriv API lagi maintenance), bukan bug di kode.


if __name__ == "__main__":
    asyncio.run(run_with_retries())
