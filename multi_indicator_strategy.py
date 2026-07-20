"""
Strategi rule-based yang menggabungkan BANYAK indikator sekaligus (bukan cuma
SMA doang), pakai sistem voting/consensus. Beda dari AI (yang belajar bobot
sendiri dari data), ini aturan teknikal analysis klasik yang digabung manual.

Kenapa dibikin: SMA crossover doang gampang kena sinyal palsu (whipsaw) -
harga nyerempet garis SMA sebentar terus balik lagi. Idenya di sini: sinyal
baru dianggap valid kalau BANYAK indikator kompak setuju arah yang sama,
bukan cuma satu doang.

Aturan tiap indikator ("vote" UP/DOWN/abstain):
- SMA: fast > slow -> UP, fast < slow -> DOWN
- RSI: <30 (oversold, ekspektasi reversal naik) -> UP, >70 -> DOWN
- MACD: histogram positif -> UP, negatif -> DOWN
- Bollinger Bands: harga nyentuh/lewat lower band -> UP, upper band -> DOWN
- Stochastic: %K <20 (oversold) -> UP, >80 (overbought) -> DOWN
- Williams %R: <-80 (oversold) -> UP, >-20 (overbought) -> DOWN
- ROC: positif (momentum naik) -> UP, negatif -> DOWN
"""
from collections import deque
import indicators as ind


class MultiIndicatorStrategy:
    def __init__(self, min_consensus=5, fast=5, slow=20):
        self.prices = deque(maxlen=60)
        self.fast = fast
        self.slow = slow
        self.min_consensus = min_consensus  # minimal berapa indikator sepakat

    def update(self, price: float):
        self.prices.append(price)

    def _sma(self, period):
        if len(self.prices) < period:
            return None
        vals = list(self.prices)[-period:]
        return sum(vals) / len(vals)

    def get_votes(self):
        """Return dict {nama_indikator: 'UP'/'DOWN'/None (abstain)}."""
        prices = list(self.prices)
        votes = {}

        fast = self._sma(self.fast)
        slow = self._sma(self.slow)
        votes["sma"] = ("UP" if fast > slow else "DOWN") if (fast is not None and slow is not None) else None

        if len(prices) < 10:
            return votes  # belum cukup data buat indikator lain

        tech = ind.all_indicators(prices)

        rsi = tech["rsi"]
        if rsi is None:
            votes["rsi"] = None
        elif rsi < 30:
            votes["rsi"] = "UP"
        elif rsi > 70:
            votes["rsi"] = "DOWN"
        else:
            votes["rsi"] = None

        macd, macd_signal = tech["macd"], tech["macd_signal"]
        votes["macd"] = ("UP" if macd > macd_signal else "DOWN") if (macd is not None and macd_signal is not None) else None

        upper, lower = tech["bb_upper"], tech["bb_lower"]
        last = prices[-1]
        if upper is None or lower is None:
            votes["bb"] = None
        elif last <= lower:
            votes["bb"] = "UP"
        elif last >= upper:
            votes["bb"] = "DOWN"
        else:
            votes["bb"] = None

        stoch_k = tech["stoch_k"]
        if stoch_k is None:
            votes["stoch"] = None
        elif stoch_k < 20:
            votes["stoch"] = "UP"
        elif stoch_k > 80:
            votes["stoch"] = "DOWN"
        else:
            votes["stoch"] = None

        wr = tech["williams_r"]
        if wr is None:
            votes["williams_r"] = None
        elif wr < -80:
            votes["williams_r"] = "UP"
        elif wr > -20:
            votes["williams_r"] = "DOWN"
        else:
            votes["williams_r"] = None

        roc = tech["roc"]
        if roc is None:
            votes["roc"] = None
        elif roc > 0:
            votes["roc"] = "UP"
        elif roc < 0:
            votes["roc"] = "DOWN"
        else:
            votes["roc"] = None

        return votes

    def decide(self):
        votes = self.get_votes()
        up_count = sum(1 for v in votes.values() if v == "UP")
        down_count = sum(1 for v in votes.values() if v == "DOWN")

        if up_count >= self.min_consensus and up_count > down_count:
            return "CALL"
        if down_count >= self.min_consensus and down_count > up_count:
            return "PUT"
        return None
