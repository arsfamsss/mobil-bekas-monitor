"""
main.py - Main Entrypoint untuk Bot Monitor Mobil Bekas

Menjalankan loop utama:
1. Fetch listings dari OLX
2. Filter dengan matcher
3. Dedup dengan storage
4. Kirim notifikasi untuk listing baru
"""

import logging
import sys
import time
from pathlib import Path

# Fix untuk folder dengan spasi di nama
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from matcher import matcher
from notifier_telegram import notifier
from olx_fetcher import create_olx_fetcher
from storage import storage


# =============================================================================
# LOGGING SETUP
# =============================================================================
def setup_logging() -> logging.Logger:
    """Setup logging ke console dan file."""

    # Buat folder logs jika belum ada
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Format log
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    # File handler
    log_file = log_dir / 'bot.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)

    return logging.getLogger(__name__)


logger = setup_logging()


# =============================================================================
# MAIN BOT CLASS
# =============================================================================
class MobilMonitorBot:
    """Bot utama untuk monitoring mobil bekas."""

    def __init__(self):
        """Initialize bot dengan semua komponen."""
        self.olx_fetcher = create_olx_fetcher()
        self.running = True
        self.check_count = 0
        self.new_listings_count = 0

    def validate_config(self) -> bool:
        """Validasi konfigurasi sebelum start."""
        errors = config.validate()

        if errors:
            logger.error("Konfigurasi tidak valid:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        return True

    def process_listings(self, listings: list[dict]) -> int:
        """
        Process listings: filter, dedup, dan notify.

        Args:
            listings: List of raw listings

        Returns:
            Jumlah listing baru yang di-notify
        """
        if not listings:
            return 0

        # Filter dengan matcher
        matched = matcher.filter_listings(listings)
        logger.info(f"Matched: {len(matched)} dari {len(listings)} listings")

        new_count = 0

        for listing in matched:
            listing_id = listing.get('listing_id', '')
            source = listing.get('source', 'unknown')

            # Skip jika sudah pernah dilihat
            if storage.is_listing_seen(listing_id, source):
                logger.debug(f"Skip (sudah dilihat): {listing_id}")
                continue

            # Cek rate limit sebelum notify
            if not storage.can_send_notification():
                logger.warning("Rate limit tercapai, stop processing")
                break

            # Kirim notifikasi
            logger.info(f"Listing baru: {listing.get('title', 'N/A')[:50]}")
            success = notifier.notify_listing(listing)

            # Mark sebagai sudah dilihat (apapun hasil notify)
            storage.mark_listing_seen(
                listing_id=listing_id,
                source=source,
                url=listing.get('url', ''),
                title=listing.get('title'),
                price=listing.get('price')
            )

            if success:
                new_count += 1

            # Delay antar notifikasi untuk menghindari rate limit Telegram
            time.sleep(1)

        return new_count

    def run_check(self) -> None:
        """Jalankan satu cycle pengecekan."""
        self.check_count += 1
        logger.info(f"=== Check #{self.check_count} ===")

        try:
            # Fetch dari OLX
            listings = self.olx_fetcher.fetch_listings()

            if not listings:
                logger.warning("Tidak ada listings ditemukan")
                return

            # Process listings
            new_count = self.process_listings(listings)
            self.new_listings_count += new_count

            if new_count > 0:
                logger.info(f"Ternotifikasi: {new_count} listing baru")
            else:
                logger.info("Tidak ada listing baru")

        except Exception as e:
            logger.error(f"Error saat pengecekan: {e}")

            # Kirim notifikasi error (dengan anti-spam)
            notifier.notify_error(
                error_type='fetch_error',
                error_message=str(e)
            )

    def run(self) -> None:
        """Jalankan bot loop utama."""
        logger.info("=" * 60)
        logger.info("BOT MONITOR MOBIL BEKAS - STARTED")
        logger.info("=" * 60)

        # Validasi config
        if not self.validate_config():
            logger.error("Gagal start: konfigurasi tidak valid")
            sys.exit(1)

        # Print config
        config.print_config()

        # Kirim notifikasi startup
        notifier.notify_startup()

        logger.info(f"Interval check: {config.CHECK_INTERVAL_SECONDS} detik")
        logger.info("Tekan Ctrl+C untuk stop\n")

        try:
            while self.running:
                self.run_check()

                # Log stats setiap 10 check
                if self.check_count % 10 == 0:
                    stats = storage.get_stats()
                    logger.info(f"Stats: {stats}")

                # Tunggu interval
                logger.info(f"Menunggu {config.CHECK_INTERVAL_SECONDS} detik...\n")
                time.sleep(config.CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("\nBot dihentikan oleh user (Ctrl+C)")

        except Exception as e:
            logger.error(f"Bot error: {e}")
            notifier.notify_error('bot_crash', str(e))

        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown bot dengan bersih."""
        logger.info("=" * 60)
        logger.info("BOT MONITOR MOBIL BEKAS - STOPPED")
        logger.info(f"Total checks: {self.check_count}")
        logger.info(f"Total listings baru: {self.new_listings_count}")
        logger.info("=" * 60)


# =============================================================================
# MAIN
# =============================================================================
def main():
    """Main entry point."""
    bot = MobilMonitorBot()
    bot.run()


if __name__ == '__main__':
    main()
