"""
Kalkulasi indikator teknikal standar, dipakai sebagai "bahan" buat model AI
belajar — bukan cuma harga mentah, tapi hasil olahan indikator dulu (sesuai
pola: pasang indikator -> AI belajar dari situ -> AI yang mutusin).

Semua fungsi terima list harga (float), return None kalau datanya belum cukup.
"""
from statistics import stdev


def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _ema_series(prices, period):
    if len(prices) < period:
        return []
    k = 2 / (period + 1)
    ema_vals = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema_vals.append(price * k + ema_vals[-1] * (1 - k))
    return ema_vals


def rsi(prices, period=14):
    """Relative Strength Index, skala 0-100."""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = deltas[-period:]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def macd(prices, fast=12, slow=26, signal=9):
    """Return (macd_line, signal_line) — None kalau data belum cukup."""
    if len(prices) < slow + signal:
        return None, None
    ema_fast = _ema_series(prices, fast)
    ema_slow = _ema_series(prices, slow)
    min_len = min(len(ema_fast), len(ema_slow))
    if min_len == 0:
        return None, None
    macd_line = [ema_fast[-min_len:][i] - ema_slow[-min_len:][i] for i in range(min_len)]
    if len(macd_line) < signal:
        return round(macd_line[-1], 5), None
    signal_series = _ema_series(macd_line, signal)
    if not signal_series:
        return round(macd_line[-1], 5), None
    return round(macd_line[-1], 5), round(signal_series[-1], 5)


def bollinger_bands(prices, period=20, num_std=2):
    """Return (upper, mid, lower) — None kalau data belum cukup."""
    if len(prices) < period:
        return None, None, None
    window = prices[-period:]
    mid = sum(window) / period
    sd = stdev(window) if len(window) > 1 else 0
    upper = mid + num_std * sd
    lower = mid - num_std * sd
    return round(upper, 4), round(mid, 4), round(lower, 4)


def all_indicators(prices):
    """Hitung semua indikator sekaligus dari list harga, return dict."""
    upper, mid, lower = bollinger_bands(prices)
    macd_line, macd_signal_line = macd(prices)
    return {
        "rsi": rsi(prices),
        "macd": macd_line,
        "macd_signal": macd_signal_line,
        "bb_upper": upper,
        "bb_mid": mid,
        "bb_lower": lower,
    }
