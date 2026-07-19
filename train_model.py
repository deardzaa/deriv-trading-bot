"""
Latih model AI dari ticks_dataset.csv yang dikumpulkan bot.

Cara pakai:
    python train_model.py

Butuh minimal beberapa ribu baris data di ticks_dataset.csv biar hasilnya
nggak cuma nebak-nebak (noise). Kalau datanya masih dikit, script ini akan
kasih peringatan tapi tetap jalan (buat testing pipeline aja, bukan buat
dipakai trading beneran).

PENTING: R_100 dan simbol synthetic index lain di Deriv didesain berbasis
random generator. Secara teori, nggak ada pola harga masa lalu yang bisa
diandalkan buat prediksi harga masa depan di instrumen semacam ini. Model
ini murni latihan/eksperimen data science, bukan jaminan profit.
"""
import sys
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from config import TICKS_LOG_PATH, MODEL_PATH, AI_LOOKBACK

MIN_ROWS_WARNING = 3000


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"]).reset_index(drop=True)

    # fitur: perubahan harga N tick terakhir + SMA yang udah ada di log
    for lag in range(1, AI_LOOKBACK + 1):
        df[f"lag_{lag}"] = df["price"].diff(lag)

    df["sma_fast"] = pd.to_numeric(df["sma_fast"], errors="coerce")
    df["sma_slow"] = pd.to_numeric(df["sma_slow"], errors="coerce")
    df["sma_gap"] = df["sma_fast"] - df["sma_slow"]

    # indikator teknikal tambahan (RSI, MACD, Bollinger Bands)
    df["rsi"] = pd.to_numeric(df.get("rsi"), errors="coerce")

    df["macd"] = pd.to_numeric(df.get("macd"), errors="coerce")
    df["macd_signal"] = pd.to_numeric(df.get("macd_signal"), errors="coerce")
    df["macd_hist"] = df["macd"] - df["macd_signal"]  # momentum MACD

    df["bb_upper"] = pd.to_numeric(df.get("bb_upper"), errors="coerce")
    df["bb_lower"] = pd.to_numeric(df.get("bb_lower"), errors="coerce")
    bb_range = df["bb_upper"] - df["bb_lower"]
    # posisi harga relatif dalam band (0 = di lower band, 1 = di upper band)
    df["bb_percent"] = ((df["price"] - df["bb_lower"]) / bb_range.replace(0, pd.NA))
    df["bb_width"] = bb_range

    # target: apakah harga tick berikutnya naik (1) atau turun (0)
    df["target"] = (df["price"].shift(-1) > df["price"]).astype(int)

    lag_cols = [c for c in df.columns if c.startswith("lag_")]
    indicator_cols = ["sma_gap", "rsi", "macd_hist", "bb_percent", "bb_width"]
    required_cols = lag_cols + indicator_cols + ["target"]
    df = df.dropna(subset=required_cols).reset_index(drop=True)
    return df, lag_cols + indicator_cols


def main():
    try:
        df = pd.read_csv(TICKS_LOG_PATH)
    except FileNotFoundError:
        print(f"Belum ada data di {TICKS_LOG_PATH}. Jalankan deriv_bot.py dulu biar data kekumpul.")
        sys.exit(1)

    print(f"Baris data mentah: {len(df)}")
    if len(df) < MIN_ROWS_WARNING:
        print(f"PERINGATAN: data masih {len(df)} baris, idealnya minimal {MIN_ROWS_WARNING}+ "
              f"biar model nggak cuma overfit/noise. Lanjut tetap dicoba, tapi jangan dipakai "
              f"buat trading beneran dulu.")

    feat_df, feature_cols = build_features(df)
    if len(feat_df) < 50:
        print("Data valid setelah feature engineering kurang dari 50 baris, nggak cukup buat train.")
        sys.exit(1)

    X = feat_df[feature_cols]
    y = feat_df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False  # jangan shuffle, ini deret waktu
    )

    model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\nAkurasi di data test (out-of-sample): {acc:.3f}")
    print("(Sekadar konteks: 0.50 = sama aja kayak nebak koin. Kalau cuma sedikit di atas "
          "0.50, itu nggak signifikan buat dipakai trading beneran.)")
    print(classification_report(y_test, preds, target_names=["DOWN", "UP"]))

    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)
    print(f"\nModel disimpan ke {MODEL_PATH}")
    print("Set STRATEGY_MODE = \"AI\" di config.py kalau mau bot pakai model ini.")


if __name__ == "__main__":
    main()
