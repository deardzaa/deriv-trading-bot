# Setup Bot di GitHub Actions (gratis, nggak perlu device nyala terus)

## Cara kerja
Bot ini **nggak jalan terus-terusan**. Tiap 15 menit, GitHub otomatis:
1. Nyalain "komputer virtual" sebentar
2. Jalanin `bot_once.py` — cek harga terakhir, putuskan CALL/PUT/skip, kalau ada
   sinyal langsung buka posisi
3. Simpan hasilnya balik ke repo kamu
4. Matiin komputer virtual itu

Jadi laptop/HP kamu nggak perlu nyala sama sekali setelah setup ini selesai.

## Langkah setup

### 1. Bikin akun & repo GitHub
1. Daftar di https://github.com (gratis)
2. Bikin repo baru: klik **New repository**
3. **Set ke Public** (bukan Private) — biar GitHub Actions gratis unlimited menit.
   Kalau Private, cuma dapat jatah 2000 menit/bulan gratis.
   
   ⚠️ Karena public, JANGAN pernah taruh token API langsung di kode. Semua token
   disimpan di **Secrets** (lihat langkah 3), itu aman dan nggak kelihatan orang lain.

### 2. Upload kode
Paling gampang lewat browser (nggak perlu install git):
1. Di halaman repo, klik **Add file > Upload files**
2. Extract `deriv_bot.zip` yang saya kasih, drag semua isinya (termasuk folder
   `.github`) ke situ
3. Klik **Commit changes**

### 3. Isi Secrets (token rahasia)
1. Di repo, buka **Settings > Secrets and variables > Actions**
2. Klik **New repository secret**, bikin:
   - Nama: `DERIV_API_TOKEN`, isi: token demo Deriv kamu
   - Nama: `DERIV_APP_ID`, isi: `1089` (atau app ID kamu sendiri)
   - Nama: `GEMINI_API_KEY`, isi: API key dari https://aistudio.google.com/apikey
     (gratis, tinggal login pakai akun Google)

### 4. Aktifkan Actions
1. Buka tab **Actions** di repo
2. Kalau muncul tombol "I understand my workflows, go ahead and enable them",
   klik itu
3. Kamu akan lihat 3 workflow: "Deriv Trading Bot", "Weekly Trading Summary", dan "Train AI Model"

### 5. Test manual dulu
1. Di tab Actions, klik "Deriv Trading Bot"
2. Klik **Run workflow** (kanan atas) untuk trigger manual, jangan nunggu jadwal
3. Tunggu ~1 menit, cek hasilnya — kalau ijo berarti sukses, kalau merah klik buat
   lihat error-nya (screenshot ke saya kalau bingung)

Setelah itu, bot otomatis jalan sendiri tiap 15 menit tanpa kamu sentuh lagi.

### 6. (Opsional) Aktifkan dashboard
Lihat bagian "Dashboard" di bawah buat aktifin GitHub Pages — sekali setup, dashboard-nya
selalu bisa diakses dari link tetap tanpa perlu diaktifin ulang.

## Yang perlu diperhatikan

- **Auto-mati setelah 60 hari nggak ada aktivitas commit** — ini kebijakan GitHub
  buat repo yang sepi. Kalau bot jalan terus (dan commit balik trades.json tiap
  run), ini nggak akan kena masalah ini karena selalu ada commit baru.
- **Jadwal bisa delay** beberapa menit saat GitHub lagi sibuk — ini normal, bukan
  bot-nya rusak.
- **Lihat histori & log** kapan aja di tab **Actions** — semua run tercatat di situ,
  termasuk kalau ada yang gagal.
- **Data trading** (`trades.json`, `ticks_dataset.csv`) otomatis ke-commit balik
  ke repo tiap run, jadi selalu bisa dicek dari GitHub langsung tanpa perlu buka
  device lain.

## Nge-training model AI (100% lewat GitHub, nggak perlu Python lokal)
1. Buka tab **Actions** di repo
2. Klik workflow **"Train AI Model"**
3. Klik **Run workflow**:
   - Kalau dataset kamu masih dikit dan mau langsung narik histori banyak dari Deriv,
     isi `fetch_fresh_history` = `yes` dan `history_count` = misal `5000`
   - Kalau dataset udah lumayan (dari bot yang jalan tiap 15 menit), biarin `no`
4. Tunggu proses selesai (~1-2 menit), model otomatis ke-commit ke repo sebagai `model.pkl`
5. Cek log run itu buat lihat angka akurasi model (klik run > klik job "train" > lihat output)
6. Kalau puas dengan akurasinya, edit `config.py` di GitHub (klik file > pensil icon buat edit),
   ganti `STRATEGY_MODE = "SMA"` jadi `STRATEGY_MODE = "AI"`, commit langsung dari browser
7. Bot otomatis pakai model itu di run berikutnya

Ulangi kapan aja mau update model dengan data terbaru — tinggal jalanin workflow ini lagi.

## Dashboard (100% lewat GitHub Pages, nggak perlu jalanin apa-apa)
1. Di repo, buka **Settings > Pages**
2. Di bagian **Source**, pilih **Deploy from a branch**
3. Branch: `main`, folder: `/docs`, klik **Save**
4. Tunggu 1-2 menit, GitHub kasih link (biasanya `https://<username>.github.io/<nama-repo>/`)
5. Buka link itu — dashboard bakal otomatis baca `trades.json` terbaru dari repo kamu
6. Bookmark link itu di HP, refresh kapan aja buat lihat data terkini (nggak auto-refresh
   sendiri karena ini halaman statis, tapi tinggal refresh manual)

Dashboard ini cuma bisa baca repo yang **public** (karena `raw.githubusercontent.com` nggak
bisa akses repo private tanpa autentikasi tambahan).
