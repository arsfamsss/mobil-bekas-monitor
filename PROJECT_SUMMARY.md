# 🚗 Mobil Bekas Monitor Bot - Project Summary

## 📌 Overview

Bot Python canggih untuk memonitor listing mobil bekas secara real-time dari 4 marketplace terbesar di Indonesia. Bot berjalan otomatis 24/7 (via Termux/Server) dan mengirim notifikasi instan ke Telegram saat ditemukan mobil yang sesuai kriteria.

## 🌟 Fitur Utama

- **Multi-Platform Monitoring**: Mengecek 4 website sekaligus secara bergantian:
  - **OLX.co.id**
  - **Mobil123.com**
  - **Carmudi.co.id**
  - **Jualo.com**
- **Smart Filtering**:
  - Hanya Toyota Avanza/Veloz (filter akurat via `matcher.py`)
  - Tahun 2019-2021
  - Harga Rp 120jt - 190jt
  - KM Maksimal 60.000
  - Transmisi Manual
- **Prioritas & Scoring**:
  - **Plat F**: Mendapat skor prioritas tinggi (terdeteksi dari judul/deskripsi).
  - **Low KM**: Bonus skor untuk KM rendah.
- **Notifikasi Telegram**: Mengirim foto mobil, harga, lokasi, dan detail lengkap.
- **Anti-Duplicate**: Database SQLite mencegah notifikasi ganda untuk mobil yang sama.
- **Resilient**: Retry mechanism otomatis jika salah satu website error/down.

---

## 🏗️ update Troubleshooting & Kendala (Termux)

Selama pengembangan di platform **Android Termux**, ditemukan beberapa kendala teknis spesifik dan solusinya:

### 1. Blokir Network OLX (Anti-Bot)

- **Masalah**: OLX memblokir request API dari jaringan seluler/residential dengan error `Connection Reset` atau `Timeout`.
- **Solusi Terpilih**:
  - Menggunakan **CloudScraper** dengan profil **iOS/iPhone** untuk menyamar sebagai HP valid.
  - Tingkatkan **Timeout** menjadi 60 detik.
  - Mengalihkan beban ke platform lain (Mobil123/Carmudi) jika OLX macet.

### 2. Dependency `lxml` Gagal Install

- **Masalah**: Library `lxml` (parser HTML cepat) membutuhkan compile C++ yang sering gagal di Termux (`clang` error / `red build wheel`).
- **Solusi**: Mengganti semua parsing mechanism menggunakan `html.parser` bawaan Python. Lebih ringan dan 100% kompatibel Termux tanpa install library tambahan berat.

### 3. Struktur `main.py` & Import Error

- **Masalah**: Terjadi crash `AttributeError` karena sisa refactor code lama, dan `ImportError` karena salah nama class (`Matcher` vs `ListingMatcher`).
- **Solusi**: Rewriting total `main.py` dengan struktur modern yang meloop 4 fetcher secara dinamis dan fix import name.

---

## 🛠️ Cara Penggunaan (Termux)

### 1. Persiapan Awal

Pastikan sudah install: `python`, `git`, `tmux`.

```bash
pkg update && pkg upgrade -y
pkg install python git tmux -y
```

### 2. Clone & Install

```bash
git clone https://github.com/arsfamsss/mobil-bekas-monitor.git
cd mobil-bekas-monitor
pip install -r requirements.txt
```

### 3. Setup Konfig Otomatis

Saya sudah buatkan script helper agar tidak perlu edit manual:

```bash
# 1. Copy template dulu
cp .env.example .env

# 2. Isi Token Telegram (Wajib manual dikiit)
nano .env
# (Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID lalu Save Ctrl+O, Exit Ctrl+X)

# 3. Setup URL Search Otomatis
python setup_urls.py
# (Otomatis mengisi URL Mobil123/Carmudi/Jualo/OLX dengan filter Avanza)
```

### 4. Jalankan Bot

```bash
python main.py
```

### 5. Jalankan di Background (Biar HP bisa dipakai)

Gunakan `tmux`:

```bash
tmux new -s botmobil
python main.py
# Lalu tekan Ctrl+B, lepas, tekan D (Detach)
```

Untuk melihat bot lagi: `tmux attach -t botmobil`

---

## 📂 Struktur File

- `main.py`: Otak utama bot (looping & koordinasi).
- `config.py`: Pengaturan (Token, URL, Timeout).
- `matcher.py`: Logika filter ("Apakah ini Avanza?", "Apakah Plat F?").
- `storage.py`: Database ingatan bot (agar tidak lupa listing yang sudah dikirim).
- `*_fetcher.py`: Skrip khusus untuk mengambil data dari masing-masing website.
- `notifier_telegram.py`: Tukang kirim pesan ke HP Anda.
