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
import os
import sys
import time
import websockets

from config import (
    DERIV_API_TOKEN, APP_ID, SYMBOL, STAKE, DURATION, DURATION_UNIT,
    STRATEGY_MODE, MAX_RETRIES, RETRY_DELAY_SECONDS,
    HISTORY_TICKS_COUNT, DAILY_LOSS_LIMIT, DAILY_PROFIT_LIMIT, ENABLE_DAILY_LIMITS,
    MODEL_PATH,
)
from strategy import SmaCrossoverStrategy
from trade_logger import log_open_trade, log_close_trade, get_today_pl
from dataset_logger import log_tick
import indicators as ind
from deriv_auth import get_demo_ws_url
import shadow_logger


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
    prices = [float(p) for p in res["history"]["prices"]]
    times = [int(t) for t in res["history"]["times"]]
    return prices, times


async def fetch_price_at(ws, target_epoch):
    """Ambil harga historis paling deket sebelum/pas target_epoch - dipakai
    buat resolve prediksi shadow (cek harga asli pas prediksi jatuh tempo)."""
    await ws.send(json.dumps({
        "ticks_history": SYMBOL,
        "adjust_start_time": 1,
        "count": 1,
        "end": target_epoch,
        "style": "ticks",
    }))
    res = json.loads(await ws.recv())
    if "error" in res:
        raise RuntimeError(res["error"].get("message"))
    prices = res["history"]["prices"]
    if not prices:
        return None
    return float(prices[-1])


async def resolve_shadow_predictions(ws):
    """Cek prediksi shadow yang udah jatuh tempo, tarik harga asli, catat
    bener/salah. Ini yang bikin forward-test-nya jujur - dievaluasi pakai
    harga yang beneran terjadi, bukan data yang udah dites-tes sebelumnya."""
    now = int(time.time())
    pending = shadow_logger.get_pending(now)
    if not pending:
        return
    print(f"Menyelesaikan {len(pending)} prediksi shadow yang udah jatuh tempo...")
    for pred in pending:
        try:
            actual_price = await fetch_price_at(ws, pred["target_epoch"])
            if actual_price is None:
                continue
            shadow_logger.resolve_prediction(pred["id"], actual_price)
            status = "BENAR" if (
                (actual_price > pred["entry_price"]) == (pred["predicted_direction"] == "UP")
            ) else "SALAH"
            print(f"  [SHADOW #{pred['id']}] prediksi {pred['predicted_direction']} "
                  f"({pred['confidence']:.2f}) -> {status} "
                  f"(entry={pred['entry_price']}, actual={actual_price})")
        except Exception as e:
            print(f"  [WARN] Gagal resolve prediksi #{pred['id']}: {e}")


def make_shadow_prediction(prices, last_epoch):
    """Kalau model.pkl ada, bikin prediksi AI dan CATAT AJA (nggak dipakai
    trading beneran - itu tetap tugas strategy dari build_strategy()).
    Return None kalau model belum ada atau belum cukup data."""
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        from ai_strategy import AiStrategy
        ai = AiStrategy()
        for p in prices:
            ai.update(p)
        row = ai._build_feature_row()
        if row is None:
            return None
        import pandas as pd
        X = pd.DataFrame([[row[c] for c in ai.feature_cols]], columns=ai.feature_cols)
        proba = ai.model.predict_proba(X)[0]
        direction = "UP" if proba[1] >= proba[0] else "DOWN"
        confidence = max(proba)
        target_epoch = last_epoch + DURATION
        pred_id = shadow_logger.log_prediction(
            entry_price=prices[-1],
            direction=direction,
            confidence=confidence,
            made_at_epoch=last_epoch,
            target_epoch=target_epoch,
        )
        print(f"[SHADOW #{pred_id}] Prediksi baru: {direction} (confidence={confidence:.2f}), "
              f"jatuh tempo dalam {DURATION}s")
        return pred_id
    except Exception as e:
        print(f"[WARN] Gagal bikin prediksi shadow: {e}")
        return None


async def single_run():
    if not DERIV_API_TOKEN:
        print("[FATAL] DERIV_API_TOKEN kosong. Cek GitHub Secrets.")
        sys.exit(1)

    # Ambil URL WebSocket khusus akun DEMO lewat REST + OTP (arsitektur API
    # terbaru Deriv). Ini sengaja CUMA nyari akun bertipe demo - kalau nggak
    # ketemu, get_demo_ws_url() raise error dan bot berhenti (fail-open akan
    # nangkep ini di run_with_retries).
    ws_url, account_id = get_demo_ws_url(DERIV_API_TOKEN, APP_ID)
    print(f"Akun demo ditemukan: {account_id}")

    async with websockets.connect(ws_url, open_timeout=15) as ws:
        # Shadow mode: selesaikan prediksi lama dulu (evaluasi jujur pakai
        # harga yang beneran udah kejadian), sebelum bikin prediksi baru.
        await resolve_shadow_predictions(ws)

        prices, times = await fetch_history(ws)
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

        # Shadow mode: bikin prediksi AI baru buat forward-test, TERLEPAS dari
        # STRATEGY_MODE yang beneran dipakai buat trading. Ini murni observasi,
        # nggak mempengaruhi keputusan trading di bawah.
        make_shadow_prediction(prices, times[-1])

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
