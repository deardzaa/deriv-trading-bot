"""
Nyimpen setiap tick harga mentah + indikator teknikal ke CSV, buat dataset
training AI nanti. Ini beda dari trade_logger.py (yang nyimpen hasil trade) —
file ini nyimpen SEMUA pergerakan harga & indikator, terlepas dari ada trade
atau enggak, biar dataset-nya lebih kaya buat model belajar pola.

Kolom CSV:
  timestamp, symbol, price, sma_fast, sma_slow, rsi, macd, macd_signal,
  bb_upper, bb_mid, bb_lower, stoch_k, stoch_d, williams_r, roc, signal
"""
import csv
import os
from datetime import datetime
from config import TICKS_LOG_PATH

_FIELDNAMES = [
    "timestamp", "symbol", "price", "sma_fast", "sma_slow",
    "rsi", "macd", "macd_signal", "bb_upper", "bb_mid", "bb_lower",
    "stoch_k", "stoch_d", "williams_r", "roc", "signal",
]


def _migrate_if_needed():
    """Kalau file udah ada tapi kolomnya beda (skema lama, sebelum indikator
    baru ditambah), migrasi otomatis: kolom baru diisi kosong buat baris lama,
    biar data historis nggak hilang dan tetap konsisten."""
    if not os.path.exists(TICKS_LOG_PATH):
        return
    with open(TICKS_LOG_PATH, "r", newline="") as f:
        reader = csv.reader(f)
        try:
            existing_header = next(reader)
        except StopIteration:
            return  # file kosong

    if existing_header == _FIELDNAMES:
        return  # udah sesuai, nggak perlu migrasi

    print(f"[dataset_logger] Skema CSV berubah, migrasi {TICKS_LOG_PATH}...")
    import pandas as pd
    df = pd.read_csv(TICKS_LOG_PATH)
    for col in _FIELDNAMES:
        if col not in df.columns:
            df[col] = ""
    df = df[_FIELDNAMES]  # urutan kolom sesuai skema baru
    df.to_csv(TICKS_LOG_PATH, index=False)
    print(f"[dataset_logger] Migrasi selesai, {len(df)} baris dipertahankan.")


_migrate_if_needed()
_header_written = os.path.exists(TICKS_LOG_PATH)


def log_tick(symbol, price, sma_fast, sma_slow, signal, indicators=None):
    global _header_written
    indicators = indicators or {}
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "price": price,
        "sma_fast": sma_fast if sma_fast is not None else "",
        "sma_slow": sma_slow if sma_slow is not None else "",
        "rsi": indicators.get("rsi", ""),
        "macd": indicators.get("macd", ""),
        "macd_signal": indicators.get("macd_signal", ""),
        "bb_upper": indicators.get("bb_upper", ""),
        "bb_mid": indicators.get("bb_mid", ""),
        "bb_lower": indicators.get("bb_lower", ""),
        "stoch_k": indicators.get("stoch_k", ""),
        "stoch_d": indicators.get("stoch_d", ""),
        "williams_r": indicators.get("williams_r", ""),
        "roc": indicators.get("roc", ""),
        "signal": signal or "",
    }
    write_header = not _header_written
    with open(TICKS_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        if write_header:
            writer.writeheader()
            _header_written = True
        writer.writerow(row)
