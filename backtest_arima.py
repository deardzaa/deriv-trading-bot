"""
Backtest ArimaStrategy pakai ticks_dataset.csv.

CATATAN PERFORMA: fit ARIMA itu berat (bukan operasi O(1) kayak SMA/RSI),
jadi backtest ini SENGAJA nge-sample tiap N tick (bukan tiap tick), biar
nggak keburu lambat buat dataset besar. Evaluasi tetap non-overlapping
(konsisten sama backtest_multi_indicator.py dan train_model.py).

Cara pakai:
    python backtest_arima.py [jumlah_sample_max]
"""
import sys
import time
import pandas as pd

from config import TICKS_LOG_PATH, PREDICTION_HORIZON_TICKS
from arima_strategy import ArimaStrategy

DEFAULT_MAX_SAMPLES = 300  # batasi jumlah kali fit ARIMA biar nggak lama


def backtest(prices, max_samples):
    strategy = ArimaStrategy()
    correct = 0
    total = 0
    next_eligible = strategy.window
    sample_count = 0

    for i, p in enumerate(prices):
        strategy.update(p)
        if i < next_eligible or sample_count >= max_samples:
            continue

        signal = strategy.decide()
        sample_count += 1  # dihitung tiap kali ARIMA beneran nyoba fit
        if signal is None:
            continue

        target_idx = i + PREDICTION_HORIZON_TICKS
        if target_idx >= len(prices):
            continue

        actual_dir = "CALL" if prices[target_idx] > prices[i] else "PUT"
        total += 1
        if signal == actual_dir:
            correct += 1
        next_eligible = i + PREDICTION_HORIZON_TICKS  # skip biar non-overlap

    return correct, total, sample_count


def main():
    max_samples = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MAX_SAMPLES

    try:
        df = pd.read_csv(TICKS_LOG_PATH)
    except FileNotFoundError:
        print(f"Belum ada data di {TICKS_LOG_PATH}. Jalankan bot dulu biar data kekumpul.")
        sys.exit(1)

    prices = pd.to_numeric(df["price"], errors="coerce").dropna().tolist()
    print(f"Data tersedia: {len(prices)} tick. Backtest ARIMA dibatasi max "
          f"{max_samples} kali fit (biar nggak lama - ARIMA fitting itu berat).")
    print(f"Horizon prediksi: {PREDICTION_HORIZON_TICKS} tick / {PREDICTION_HORIZON_TICKS*2}s ke depan\n")

    start = time.time()
    correct, total, sample_count = backtest(prices, max_samples)
    elapsed = time.time() - start

    print(f"Waktu: {elapsed:.1f} detik buat {sample_count} kali fit ARIMA")
    print(f"Sinyal valid (forecast cukup signifikan): {total}/{sample_count}")

    if total == 0:
        print("\nNggak ada sinyal valid yang bisa dievaluasi (mungkin semua forecast")
        print("ARIMA terlalu deket sama harga terakhir - ini KONSISTEN dengan")
        print("data yang mirip random walk, di mana forecast terbaik ARIMA")
        print("emang cenderung 'nggak berubah dari harga sekarang'.")
        sys.exit(0)

    acc = correct / total
    print(f"\nAkurasi: {acc:.3f} ({correct}/{total})")
    print("(0.50 = setara nebak koin.)")
    print("\nInterpretasi:")
    print("- Kalau akurasi deket 0.50 dan/atau sinyal valid sangat sedikit")
    print("  dibanding jumlah fit, itu konsisten sama data random walk - ARIMA")
    print("  matematis nggak nemu pola yang bisa diramal dari struktur harganya.")
    print("- Kalau akurasi jelas di atas 0.55 dengan sample cukup banyak, itu")
    print("  sinyal ARIMA beneran nangkep sesuatu yang nyata.")


if __name__ == "__main__":
    main()
