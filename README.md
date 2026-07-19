# Flyonz Quant — Deriv Demo Trading Bot

Bot trading otomatis untuk akun **DEMO** Deriv (binary options RISE/FALL) + dashboard live, mirip
dengan yang ada di screenshot referensi.

## ⚠️ Peringatan penting
- Bot ini **dikunci ke akun demo**. Kalau token yang kamu pakai ternyata akun real, bot akan
  langsung berhenti (lihat `config.py` -> `ALLOW_REAL_ACCOUNT`).
- Binary options / options trading punya risiko kehilangan modal yang tinggi. Win rate historis
  di data demo **tidak menjamin** hasil yang sama di masa depan atau di akun real.
- Ini bukan nasihat keuangan. Semua keputusan trading tanggung jawab kamu sendiri.
- Strategi default (SMA crossover) itu contoh dasar, bukan strategi yang sudah terbukti profitable.

## Struktur project
```
deriv_bot/
├── config.py          # konfigurasi (symbol, stake, durasi, dst)
├── strategy.py         # logic sinyal trading (ganti ini kalau mau pasang model AI)
├── trade_logger.py      # nyimpen histori trade ke trades.json
├── deriv_bot.py         # bot utama, connect ke Deriv WebSocket API
├── dashboard.py         # server Flask untuk dashboard live
├── templates/dashboard.html
├── requirements.txt
└── .env.example
```

## Setup
1. Buat akun demo di https://app.deriv.com (kalau belum punya)
2. Ambil API token demo di https://app.deriv.com/account/api-token (scope: Read + Trade)
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` jadi `.env`, isi token kamu:
   ```
   cp .env.example .env
   ```
5. Jalankan bot (terminal 1):
   ```
   python deriv_bot.py
   ```
6. Jalankan dashboard (terminal 2):
   ```
   python dashboard.py
   ```
   lalu buka http://localhost:5000

## Ganti pengaturan
Edit `config.py`:
- `SYMBOL` — instrumen (default `R_100`)
- `STAKE` — nominal stake per trade
- `DURATION` / `DURATION_UNIT` — durasi kontrak
- `SMA_FAST` / `SMA_SLOW` — parameter strategi
- `DAILY_LOSS_LIMIT` / `DAILY_PROFIT_LIMIT` — batas rugi/untung harian, bot
  otomatis berhenti buka posisi baru kalau salah satu tercapai (trade yang
  udah terbuka tetap dibiarkan settle normal)

## Indikator teknikal yang dipakai model AI
Model belajar dari kombinasi fitur berikut (bukan cuma harga mentah):
- **Lag harga** — perubahan harga 1-10 tick terakhir
- **SMA gap** — selisih moving average cepat vs lambat
- **RSI** — kekuatan momentum (0-100)
- **MACD histogram** — selisih garis MACD vs signal line-nya
- **Bollinger Bands** — posisi harga relatif dalam band (`bb_percent`) dan lebar band (`bb_width`)

Semua ini dihitung otomatis oleh `indicators.py` dan disimpan tiap tick ke
`ticks_dataset.csv`, jadi setiap kali `train_model.py` dijalankan, modelnya
belajar dari kombinasi indikator-indikator ini, bukan cuma dari SMA doang.

## Soal fitur "AI learning" di post kamu
Bot ini masih pakai strategi rule-based (SMA crossover), bukan model AI. `trades.json` yang
dihasilkan bot ini bisa dipakai sebagai dataset awal (fitur: harga entry, waktu, hasil menang/kalah)
kalau nanti mau melatih model klasifikasi (misalnya logistic regression / random forest) untuk
prediksi CALL/PUT. Itu langkah terpisah — kasih tahu saya kalau mau saya bantu bagian itu juga.
