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


def stochastic_oscillator(prices, period=14, smooth=3):
    """Stochastic %K dan %D, skala 0-100. Karena data kita cuma tick (bukan
    OHLC candle), highest/lowest dihitung dari rolling window harga tick."""
    if len(prices) < period + smooth:
        return None, None
    k_values = []
    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        highest, lowest = max(window), min(window)
        if highest == lowest:
            k_values.append(50.0)
        else:
            k_values.append((prices[i] - lowest) / (highest - lowest) * 100)
    if len(k_values) < smooth:
        return round(k_values[-1], 2), None
    d_value = sum(k_values[-smooth:]) / smooth
    return round(k_values[-1], 2), round(d_value, 2)


def williams_r(prices, period=14):
    """Williams %R, skala -100 sampai 0."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    highest, lowest = max(window), min(window)
    if highest == lowest:
        return -50.0
    return round((highest - prices[-1]) / (highest - lowest) * -100, 2)


def rate_of_change(prices, period=10):
    """ROC: persentase perubahan harga dibanding N tick lalu."""
    if len(prices) < period + 1:
        return None
    old_price = prices[-1 - period]
    if old_price == 0:
        return None
    return round((prices[-1] - old_price) / old_price * 100, 4)


def all_indicators(prices):
    """Hitung semua indikator sekaligus dari list harga, return dict."""
    upper, mid, lower = bollinger_bands(prices)
    macd_line, macd_signal_line = macd(prices)
    stoch_k, stoch_d = stochastic_oscillator(prices)
    return {
        "rsi": rsi(prices),
        "macd": macd_line,
        "macd_signal": macd_signal_line,
        "bb_upper": upper,
        "bb_mid": mid,
        "bb_lower": lower,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "williams_r": williams_r(prices),
        "roc": rate_of_change(prices),
    }
