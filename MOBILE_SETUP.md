# Cara Build & Jalanin Bot Ini 100% dari HP (Termux)

Semua langkah ini dikerjain di HP Android, nggak perlu PC. Estimasi waktu ~20-30 menit
kalau baru pertama kali.

## 1. Install Termux
- Jangan install dari Play Store (versinya udah nggak di-update).
- Install dari **F-Droid**: https://f-droid.org/packages/com.termux/
  (install F-Droid dulu kalau belum ada, lalu cari "Termux" di dalamnya)

## 2. Setup dasar Termux
Buka Termux, jalankan satu-satu (Enter setelah tiap baris):
```
termux-setup-storage
pkg update -y && pkg upgrade -y
pkg install python git zip -y
```
`termux-setup-storage` bakal munculin izin akses storage — tap **Allow**.

## 3. Ambil kode bot
Kamu punya 2 opsi:

**Opsi A — download zip yang saya kasih:**
1. Download `deriv_bot.zip` dari chat ini ke folder Download HP kamu
2. Di Termux:
   ```
   cd ~
   cp /sdcard/Download/deriv_bot.zip .
   unzip deriv_bot.zip
   cd deriv_bot
   ```

**Opsi B — kalau saya push ke GitHub (bilang aja kalau mau saya buatkan repo):**
```
git clone <url_repo>
cd deriv_bot
```

## 4. Install dependencies Python
```
pip install -r requirements.txt
```
Kalau ada error pas install `websockets` (butuh compile), jalankan dulu:
```
pkg install clang rust -y
```
lalu ulangi `pip install -r requirements.txt`.

## 5. Isi token API demo Deriv
1. Buka browser HP, login ke https://app.deriv.com pakai akun **DEMO**
2. Buka https://app.deriv.com/account/api-token
3. Buat token baru, centang scope **Read** + **Trade**, generate
4. Copy token itu
5. Balik ke Termux:
   ```
   cp .env.example .env
   nano .env
   ```
6. Ganti `isi_token_demo_kamu_disini` dengan token kamu. Simpan: `Ctrl+O`, Enter, lalu `Ctrl+X` keluar.

## 6. Jalankan bot
Termux bisa buka beberapa sesi sekaligus — geser dari kiri layar (swipe from left edge) buat buka menu, pilih "New session".

**Sesi 1 (bot):**
```
cd ~/deriv_bot
python deriv_bot.py
```

**Sesi 2 (dashboard):**
```
cd ~/deriv_bot
python dashboard.py
```

## 7. Lihat dashboard
Buka browser di HP yang sama, ketik:
```
http://127.0.0.1:5000
```
Dashboard bakal nampilin Net P&L, Win/Loss, Win Rate, dan jumlah data yang udah kekumpul buat AI.

## 8. Biar bot tetap jalan meski HP dikunci
Termux bakal ke-kill kalau HP dikunci lama, kecuali:
- Aktifkan "wake lock" di Termux: swipe notifikasi Termux ke bawah, tap ikon lock
- Atau matikan battery optimization untuk Termux: Settings > Apps > Termux > Battery > Unrestricted

## 9. Aktifin mode AI (setelah data cukup banyak)
Bot defaultnya pakai strategi SMA (rule-based). Buat pakai AI:

1. Biarin bot jalan beberapa hari dulu biar `ticks_dataset.csv` kekumpul banyak
   (idealnya ribuan baris — makin banyak makin baik).
2. Stop bot (`Ctrl+C` di sesi bot).
3. Latih model:
   ```
   python train_model.py
   ```
   Ini bakal nampilin akurasi model di data yang belum pernah dilihat (out-of-sample).
   **Perhatikan angkanya**: kalau akurasi cuma sedikit di atas 50%, artinya modelnya
   nggak jauh beda dari nebak koin — itu wajar untuk instrumen synthetic index kayak
   R_100 yang memang didesain random. Jangan dipaksa dipakai kalau akurasinya rendah.
4. Kalau mau tetap coba, edit `config.py`:
   ```
   nano config.py
   ```
   ganti `STRATEGY_MODE = "SMA"` jadi `STRATEGY_MODE = "AI"`. Simpan (`Ctrl+O`, Enter, `Ctrl+X`).
5. Jalankan ulang bot: `python deriv_bot.py` — bakal muncul log "Mode: AI (pakai model.pkl)".
6. Kapan aja mau balik ke SMA, ganti lagi `STRATEGY_MODE = "SMA"`.

**Catatan buat HP**: install `pandas` dan `scikit-learn` di Termux kadang lambat karena
compile dari source (bisa 10-20 menit, tergantung HP). Kalau gagal/stuck lama, kasih tau saya
error-nya, atau alternatifnya latih modelnya sekali di komputer/laptop teman lalu copy file
`model.pkl` yang dihasilkan ke folder `deriv_bot` di HP kamu — bot di HP tetap bisa pakai model
itu tanpa perlu re-train di HP.

## 10. Ambil dataset yang udah kekumpul
File `ticks_dataset.csv` di folder `deriv_bot` isinya data harga mentah (timestamp, harga,
SMA, sinyal) yang kekumpul otomatis tiap tick — ini yang bisa dipakai buat training model AI
nanti. Cek isinya:
```
cat ticks_dataset.csv | head -20
```

## Kalau stuck
Screenshot error-nya di Termux, kirim ke saya di chat ini, saya bantu debug.

---
⚠️ **Ingat**: bot ini terkunci ke akun DEMO. Trading options berisiko tinggi, ini bukan saran
finansial, dan hasil demo nggak menjamin hasil sama di real.
