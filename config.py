"""
Konfigurasi bot. Isi DERIV_API_TOKEN dengan token DEMO kamu.
Cara ambil token demo:
1. Login ke https://app.deriv.com dengan akun DEMO (bukan real)
2. Buka https://app.deriv.com/account/api-token
3. Buat token baru dengan scope: Read, Trade
4. Copy token itu ke file .env (lihat .env.example)
"""
import os
from dotenv import load_dotenv

load_dotenv()

DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "")
APP_ID = os.getenv("DERIV_APP_ID", "1089")  # 1089 = app_id publik default Deriv untuk testing

SYMBOL = "R_100"          # instrumen yang ditrade
STAKE = 1.0                # USD per trade (base stake, dipakai lagi tiap reset Martingale)
DURATION = 60               # durasi kontrak (detik)
DURATION_UNIT = "s"

# Martingale: kalau kalah, stake berikutnya dinaikin biar sekali menang bisa
# nutup rugi + untung sedikit. RISIKO TINGGI - baca README sebelum diaktifin.
# Reset ke stake awal kalau MENANG, atau kalau udah kalah MARTINGALE_MAX_STEPS
# kali berturut-turut (biar nggak bablas).
ENABLE_MARTINGALE = False
MARTINGALE_MAX_STEPS = 3
# Batas keamanan mutlak - stake nggak akan pernah lebih dari STAKE dikali
# angka ini, apapun yang terjadi (jaga-jaga kalau ada estimasi payout yang
# meleset atau bug).
MARTINGALE_MAX_MULTIPLIER = 10

SMA_FAST = 5
SMA_SLOW = 20

# "SMA" = strategi rule-based bawaan (1 indikator). "MULTI" = voting/consensus
# banyak indikator sekaligus. "AI" = pakai model hasil train_model.py.
# Jangan set "AI" sebelum ada model.pkl (jalankan train_model.py dulu setelah
# dataset ticks_dataset.csv cukup banyak, minimal ribuan baris).
STRATEGY_MODE = "SMA"
MULTI_MIN_CONSENSUS = 5  # dari 7 indikator, minimal berapa yang harus sepakat
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
AI_LOOKBACK = 10       # berapa tick terakhir dipakai sebagai fitur
AI_MIN_CONFIDENCE = 0.60  # minimal probabilitas biar model mau ambil posisi

# Horizon prediksi HARUS match durasi kontrak beneran (DURATION di atas),
# bukan cuma "tick berikutnya" - kalau nggak, model belajar soal yang beda
# dari yang beneran ditradingkan. R_100 standard tick tiap ~2 detik.
TICK_INTERVAL_SECONDS = 2
PREDICTION_HORIZON_TICKS = max(1, round(DURATION / TICK_INTERVAL_SECONDS))

# Batas harian - bot berhenti buka posisi baru kalau salah satu tercapai.
# Trade yang udah OPEN tetap dibiarkan settle secara normal, cuma nggak ada
# entry baru sampai hari berikutnya (WIB/UTC tergantung server, lihat catatan
# di GITHUB_SETUP.md).
DAILY_LOSS_LIMIT = -10.0   # berhenti kalau rugi harian sudah mencapai ini (negatif)
DAILY_PROFIT_LIMIT = 15.0  # berhenti kalau untung harian sudah mencapai ini (positif)
ENABLE_DAILY_LIMITS = True
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
HISTORY_TICKS_COUNT = 60  # berapa tick historis ditarik tiap run buat hitung sinyal

# Gemini — dipakai HANYA buat rangkuman mingguan, BUKAN buat keputusan trade
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

TRADES_LOG_PATH = os.path.join(os.path.dirname(__file__), "trades.json")
TICKS_LOG_PATH = os.path.join(os.path.dirname(__file__), "ticks_dataset.csv")
SHADOW_LOG_PATH = os.path.join(os.path.dirname(__file__), "shadow_predictions.json")

# SAFETY: bot ini defaultnya hanya boleh jalan di akun DEMO.
# Set ke True hanya kalau kamu benar-benar paham risikonya dan mau pakai akun real.
ALLOW_REAL_ACCOUNT = False
