"""
mobil123_fetcher.py - Mobil123 Listing Fetcher

Mengambil dan parse listing dari Mobil123.com.
Dengan retry mechanism dan multiple selector fallback.
"""

import logging
import random
import re
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

from config import config

logger = logging.getLogger(__name__)


# =============================================================================
# USER AGENT ROTATION
# =============================================================================
USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
]


# =============================================================================
# SELECTORS - Multiple fallbacks for different page structures
# =============================================================================
SELECTORS = {
    # Primary selectors
    'card': [
        'article.listing-item',
        '.listing-card',
        '.car-listing-item',
        'div[data-listing-id]',
        '.used-car-item',
    ],
    'title': [
        '.listing-item-title a',
        '.listing-title a',
        'h2.title a',
        '.card-title a',
        'a[data-testid="listing-link"]',
    ],
    'price': [
        '.price',
        '.listing-price',
        '.car-price',
        '[data-testid="price"]',
    ],
    'location': [
        '.listing-item-location',
        '.location',
        '.listing-location',
    ],
    'image': [
        'img.listing-item-img',
        'img.listing-img',
        '.listing-image img',
        'img[data-src]',
    ],
    'details': [
        '.listing-item-info',
        '.listing-details',
        '.car-specs',
    ],
}


class Mobil123Fetcher:
    """Fetcher untuk Mobil123 dengan retry mechanism."""

    SOURCE_NAME = 'mobil123'
    BASE_URL = 'https://www.mobil123.com'

    def __init__(self, search_url: Optional[str] = None):
        """Initialize fetcher."""
        self.search_url = search_url or config.MOBIL123_SEARCH_URL
        self._setup_session()

    def _setup_session(self):
        """Setup session with cloudscraper or requests."""
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'ios', 'mobile': True}
            )
        else:
            self.session = requests.Session()

        self._rotate_user_agent()

    def _rotate_user_agent(self):
        """Rotate User-Agent for anti-detection."""
        ua = random.choice(USER_AGENTS)
        self.session.headers.update({
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })

    def _select_one(self, soup, selector_list: list):
        """Try multiple selectors and return first match."""
        for selector in selector_list:
            elem = soup.select_one(selector)
            if elem:
                return elem
        return None

    def _select_all(self, soup, selector_list: list) -> list:
        """Try multiple selectors and return all matches."""
        for selector in selector_list:
            elems = soup.select(selector)
            if elems:
                return elems
        return []

    def fetch_listings(self, max_retries: int = 3) -> list[dict]:
        """Fetch listings from Mobil123 with retry."""
        if not self.search_url or str(self.search_url).lower() == 'none':
            return []

        logger.info(f"Fetching Mobil123: {self.search_url[:60]}...")

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(1, 3)
                    logger.info(f"Mobil123 retry {attempt + 1}/{max_retries} setelah {delay:.1f}s...")
                    time.sleep(delay)
                    self._rotate_user_agent()
                else:
                    time.sleep(random.uniform(0.5, 1.5))

                response = self.session.get(
                    self.search_url,
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                cards = self._select_all(soup, SELECTORS['card'])

                if not cards:
                    # Try finding any listing container
                    cards = soup.select('.listing, .car-card, [data-listing]')

                listings = []
                for card in cards:
                    try:
                        item = self._parse_card(card)
                        if item:
                            listings.append(item)
                    except Exception as e:
                        logger.debug(f"Error parsing Mobil123 card: {e}")

                logger.info(f"Mobil123: Ditemukan {len(listings)} listing")
                return listings

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logger.warning(f"Mobil123 returned 403 Forbidden - website may be blocking bots")
                else:
                    logger.warning(f"Mobil123 HTTP error: {e}")
            except Exception as e:
                logger.warning(f"Mobil123 attempt {attempt + 1}/{max_retries} gagal: {e}")

        logger.error(f"Gagal fetch Mobil123 setelah {max_retries} attempts")
        return []

    def _parse_card(self, card) -> Optional[dict]:
        """Parse single listing card with multiple selector fallbacks."""
        # Title & URL
        title_elem = self._select_one(card, SELECTORS['title'])
        if not title_elem:
            # Fallback: get first link in card
            title_elem = card.select_one('a[href*="mobil"]')

        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.BASE_URL, url)

        listing_id = url.split('/')[-1] if url else str(hash(title))

        # Price
        price_elem = self._select_one(card, SELECTORS['price'])
        price = 0
        if price_elem:
            price_str = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
            price = int(price_str) if price_str else 0

        # Location
        loc_elem = self._select_one(card, SELECTORS['location'])
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Image
        img_elem = self._select_one(card, SELECTORS['image'])
        if not img_elem:
            img_elem = card.select_one('img')
        image_url = ''
        if img_elem:
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '')

        # Details
        details_elem = self._select_one(card, SELECTORS['details'])
        details_text = card.get_text(" ", strip=True)

        # Parse year
        year = None
        year_match = re.search(r'\b(20\d{2})\b', f"{title} {details_text}")
        if year_match:
            year = int(year_match.group(1))

        # Parse KM
        km = None
        km_match = re.search(r'(\d+[\d.,]*)\s*(?:km|kilometer)', details_text, re.IGNORECASE)
        if km_match:
            km_str = re.sub(r'[^\d]', '', km_match.group(1))
            km = int(km_str) if km_str else None

        # Parse transmission
        transmission = None
        if re.search(r'\b(man|manual)\b', details_text, re.IGNORECASE):
            transmission = 'manual'
        elif re.search(r'\b(auto|matic|at|cvt)\b', details_text, re.IGNORECASE):
            transmission = 'automatic'

        return {
            'listing_id': listing_id,
            'source': self.SOURCE_NAME,
            'title': title,
            'price': price,
            'location': location,
            'url': url,
            'image_url': image_url,
            'year': year,
            'km': km,
            'transmission': transmission,
            'color': None,
        }


def create_mobil123_fetcher() -> Mobil123Fetcher:
    return Mobil123Fetcher()
