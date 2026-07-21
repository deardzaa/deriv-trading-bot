"""
Cek apakah gold (XAU/USD) tersedia buat ditradingkan lewat Deriv API,
sebelum kita invest waktu buat adaptasi bot ke instrumen ini.

Yang dicek:
1. active_symbols  -> apakah simbol gold (frxXAUUSD) aktif & bisa ditradingkan
2. contracts_for   -> tipe kontrak apa aja yang tersedia buat simbol itu,
                      berapa durasi minimum/maksimumnya

Cara pakai:
    python check_gold_symbol.py
"""
import asyncio
import json
import sys
import websockets

from config import DERIV_API_TOKEN, APP_ID
from deriv_auth import get_demo_ws_url

# Kandidat simbol - dicek semua, biar kalau salah satu nama berubah/deprecated
# masih ketemu yang aktif.
CANDIDATE_SYMBOLS = ["frxXAUUSD", "XAUUSD"]


async def check():
    print("Ambil URL WebSocket akun demo...")
    ws_url, account_id = get_demo_ws_url(DERIV_API_TOKEN, APP_ID)
    print(f"Terhubung ke akun demo: {account_id}\n")

    async with websockets.connect(ws_url) as ws:
        # === 1. active_symbols ===
        print("=" * 60)
        print("CEK active_symbols (cari yang berhubungan sama gold)")
        print("=" * 60)
        await ws.send(json.dumps({"active_symbols": "brief"}))
        resp = json.loads(await ws.recv())

        if "error" in resp:
            print(f"[ERROR] {resp['error'].get('message')}")
            sys.exit(1)

        symbols = resp.get("active_symbols", [])
        gold_matches = [
            s for s in symbols
            if "XAU" in s.get("symbol", "").upper() or "gold" in s.get("display_name", "").lower()
        ]

        if not gold_matches:
            print("Nggak ketemu simbol gold apapun di active_symbols.")
            print("Kemungkinan: nggak tersedia di landing company akun kamu, atau nama simbol beda.")
        else:
            for s in gold_matches:
                print(f"  symbol={s.get('symbol')} | display_name={s.get('display_name')} | "
                      f"market={s.get('market')} | exchange_is_open={s.get('exchange_is_open')} | "
                      f"is_trading_suspended={s.get('is_trading_suspended')}")

        # Ambil symbol code pertama yang valid buat dicek contracts_for
        found_symbol = gold_matches[0]["symbol"] if gold_matches else None

        # Kalau nggak ketemu dari hasil active_symbols, coba paksa cek kandidat manual
        if not found_symbol:
            print("\nCoba cek kandidat simbol manual satu-satu ke contracts_for...")
            found_symbol = CANDIDATE_SYMBOLS[0]

        # === 2. contracts_for ===
        print("\n" + "=" * 60)
        print(f"CEK contracts_for symbol={found_symbol}")
        print("=" * 60)
        await ws.send(json.dumps({"contracts_for": found_symbol, "currency": "USD"}))
        resp2 = json.loads(await ws.recv())

        if "error" in resp2:
            print(f"[ERROR] {resp2['error'].get('message')}")
            print(f"Simbol '{found_symbol}' kemungkinan nggak valid/nggak tersedia buat akun ini.")
            sys.exit(1)

        contracts = resp2.get("contracts_for", {}).get("available", [])
        if not contracts:
            print("Nggak ada kontrak yang tersedia buat simbol ini.")
            sys.exit(0)

        print(f"Ketemu {len(contracts)} tipe kontrak. Detail tiap tipe:\n")
        seen_types = {}
        for c in contracts:
            ctype = c.get("contract_type")
            if ctype not in seen_types:
                seen_types[ctype] = c

        for ctype, c in seen_types.items():
            print(f"  contract_type={ctype}")
            print(f"    min_contract_duration={c.get('min_contract_duration')}  "
                  f"max_contract_duration={c.get('max_contract_duration')}")
            print(f"    barrier_category={c.get('barrier_category')}  "
                  f"start_type={c.get('start_type')}")
            print()

        print("=" * 60)
        print("KESIMPULAN")
        print("=" * 60)
        print(f"Simbol yang dicek: {found_symbol}")
        print(f"Jumlah tipe kontrak tersedia: {len(seen_types)}")
        print("\nBandingkan 'min_contract_duration' di atas sama DURATION di config.py (sekarang 60s).")
        print("Kalau minimum durasi gold jauh lebih panjang dari 60s, bot perlu")
        print("disesuaikan (DURATION, PREDICTION_HORIZON_TICKS, dan strategi horizon-nya).")


if __name__ == "__main__":
    asyncio.run(check())
