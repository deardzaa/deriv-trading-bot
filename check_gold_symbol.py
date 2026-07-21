"""
Cek instrumen REAL (bukan synthetic index/RNG) apa aja yang tersedia di akun
Deriv kamu, dan berapa durasi kontrak MINIMUM masing-masing.

Tujuan: cari tau apakah ada instrumen pasar riil (forex/stock index/crypto)
yang bisa ditradingkan dengan durasi pendek (menitan), sebagai alternatif
dari gold yang minimumnya 1 hari.

Cara pakai:
    python check_gold_symbol.py
"""
import asyncio
import json
import sys
import websockets

from config import DERIV_API_TOKEN, APP_ID
from deriv_auth import get_demo_ws_url

# Market REAL yang mau dicek (bukan synthetic_index)
REAL_MARKETS = ["forex", "indices", "commodities", "cryptocurrency"]

# Berapa banyak simbol dicek per kategori (biar nggak kelamaan)
MAX_PER_MARKET = 6


async def check():
    print("Ambil URL WebSocket akun demo...")
    ws_url, account_id = get_demo_ws_url(DERIV_API_TOKEN, APP_ID)
    print(f"Terhubung ke akun demo: {account_id}\n")

    async with websockets.connect(ws_url) as ws:
        print("=" * 60)
        print("CEK active_symbols (semua market riil)")
        print("=" * 60)
        await ws.send(json.dumps({"active_symbols": "brief"}))
        resp = json.loads(await ws.recv())

        if "error" in resp:
            print(f"[ERROR] {resp['error'].get('message')}")
            sys.exit(1)

        symbols = resp.get("active_symbols", [])
        print(f"\nTotal simbol diterima dari API: {len(symbols)}")
        print("\n--- DEBUG: contoh 2 entri mentah dari API (biar ketauan nama field asli) ---")
        print(json.dumps(symbols[:2], indent=2))
        print("--- END DEBUG ---\n")

        by_market = {}
        for s in symbols:
            m = s.get("market")
            if m in REAL_MARKETS:
                by_market.setdefault(m, []).append(s)

        for m in REAL_MARKETS:
            found = by_market.get(m, [])
            print(f"\n{m}: {len(found)} simbol tersedia")
            for s in found[:MAX_PER_MARKET]:
                sym = s.get('underlying_symbol') or '?'
                name = s.get('underlying_symbol_name') or '?'
                print(f"  {sym:<15} {name}")

        # === Cek contracts_for buat tiap kategori (ambil 1-2 simbol representatif) ===
        print("\n" + "=" * 60)
        print("CEK DURASI MINIMUM KONTRAK per KATEGORI")
        print("=" * 60)

        summary = []
        for m in REAL_MARKETS:
            found = by_market.get(m, [])
            if not found:
                print(f"\n{m}: TIDAK TERSEDIA di akun ini, skip.")
                continue

            # Cek 2 simbol representatif per market biar nggak cuma 1 sample
            for s in found[:2]:
                symbol = s.get("underlying_symbol")
                if not symbol:
                    print(f"\n({m}): entri ini nggak punya field 'symbol' yang valid, skip. Raw: {s}")
                    continue
                await ws.send(json.dumps({"contracts_for": symbol}))
                resp2 = json.loads(await ws.recv())

                if "error" in resp2:
                    print(f"\n{symbol} ({m}): [ERROR] {resp2['error'].get('message')}")
                    continue

                contracts = resp2.get("contracts_for", {}).get("available", [])
                riseFall = [c for c in contracts if c.get("contract_type") in ("CALL", "PUT")]

                if not riseFall:
                    print(f"\n{symbol} ({m}): nggak ada kontrak Rise/Fall (CALL/PUT) tersedia.")
                    continue

                min_dur = riseFall[0].get("min_contract_duration") or "?"
                max_dur = riseFall[0].get("max_contract_duration") or "?"
                print(f"\n{symbol} ({m}):")
                print(f"  Rise/Fall min_duration={min_dur}  max_duration={max_dur}")
                summary.append((symbol, m, min_dur))

        print("\n" + "=" * 60)
        print("RINGKASAN: instrumen dengan durasi PALING PENDEK per kategori")
        print("=" * 60)
        if not summary:
            print("Nggak ketemu satupun instrumen real market dengan kontrak Rise/Fall.")
            print("Kemungkinan besar: durasi pendek (menit/detik) cuma tersedia di synthetic index.")
        else:
            for symbol, m, min_dur in summary:
                print(f"  {symbol:<15} ({m:<15}) min_duration={min_dur}")
            print("\nBandingkan min_duration ini sama DURATION di config.py sekarang (60s).")
            print("Kalau semuanya '1d' ke atas, sama kayak gold - berarti Deriv memang")
            print("cuma ngasih opsi durasi pendek (tick/menit) di synthetic index, bukan")
            print("di instrumen pasar riil - kemungkinan karena alasan regulasi/likuiditas.")


if __name__ == "__main__":
    asyncio.run(check())
