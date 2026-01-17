"""
notifier_telegram.py - Telegram Notification Sender

Mengirim notifikasi ke Telegram dengan format yang rapi.
Mendukung:
- Text message
- Photo dengan caption
- Rate limiting integration
"""

import logging
from typing import Optional

import requests

from config import config
from storage import storage

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification sender."""

    API_BASE = 'https://api.telegram.org/bot'

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        """
        Initialize notifier.

        Args:
            bot_token: Telegram bot token. Default dari config.
            chat_id: Target chat ID. Default dari config.
        """
        self.bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.api_url = f"{self.API_BASE}{self.bot_token}"

    def _format_price(self, price: int) -> str:
        """Format harga ke format rupiah."""
        if price >= 1_000_000_000:
            return f"Rp {price / 1_000_000_000:.1f} M"
        elif price >= 1_000_000:
            return f"Rp {price / 1_000_000:.0f} Juta"
        else:
            return f"Rp {price:,}".replace(',', '.')

    def _format_km(self, km: Optional[int]) -> str:
        """Format kilometer."""
        if km is None:
            return "N/A"
        return f"{km:,} km".replace(',', '.')

    def format_listing_message(self, listing: dict) -> str:
        """
        Format listing ke pesan Telegram.

        Args:
            listing: Dict data listing

        Returns:
            Formatted message string
        """
        title = listing.get('title', 'Tanpa Judul')
        price = listing.get('price', 0)
        location = listing.get('location', 'Tidak diketahui')
        year = listing.get('year', 'N/A')
        transmission = listing.get('transmission', 'N/A')
        km = listing.get('km')
        plat = listing.get('plat', 'unknown')
        url = listing.get('url', '')
        source = listing.get('source', 'unknown').upper()
        score = listing.get('score', 0)

        # Format transmisi
        trans_display = 'Manual' if transmission and 'manual' in transmission.lower() else \
                       'Matic' if transmission and 'matic' in transmission.lower() else \
                       str(transmission).title() if transmission else 'N/A'

        # Build message
        lines = [
            f"🚗 *{self._escape_markdown(title)}*",
            f"💰 {self._format_price(price)}",
            f"📍 {self._escape_markdown(location)}",
            f"📅 {year} | 🧭 {trans_display} | 🧾 {self._format_km(km)}",
            f"🏷️ Plat: {plat}",
        ]

        # Tambah score jika ada
        if score:
            lines.append(f"⭐ Skor: {score}/100")

        # Tambah source
        lines.append(f"📱 Sumber: {source}")

        # Tambah URL
        if url:
            lines.append(f"\n🔗 [Lihat Detail]({url})")

        return '\n'.join(lines)

    def _escape_markdown(self, text: str) -> str:
        """Escape special characters untuk Markdown V2."""
        if not text:
            return ''
        # Untuk MarkdownV1, escape characters yang perlu
        special_chars = ['_', '*', '`', '[']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    def send_message(
        self,
        text: str,
        parse_mode: str = 'Markdown',
        disable_preview: bool = False
    ) -> bool:
        """
        Kirim text message ke Telegram.

        Args:
            text: Pesan untuk dikirim
            parse_mode: Mode parsing (Markdown/HTML)
            disable_preview: Disable link preview

        Returns:
            True jika berhasil
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Bot token atau chat ID tidak diset")
            return False

        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': disable_preview,
                },
                timeout=30
            )

            if response.status_code == 200:
                logger.debug("Pesan terkirim ke Telegram")
                return True
            else:
                logger.error(f"Gagal kirim pesan: {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Error kirim pesan Telegram: {e}")
            return False

    def send_photo(
        self,
        photo_url: str,
        caption: str,
        parse_mode: str = 'Markdown'
    ) -> bool:
        """
        Kirim photo dengan caption ke Telegram.

        Args:
            photo_url: URL gambar
            caption: Caption untuk gambar
            parse_mode: Mode parsing untuk caption

        Returns:
            True jika berhasil
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Bot token atau chat ID tidak diset")
            return False

        try:
            response = requests.post(
                f"{self.api_url}/sendPhoto",
                json={
                    'chat_id': self.chat_id,
                    'photo': photo_url,
                    'caption': caption,
                    'parse_mode': parse_mode,
                },
                timeout=30
            )

            if response.status_code == 200:
                logger.debug("Photo terkirim ke Telegram")
                return True
            else:
                # Fallback ke text message jika photo gagal
                logger.warning(f"Gagal kirim photo, fallback ke text: {response.text}")
                return self.send_message(caption)

        except requests.RequestException as e:
            logger.error(f"Error kirim photo Telegram: {e}")
            # Fallback ke text
            return self.send_message(caption)

    def notify_listing(self, listing: dict, with_photo: bool = True) -> bool:
        """
        Kirim notifikasi listing ke Telegram dengan rate limiting.

        Args:
            listing: Dict data listing
            with_photo: Coba kirim dengan photo jika ada

        Returns:
            True jika berhasil
        """
        # Cek rate limit
        if not storage.can_send_notification():
            logger.warning("Rate limit tercapai, skip notifikasi")
            return False

        listing_id = listing.get('listing_id', 'unknown')
        message = self.format_listing_message(listing)

        success = False
        image_url = listing.get('image_url', '')

        # Coba kirim dengan photo
        if with_photo and image_url:
            success = self.send_photo(image_url, message)
        else:
            success = self.send_message(message)

        # Log notifikasi
        storage.log_notification(listing_id, success)

        return success

    def notify_error(self, error_type: str, error_message: str) -> bool:
        """
        Kirim notifikasi error dengan anti-spam.

        Args:
            error_type: Jenis error
            error_message: Detail error

        Returns:
            True jika berhasil
        """
        # Cek anti-spam error
        if not storage.can_send_error_notification(error_type):
            logger.debug(f"Skip error notification (anti-spam): {error_type}")
            return False

        message = (
            f"⚠️ *Error pada Bot Monitor*\n\n"
            f"Tipe: `{error_type}`\n"
            f"Pesan: {error_message}\n\n"
            f"Bot akan terus berjalan dan retry otomatis."
        )

        success = self.send_message(message)

        if success:
            storage.log_error_notification(error_type, error_message)

        return success

    def notify_startup(self) -> bool:
        """Kirim notifikasi bot sudah start."""
        message = (
            "🚀 *Bot Monitor Mobil Bekas Aktif*\n\n"
            f"Interval check: {config.CHECK_INTERVAL_SECONDS} detik\n"
            f"Max notif/jam: {config.MAX_NOTIFICATIONS_PER_HOUR}\n"
            f"Filter: Avanza {config.FILTER_MIN_YEAR}-{config.FILTER_MAX_YEAR}\n"
            f"Harga: {config.FILTER_MIN_PRICE/1_000_000:.0f}-{config.FILTER_MAX_PRICE/1_000_000:.0f} Juta\n"
            f"KM Max: {config.FILTER_MAX_KM:,}\n".replace(',', '.')
        )
        return self.send_message(message)

    def notify_stats(self, stats: dict) -> bool:
        """Kirim statistik bot."""
        message = (
            "📊 *Statistik Bot*\n\n"
            f"Total listing ditemukan: {stats.get('total_listings', 0)}\n"
            f"Notifikasi hari ini: {stats.get('notifications_today', 0)}\n"
            f"Notifikasi 1 jam terakhir: {stats.get('notifications_last_hour', 0)}\n"
        )

        by_source = stats.get('by_source', {})
        if by_source:
            message += "\nPer sumber:\n"
            for source, count in by_source.items():
                message += f"  • {source.upper()}: {count}\n"

        return self.send_message(message)


# Singleton instance
notifier = TelegramNotifier()
