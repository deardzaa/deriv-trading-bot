"""
Strategi berbasis ARIMA (AutoRegressive Integrated Moving Average) - model
matematis klasik buat forecasting time series, BEDA dari ML (yang belajar
pola dari data lewat banyak fitur) dan BEDA dari aturan indikator (yang pakai
rule tetap). ARIMA murni model statistik yang "fit" ke deret harga itu
sendiri, lalu forecast titik berikutnya berdasarkan struktur matematisnya.

Cara kerja singkat:
- AR (AutoRegressive): harga sekarang dijelaskan dari harga-harga sebelumnya
- I (Integrated): differencing buat bikin deret jadi stasioner (biar valid
  dianalisis) - order=1 cocok buat data yang mirip random walk
- MA (Moving Average): harga sekarang juga dijelaskan dari error forecast
  sebelumnya

CATATAN PENTING: kalau data beneran random walk murni (ARIMA(0,1,0)), model
ARIMA apa pun secara matematis akan konvergen ke "forecast = harga terakhir"
- artinya nggak ada prediksi yang lebih baik dari "diam aja". Ini bukan
  kelemahan ARIMA, tapi konsekuensi matematis dari sifat data itu sendiri.
"""
import warnings
from collections import deque

warnings.filterwarnings("ignore")  # statsmodels suka berisik soal konvergensi


class ArimaStrategy:
    def __init__(self, order=(1, 1, 1), window=50, min_move_threshold=0.01):
        self.prices = deque(maxlen=window)
        self.order = order
        self.window = window
        # minimal seberapa besar forecast harus beda dari harga sekarang
        # biar dianggap sinyal valid (bukan noise forecast yang kecil banget)
        self.min_move_threshold = min_move_threshold
        self.fast = 5   # buat kompatibilitas logging (dipakai bot_once.py)
        self.slow = 20

    def update(self, price: float):
        self.prices.append(price)

    def _sma(self, period):
        if len(self.prices) < period:
            return None
        vals = list(self.prices)[-period:]
        return sum(vals) / len(vals)

    def forecast(self, steps=1):
        """Return harga hasil forecast N langkah ke depan, atau None kalau
        data belum cukup / model gagal fit."""
        if len(self.prices) < self.window:
            return None
        try:
            from statsmodels.tsa.arima.model import ARIMA
            data = list(self.prices)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ARIMA(data, order=self.order)
                fitted = model.fit()
                forecast_result = fitted.forecast(steps=steps)
            return float(forecast_result[-1])
        except Exception:
            return None  # ARIMA kadang gagal konvergen, itu wajar - skip aja

    def decide(self):
        if len(self.prices) < self.window:
            return None
        last_price = self.prices[-1]
        predicted = self.forecast(steps=1)
        if predicted is None:
            return None

        move = predicted - last_price
        move_pct = abs(move) / last_price if last_price else 0
        if move_pct < self.min_move_threshold / 100:
            return None  # forecast-nya kedeketan banget, nggak signifikan

        return "CALL" if move > 0 else "PUT"
