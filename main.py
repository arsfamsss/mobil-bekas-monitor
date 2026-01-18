"""
main.py - Main Entrypoint untuk Bot Monitor Mobil Bekas

Menjalankan loop utama:
1. Fetch listings dari OLX, Mobil123, Carmudi, Jualo
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
from matcher import Matcher
from notifier_telegram import TelegramNotifier
from storage import Storage

# Fetchers
from olx_fetcher import create_olx_fetcher
from mobil123_fetcher import create_mobil123_fetcher
from carmudi_fetcher import create_carmudi_fetcher
from jualo_fetcher import create_jualo_fetcher


# =============================================================================
# LOGGING SETUP
# =============================================================================
def setup_logging() -> logging.Logger:
    """Setup logging ke console dan file."""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    log_file = log_dir / 'bot.log'
    # Use 'a' to append logs instead of overwrite if desired, but here we keep file handler simple
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)

    return logging.getLogger(__name__)


logger = setup_logging()


def main():
    logger.info("========== BOT MONITOR MOBIL BEKAS - STARTED ==========")
    
    # Validate config
    errors = config.validate()
    if errors:
        for err in errors:
            logger.error(err)
        return

    config.print_config()

    # Initialize components
    logger.info("Initializing components...")
    
    fetchers = []
    
    # Safely create fetchers
    try: 
        fetchers.append(create_olx_fetcher()) 
        logger.info("- OLX Fetcher: OK")
    except Exception as e: logger.error(f"- OLX Fetcher: ERROR ({e})")

    try: 
        fetchers.append(create_mobil123_fetcher()) 
        logger.info("- Mobil123 Fetcher: OK")
    except Exception as e: logger.error(f"- Mobil123 Fetcher: ERROR ({e})")
        
    try: 
        fetchers.append(create_carmudi_fetcher()) 
        logger.info("- Carmudi Fetcher: OK")
    except Exception as e: logger.error(f"- Carmudi Fetcher: ERROR ({e})")

    try: 
        fetchers.append(create_jualo_fetcher()) 
        logger.info("- Jualo Fetcher: OK")
    except Exception as e: logger.error(f"- Jualo Fetcher: ERROR ({e})")

    matcher = Matcher()
    storage = Storage()
    notifier = TelegramNotifier()

    # Send startup notification
    try:
        notifier.notify_startup()
    except Exception as e:
        logger.warning(f"Gagal kirim startup notif: {e}")

    logger.info(f"Interval check: {config.CHECK_INTERVAL_SECONDS} detik")
    logger.info("Tekan Ctrl+C untuk stop")

    check_count = 0
    try:
        while True:
            check_count += 1
            logger.info(f"\n=== Check #{check_count} ===")
            
            total_new_listings = 0
            
            for fetcher in fetchers:
                source_name = getattr(fetcher, 'SOURCE_NAME', 'unknown')
                
                # Check URL
                if not fetcher.search_url or str(fetcher.search_url).lower() == 'none' or not fetcher.search_url.startswith('http'):
                    logger.debug(f"Skipping {source_name}: URL not configured")
                    continue

                try:
                    listings = fetcher.fetch_listings()
                    if not listings:
                        continue
                        
                    for item in listings:
                        # Deduplication check
                        listing_id = str(item.get('listing_id', ''))
                        if storage.is_listing_seen(listing_id, source_name):
                            continue
                            
                        # Filtering
                        listings_to_check = [item] # Matcher expects list
                        matched_listings = matcher.filter_listings(listings_to_check)
                        
                        if matched_listings:
                            filtered_item = matched_listings[0] # Get back the item (matcher might add labels)
                            
                            # Save to storage to mark as seen
                            storage.mark_listing_seen(
                                listing_id=listing_id,
                                source=source_name,
                                url=filtered_item.get('url', ''),
                                title=filtered_item.get('title', ''),
                                price=filtered_item.get('price', 0)
                            )
                            
                            # Send notification
                            logger.info(f"🚀 NEW LISTING found on {source_name}: {filtered_item.get('title')}")
                            if notifier.notify_listing(filtered_item):
                                total_new_listings += 1
                                # Small delay to be nice to Telegram API
                                time.sleep(1)
                                
                except Exception as e:
                    logger.error(f"Error processing {source_name}: {e}")
            
            if total_new_listings == 0:
                logger.info("Tidak ada notifikasi baru dikirim.")
            else:
                logger.info(f"✨ Total notifikasi baru: {total_new_listings}")

            logger.info(f"Menunggu {config.CHECK_INTERVAL_SECONDS} detik...")
            time.sleep(config.CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        try:
            notifier.notify_error('Fatal Error', str(e))
        except:
            pass

if __name__ == "__main__":
    main()
