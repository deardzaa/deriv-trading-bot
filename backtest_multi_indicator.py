"""
Backtest MultiIndicatorStrategy pakai ticks_dataset.csv - ngukur akurasi di
berbagai level 'min_consensus' (berapa indikator yang harus kompak setuju
sebelum sinyal dianggap valid).

PENTING: evaluasi di sini SENGAJA non-overlapping dari awal (skip
PREDICTION_HORIZON_TICKS tiap kali abis ngasih sinyal) - biar nggak kena
ilusi akurasi tinggi dari window yang saling nyerempet, sama kayak yang
kita temuin di train_model.py.

Cara pakai:
    python backtest_multi_indicator.py
"""
import sys
import pandas as pd

from config import TICKS_LOG_PATH, PREDICTION_HORIZON_TICKS
from multi_indicator_strategy import MultiIndicatorStrategy


def backtest(prices, min_consensus):
    strategy = MultiIndicatorStrategy(min_consensus=min_consensus)
    correct = 0
    total = 0
    next_eligible = 0

    for i, p in enumerate(prices):
        strategy.update(p)
        if i < next_eligible:
            continue
        signal = strategy.decide()
        if signal is None:
            continue
        target_idx = i + PREDICTION_HORIZON_TICKS
        if target_idx >= len(prices):
            continue
        actual_dir = "CALL" if prices[target_idx] > prices[i] else "PUT"
        total += 1
        if signal == actual_dir:
            correct += 1
        next_eligible = i + PREDICTION_HORIZON_TICKS  # skip biar nggak overlap

    return correct, total


def main():
    try:
        df = pd.read_csv(TICKS_LOG_PATH)
    except FileNotFoundError:
        print(f"Belum ada data di {TICKS_LOG_PATH}. Jalankan bot dulu biar data kekumpul.")
        sys.exit(1)

    prices = pd.to_numeric(df["price"], errors="coerce").dropna().tolist()
    print(f"Backtest pakai {len(prices)} tick harga (evaluasi non-overlapping dari awal)")
    print(f"Horizon prediksi: {PREDICTION_HORIZON_TICKS} tick / {PREDICTION_HORIZON_TICKS*2}s ke depan\n")

    print(f"{'Min Consensus':>15} | {'Akurasi':>8} | {'Jml Sinyal':>10}")
    print("-" * 45)
    for min_consensus in range(2, 8):
        correct, total = backtest(prices, min_consensus)
        if total == 0:
            print(f"{min_consensus:>15} | {'--':>8} | {0:>10} (nggak ada sinyal di level ini)")
            continue
        acc = correct / total
        print(f"{min_consensus:>15} | {acc:>8.3f} | {total:>10}")

    print("\nInterpretasi:")
    print("- 'Min Consensus' = minimal berapa dari 7 indikator yang harus kompak")
    print("  setuju sebelum sinyal dianggap valid (makin tinggi, makin ketat/jarang).")
    print("- 0.50 = setara nebak koin. Kalau nggak jauh di atas itu, berarti")
    print("  gabungan indikator ini juga belum ketemu sinyal yang beneran diandalkan.")
    print("- Bandingin sama hasil SMA doang yang udah jalan - kalau consensus level")
    print("  tertentu jelas lebih baik DAN jumlah sinyalnya masih wajar (bukan cuma")
    print("  segelintir), itu baru layak dicoba ganti strategi trading beneran.")


if __name__ == "__main__":
    main()
