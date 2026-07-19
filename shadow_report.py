"""
Liat rapor forward-test shadow mode - dijalankan kapan aja buat cek gimana
performa prediksi AI di data BARU (bukan data historis yang udah dites).

Cara pakai:
    python shadow_report.py
"""
import shadow_logger


def main():
    data = shadow_logger._load()
    all_preds = data["predictions"]
    resolved = [p for p in all_preds if p["resolved"]]
    pending = [p for p in all_preds if not p["resolved"]]

    print(f"Total prediksi shadow: {len(all_preds)}")
    print(f"  Sudah resolved (ada hasilnya): {len(resolved)}")
    print(f"  Masih pending (nunggu jatuh tempo): {len(pending)}")

    if not resolved:
        print("\nBelum ada prediksi yang resolved. Biarin bot jalan beberapa jam/hari dulu.")
        return

    print("\n" + "=" * 55)
    print("AKURASI PER LEVEL CONFIDENCE (data BARU, bukan backtest)")
    print("=" * 55)
    print(f"{'Min Confidence':>15} | {'Akurasi':>8} | {'Jml Prediksi':>13}")
    print("-" * 45)
    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        stats = shadow_logger.get_stats(min_confidence=threshold)
        if stats["total"] == 0:
            print(f"{threshold:>15.2f} | {'--':>8} | {0:>13}")
            continue
        print(f"{threshold:>15.2f} | {stats['accuracy']:>8.3f} | {stats['total']:>13}")

    print("\nIni beda dari tabel confidence di train_model.py: angka di sini")
    print("dievaluasi pakai prediksi yang beneran dibuat di masa depan (real-time),")
    print("bukan dari data historis yang sama yang dipakai buat training. Kalau")
    print("angkanya konsisten sama hasil backtest (misal tetap di atas 60% di")
    print("confidence 0.55+), itu bukti paling kuat kalau sinyalnya beneran nyata.")


if __name__ == "__main__":
    main()
