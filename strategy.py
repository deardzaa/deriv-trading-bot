"""
Strategi trading sederhana: SMA crossover.
Ganti/upgrade fungsi decide() ini nanti kalau mau pasang model AI
yang dilatih dari dataset trades.json.
"""
from collections import deque
from config import SMA_FAST, SMA_SLOW


class SmaCrossoverStrategy:
    def __init__(self, fast=SMA_FAST, slow=SMA_SLOW):
        self.fast = fast
        self.slow = slow
        # buffer lebih panjang dari cuma SMA_SLOW, biar cukup buat indikator
        # lain yang butuh histori lebih banyak (MACD butuh ~35 titik)
        self.prices = deque(maxlen=max(slow, 50))

    def update(self, price: float):
        self.prices.append(price)

    def _sma(self, period: int):
        if len(self.prices) < period:
            return None
        vals = list(self.prices)[-period:]
        return sum(vals) / len(vals)

    def decide(self):
        """
        Return "CALL" (naik/RISE), "PUT" (turun/FALL), or None (belum ada sinyal).
        Logic: kalau SMA cepat baru saja melewati SMA lambat dari bawah -> CALL.
        Kalau dari atas -> PUT.
        """
        if len(self.prices) < self.slow + 1:
            return None

        fast_now = self._sma(self.fast)
        slow_now = self._sma(self.slow)

        prev_prices = list(self.prices)[:-1]
        if len(prev_prices) < self.slow:
            return None
        fast_prev = sum(prev_prices[-self.fast:]) / self.fast
        slow_prev = sum(prev_prices[-self.slow:]) / self.slow

        if fast_prev <= slow_prev and fast_now > slow_now:
            return "CALL"
        if fast_prev >= slow_prev and fast_now < slow_now:
            return "PUT"
        return None
