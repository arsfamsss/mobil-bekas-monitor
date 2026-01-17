# 🚗 Bot Monitor Mobil Bekas

Bot Python untuk memonitor listing mobil bekas di OLX dengan notifikasi Telegram.  
Berjalan di Android Termux atau Windows/Linux.

## ✨ Fitur

- ✅ Monitor listing OLX secara otomatis
- ✅ Filter berdasarkan: model, tahun, harga, KM, transmisi, warna
- ✅ Notifikasi Telegram dengan foto
- ✅ Deduplication (tidak spam listing yang sama)
- ✅ Rate limiting (max 10 notif/jam)
- ✅ Anti-spam error notification
- ✅ Deteksi plat nomor (prioritas plat F)
- ✅ Scoring system untuk prioritas listing

## 📁 Struktur Proyek

```
Mobil Bekas Monitor/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── logs/                      # Log files (gitignored)
├── tests/
│   ├── __init__.py
│   └── test_matcher.py        # Unit tests
├── .env.example               # Template environment
├── .env                       # Konfigurasi (JANGAN COMMIT!)
├── .gitignore
├── config.py                  # Configuration loader
├── storage.py                 # SQLite dedup & history
├── olx_fetcher.py             # OLX scraper
├── matcher.py                 # Filter & scoring
├── notifier_telegram.py       # Telegram sender
├── main.py                    # Main entrypoint
├── requirements.txt
└── README.md
```

---

## 🚀 Instalasi di Termux (Android)

### 1. Install Termux

Download dari [F-Droid](https://f-droid.org/packages/com.termux/) (JANGAN dari Play Store).

### 2. Setup Termux

```bash
# Update packages
pkg update && pkg upgrade -y

# Install dependencies
pkg install python git tmux -y

# Install pip (jika belum ada)
pip install --upgrade pip
```

### 3. Clone Repository

```bash
# Masuk ke folder home
cd ~

# Clone dari GitHub (ganti dengan URL repo Anda)
git clone https://github.com/USERNAME/mobil-bekas-monitor.git

# Masuk ke folder proyek
cd mobil-bekas-monitor
```

### 4. Install Dependencies Python

```bash
pip install -r requirements.txt
```

### 5. Konfigurasi Environment

```bash
# Copy template
cp .env.example .env

# Edit .env dengan nano atau vim
nano .env
```

Isi nilai berikut di `.env`:

```ini
# Token dari @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Chat ID Anda (dapatkan dari @userinfobot)
TELEGRAM_CHAT_ID=215339913

# URL pencarian OLX
OLX_SEARCH_URL=https://www.olx.co.id/mobil-bekas_c198/q-avanza-veloz?filter=...
```

### 6. Jalankan Bot

```bash
python main.py
```

### 7. Jalankan di Background dengan tmux

```bash
# Buat session baru
tmux new -s mobil-monitor

# Jalankan bot
python main.py

# Detach dari session: tekan Ctrl+B lalu D

# Untuk kembali ke session:
tmux attach -t mobil-monitor

# Untuk list semua sessions:
tmux ls

# Untuk stop bot:
tmux attach -t mobil-monitor
# Lalu tekan Ctrl+C
```

---

## 💻 Instalasi di Windows

### 1. Install Python

Download dari [python.org](https://www.python.org/downloads/) (versi 3.10+).  
Pastikan centang "Add Python to PATH" saat instalasi.

### 2. Clone/Download Repository

```powershell
# Via Git
git clone https://github.com/USERNAME/mobil-bekas-monitor.git
cd mobil-bekas-monitor

# Atau download ZIP dan extract
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Konfigurasi Environment

```powershell
# Copy template
copy .env.example .env

# Edit .env dengan Notepad atau VSCode
notepad .env
```

### 5. Jalankan Bot

```powershell
python main.py
```

---

## 📱 Setup Telegram Bot

### 1. Buat Bot Baru

1. Buka Telegram, cari [@BotFather](https://t.me/BotFather)
2. Ketik `/newbot`
3. Ikuti instruksi untuk memberi nama bot
4. Simpan **token** yang diberikan

### 2. Dapatkan Chat ID

1. Cari [@userinfobot](https://t.me/userinfobot) di Telegram
2. Ketik `/start`
3. Bot akan membalas dengan **Chat ID** Anda

### 3. Test Bot

Kirim pesan ke bot Anda, lalu cek dengan:

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

---

## 🔧 Konfigurasi

Semua konfigurasi ada di file `.env`:

| Variable                     | Deskripsi                   | Default   |
| ---------------------------- | --------------------------- | --------- |
| `TELEGRAM_BOT_TOKEN`         | Token bot Telegram          | (wajib)   |
| `TELEGRAM_CHAT_ID`           | Chat ID untuk notifikasi    | (wajib)   |
| `OLX_SEARCH_URL`             | URL pencarian OLX           | (wajib)   |
| `CHECK_INTERVAL_SECONDS`     | Interval pengecekan (detik) | 180       |
| `MAX_NOTIFICATIONS_PER_HOUR` | Max notifikasi per jam      | 10        |
| `FILTER_MIN_YEAR`            | Tahun minimum               | 2019      |
| `FILTER_MAX_YEAR`            | Tahun maximum               | 2021      |
| `FILTER_MIN_PRICE`           | Harga minimum (Rp)          | 120000000 |
| `FILTER_MAX_PRICE`           | Harga maximum (Rp)          | 190000000 |
| `FILTER_MAX_KM`              | Kilometer maximum           | 60000     |
| `LOG_LEVEL`                  | Level logging               | INFO      |

---

## 🧪 Testing

```bash
# Jalankan semua tests
pytest tests/ -v

# Jalankan dengan coverage
pytest tests/ -v --cov=.

# Lint dengan ruff
ruff check .
```

---

## 📤 Push ke GitHub

### 1. Buat Repository di GitHub

1. Buka [github.com/new](https://github.com/new)
2. Buat repository baru (misal: `mobil-bekas-monitor`)
3. Jangan tambahkan README/gitignore (sudah ada)

### 2. Push dari Lokal

```bash
# Initialize git (jika belum)
git init

# Add remote
git remote add origin https://github.com/USERNAME/mobil-bekas-monitor.git

# Add semua file
git add .

# Commit
git commit -m "Initial commit: OLX Monitor Bot"

# Push
git push -u origin main
```

### 3. Setup GitHub Secrets (Opsional)

Untuk CI/CD, tambahkan secrets di repository:

1. Buka **Settings** > **Secrets and variables** > **Actions**
2. Tambahkan:
   - `TELEGRAM_BOT_TOKEN` (opsional, untuk testing)
   - `TELEGRAM_CHAT_ID` (opsional, untuk testing)

---

## 🔄 GitHub Actions CI

Repository sudah dilengkapi dengan GitHub Actions untuk:

- ✅ Lint dengan `ruff`
- ✅ Unit test dengan `pytest`

CI akan berjalan otomatis setiap push atau pull request.

---

## 🛠️ Troubleshooting

### Bot tidak menemukan listing

1. Cek URL OLX valid dengan membukanya di browser
2. OLX mungkin mengubah struktur HTML - update selector di `olx_fetcher.py`
3. Cek log di `logs/bot.log`

### Gagal kirim notifikasi Telegram

1. Pastikan token dan chat ID benar
2. Pastikan sudah `/start` di bot Telegram
3. Cek koneksi internet

### Rate limit tercapai

Bot akan otomatis stop notifikasi jika >10 notif/jam.  
Tunggu 1 jam atau sesuaikan `MAX_NOTIFICATIONS_PER_HOUR`.

### Error parsing

OLX mungkin mengubah struktur. Update selector di bagian `SELECTORS` di `olx_fetcher.py`.

---

## 📜 License

MIT License - bebas digunakan dan dimodifikasi.

---

## 👨‍💻 Kontributor

- Bot dibuat dengan ❤️ untuk mencari Avanza impian Anda!
