"""
Strategi berbasis model AI (dilatih oleh train_model.py).
Dipakai kalau STRATEGY_MODE = "AI" di config.py.

Fitur yang dipakai model: histori perubahan harga (lag), SMA gap, RSI, MACD
histogram, Bollinger Bands, Stochastic Oscillator, Williams %R, Rate of
Change — fitur yang beneran dipakai ditentuin dari feature_cols yang
disimpan di model.pkl (jadi otomatis cocok, model lama/baru sama-sama jalan).
"""
import os
from collections import deque
import joblib

from config import AI_LOOKBACK, AI_MIN_CONFIDENCE, MODEL_PATH
import indicators as ind


class AiStrategy:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model AI belum ada di {MODEL_PATH}. Jalankan `python train_model.py` dulu."
            )
        bundle = joblib.load(MODEL_PATH)
        self.model = bundle["model"]
        self.feature_cols = bundle["feature_cols"]
        # buffer cukup panjang buat semua indikator (MACD butuh paling banyak, ~35)
        self.prices = deque(maxlen=max(AI_LOOKBACK + 25, 50))
        self.fast = 5
        self.slow = 20

    def update(self, price: float):
        self.prices.append(price)

    def _sma(self, period):
        if len(self.prices) < period:
            return None
        vals = list(self.prices)[-period:]
        return sum(vals) / len(vals)

    def _build_feature_row(self):
        prices = list(self.prices)
        last_price = prices[-1]

        row = {}
        for lag in range(1, AI_LOOKBACK + 1):
            if len(prices) > lag:
                row[f"lag_{lag}"] = last_price - prices[-1 - lag]
            else:
                return None  # belum cukup data

        fast = self._sma(self.fast)
        slow = self._sma(self.slow)
        row["sma_gap"] = (fast - slow) if (fast is not None and slow is not None) else None

        tech = ind.all_indicators(prices)
        row["rsi"] = tech["rsi"]

        macd_line, macd_signal = tech["macd"], tech["macd_signal"]
        row["macd_hist"] = (macd_line - macd_signal) if (macd_line is not None and macd_signal is not None) else None

        upper, lower = tech["bb_upper"], tech["bb_lower"]
        if upper is not None and lower is not None and (upper - lower) != 0:
            row["bb_percent"] = (last_price - lower) / (upper - lower)
            row["bb_width"] = upper - lower
        else:
            row["bb_percent"] = None
            row["bb_width"] = None

        row["stoch_k"] = tech["stoch_k"]
        row["stoch_d"] = tech["stoch_d"]
        row["williams_r"] = tech["williams_r"]
        row["roc"] = tech["roc"]

        if any(row.get(c) is None for c in self.feature_cols):
            return None  # ada fitur yang belum bisa dihitung (data belum cukup)

        return row

    def decide(self):
        row = self._build_feature_row()
        if row is None:
            return None

        import pandas as pd
        X = pd.DataFrame([[row[c] for c in self.feature_cols]], columns=self.feature_cols)
        proba = self.model.predict_proba(X)[0]  # [P(down), P(up)]
        p_up, p_down = proba[1], proba[0]

        if p_up >= AI_MIN_CONFIDENCE:
            return "CALL"
        if p_down >= AI_MIN_CONFIDENCE:
            return "PUT"
        return None  # model nggak cukup yakin, skip trade
