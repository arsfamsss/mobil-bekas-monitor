"""
config.py - Konfigurasi dan Environment Loader

Memuat semua konfigurasi dari file .env dengan default values.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class Config:
    """Konfigurasi aplikasi dari environment variables."""

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')

    # Search URLs
    OLX_SEARCH_URL: str = os.getenv(
        'OLX_SEARCH_URL',
        'https://www.olx.co.id/mobil-bekas_c198/q-avanza-veloz'
    )

    # Timing Configuration
    CHECK_INTERVAL_SECONDS: int = int(os.getenv('CHECK_INTERVAL_SECONDS', '180'))

    # Rate Limiting
    MAX_NOTIFICATIONS_PER_HOUR: int = int(os.getenv('MAX_NOTIFICATIONS_PER_HOUR', '10'))
    MAX_ERROR_NOTIFICATIONS_PER_HOUR: int = 1  # Fixed, tidak perlu konfigurasi

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'mobil_monitor.db')

    # Filter Criteria (bisa di-override via env jika mau)
    FILTER_MIN_YEAR: int = int(os.getenv('FILTER_MIN_YEAR', '2019'))
    FILTER_MAX_YEAR: int = int(os.getenv('FILTER_MAX_YEAR', '2021'))
    FILTER_MIN_PRICE: int = int(os.getenv('FILTER_MIN_PRICE', '120000000'))
    FILTER_MAX_PRICE: int = int(os.getenv('FILTER_MAX_PRICE', '190000000'))
    FILTER_MAX_KM: int = int(os.getenv('FILTER_MAX_KM', '60000'))
    FILTER_TRANSMISSION: str = os.getenv('FILTER_TRANSMISSION', 'manual').lower()
    FILTER_COLOR: str = os.getenv('FILTER_COLOR', 'putih').lower()

    # Request Configuration
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    USER_AGENT: str = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    )

    @classmethod
    def validate(cls) -> list[str]:
        """Validasi konfigurasi wajib. Return list error jika ada."""
        errors = []

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN tidak diset di .env")

        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID tidak diset di .env")

        if not cls.OLX_SEARCH_URL:
            errors.append("OLX_SEARCH_URL tidak diset di .env")

        return errors

    @classmethod
    def print_config(cls) -> None:
        """Print konfigurasi untuk debugging (tanpa token)."""
        print("=" * 50)
        print("KONFIGURASI BOT")
        print("=" * 50)
        print(f"OLX URL: {cls.OLX_SEARCH_URL[:50]}...")
        print(f"Check Interval: {cls.CHECK_INTERVAL_SECONDS} detik")
        print(f"Max Notif/Jam: {cls.MAX_NOTIFICATIONS_PER_HOUR}")
        print(f"Filter Tahun: {cls.FILTER_MIN_YEAR}-{cls.FILTER_MAX_YEAR}")
        print(f"Filter Harga: {cls.FILTER_MIN_PRICE:,}-{cls.FILTER_MAX_PRICE:,}")
        print(f"Filter KM: 0-{cls.FILTER_MAX_KM:,}")
        print(f"Filter Transmisi: {cls.FILTER_TRANSMISSION}")
        print(f"Telegram Token: {'***SET***' if cls.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
        print(f"Telegram Chat ID: {'***SET***' if cls.TELEGRAM_CHAT_ID else 'NOT SET'}")
        print("=" * 50)


# Singleton instance
config = Config()
