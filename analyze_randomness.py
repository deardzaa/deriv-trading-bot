"""
Tes statistik: apakah data harga di ticks_dataset.csv beneran punya pola yang
bisa diprediksi, atau murni random walk?

Ini BEDA dari train_model.py - itu nyoba "melatih model dan lihat akurasinya",
yang bisa ketipu overfitting/kebetulan di sample kecil. Script ini langsung
nguji signifikansi statistik dari korelasi harga, jadi jawabannya lebih pasti
dan nggak tergantung algoritma ML yang dipilih.

Cara pakai:
    python analyze_randomness.py

Yang diuji:
1. Autocorrelation - apakah perubahan harga sekarang berkorelasi sama
   perubahan harga sebelumnya? (kalau random walk murni, harusnya ~0)
2. Runs test - apakah urutan naik/turun mengikuti pola non-random?
3. Ljung-Box test - uji formal signifikansi autokorelasi di banyak lag sekaligus
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf

from config import TICKS_LOG_PATH


def runs_test(directions):
    """Uji apakah urutan naik(1)/turun(0) itu random atau ada pola berturutan."""
    n1 = int(np.sum(directions == 1))
    n0 = int(np.sum(directions == 0))
    runs = 1 + int(np.sum(directions[1:] != directions[:-1]))

    expected_runs = ((2 * n1 * n0) / (n1 + n0)) + 1
    variance = (2 * n1 * n0 * (2 * n1 * n0 - n1 - n0)) / (
        ((n1 + n0) ** 2) * (n1 + n0 - 1)
    )
    if variance <= 0:
        return None, None
    z = (runs - expected_runs) / np.sqrt(variance)
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return z, p_value


def main():
    try:
        df = pd.read_csv(TICKS_LOG_PATH)
    except FileNotFoundError:
        print(f"Belum ada data di {TICKS_LOG_PATH}. Jalankan bot dulu biar data kekumpul.")
        sys.exit(1)

    prices = pd.to_numeric(df["price"], errors="coerce").dropna().reset_index(drop=True)
    print(f"Menganalisis {len(prices)} tick harga...\n")

    if len(prices) < 100:
        print("Data kurang dari 100 baris, belum cukup buat analisis statistik yang bermakna.")
        sys.exit(1)

    changes = prices.diff().dropna()
    directions = (changes > 0).astype(int).to_numpy()

    # === 1. Autocorrelation ===
    print("=" * 60)
    print("1. AUTOCORRELATION (perubahan harga vs lag sebelumnya)")
    print("=" * 60)
    acf_values = acf(changes, nlags=10, fft=True)
    for lag in range(1, 11):
        val = acf_values[lag]
        flag = " <- di luar rentang normal (0.05)" if abs(val) > 0.05 else ""
        print(f"  Lag {lag:2d}: {val:+.4f}{flag}")
    print("\n  Interpretasi: kalau random walk murni, semua nilai ini harusnya")
    print("  deket 0 (dalam rentang -0.05 sampai +0.05 buat data segini banyak).")

    # === 2. Runs test ===
    print("\n" + "=" * 60)
    print("2. RUNS TEST (pola urutan naik/turun)")
    print("=" * 60)
    z, p_value = runs_test(directions)
    if z is not None:
        print(f"  Z-score: {z:.4f} | p-value: {p_value:.4f}")
        if p_value < 0.05:
            print("  --> SIGNIFIKAN (p < 0.05): urutan naik/turun BUKAN murni random,")
            print("      ada pola berturutan (misal cenderung 'nempel' atau 'gantian').")
        else:
            print("  --> TIDAK signifikan (p >= 0.05): konsisten sama random walk,")
            print("      urutan naik/turun nggak nunjukin pola berturutan.")

    # === 3. Ljung-Box test ===
    print("\n" + "=" * 60)
    print("3. LJUNG-BOX TEST (autokorelasi gabungan di lag 1-10)")
    print("=" * 60)
    lb_result = acorr_ljungbox(changes, lags=[10], return_df=True)
    lb_pvalue = lb_result["lb_pvalue"].iloc[0]
    print(f"  p-value: {lb_pvalue:.4f}")
    if lb_pvalue < 0.05:
        print("  --> SIGNIFIKAN (p < 0.05): ADA autokorelasi yang nggak bisa")
        print("      dijelaskan kebetulan. Ini sinyal paling kuat kalau ada pola asli.")
    else:
        print("  --> TIDAK signifikan (p >= 0.05): TIDAK ada bukti kuat autokorelasi.")
        print("      Data ini secara statistik nggak beda dari random walk murni.")

    # === Kesimpulan ===
    print("\n" + "=" * 60)
    print("KESIMPULAN")
    print("=" * 60)
    if lb_pvalue < 0.05 or (p_value is not None and p_value < 0.05):
        print("Ada indikasi statistik bahwa data harga TIDAK murni random - berarti")
        print("secara teori ada ruang buat model prediktif menemukan pola. TAPI ini")
        print("cuma nunjukin ADA korelasi, bukan seberapa BESAR dan seberapa BISA")
        print("DIANDALKAN buat trading praktis (korelasi kecil pun bisa signifikan")
        print("secara statistik di data besar, tapi nggak cukup buat profit konsisten")
        print("setelah dikurangi spread/komisi).")
    else:
        print("TIDAK ada bukti statistik yang kuat bahwa harga R_100 bisa diprediksi")
        print("dari histori harganya sendiri. Ini konsisten dengan cara Deriv")
        print("mendesain synthetic index ini (random generator). Model AI apa pun")
        print("yang dilatih dari data ini kemungkinan besar cuma akan menangkap")
        print("noise, bukan pola asli - sama seperti yang udah kelihatan di")
        print("percobaan train_model.py sebelumnya.")


if __name__ == "__main__":
    main()
