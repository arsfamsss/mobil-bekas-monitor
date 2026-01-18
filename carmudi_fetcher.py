"""
carmudi_fetcher.py - Carmudi Listing Fetcher

Mengambil dan parse listing dari Carmudi.co.id.
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
# SELECTORS - Updated based on Carmudi's current structure
# =============================================================================
SELECTORS = {
    'card': [
        'article[data-id]',
        '.listing-item',
        '.car-listing-card',
        '.card-listing',
        'a[href*="/dijual/"]',  # Carmudi uses /dijual/ in listing URLs
        '.listing-card',
    ],
    'title': [
        'h2.title a',
        '.card-title a',
        'a[title]',
        '.listing-title a',
        'h3 a',
    ],
    'price': [
        '.price',
        '.card-price',
        '.listing-price',
        '[class*="price"]',
    ],
    'location': [
        '.location',
        '.card-location',
        '.listing-location',
        '[class*="location"]',
    ],
    'details': [
        '.features',
        '.card-features',
        '.listing-specs',
        '.car-details',
    ],
}


class CarmudiFetcher:
    """Fetcher untuk Carmudi dengan retry mechanism."""

    SOURCE_NAME = 'carmudi'
    BASE_URL = 'https://www.carmudi.co.id'

    def __init__(self, search_url: Optional[str] = None):
        """Initialize fetcher."""
        self.search_url = search_url or config.CARMUDI_SEARCH_URL
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
            'Referer': 'https://www.carmudi.co.id/',
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
        """Fetch listings from Carmudi with retry."""
        if not self.search_url or str(self.search_url).lower() == 'none':
            return []

        logger.info(f"Fetching Carmudi: {self.search_url[:60]}...")

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(1, 3)
                    logger.info(f"Carmudi retry {attempt + 1}/{max_retries} setelah {delay:.1f}s...")
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

                # Try multiple card selectors
                cards = self._select_all(soup, SELECTORS['card'])

                # Fallback: Find all links to /dijual/ page (Carmudi's listing pattern)
                if not cards:
                    listing_links = soup.select('a[href*="/dijual/"]')
                    # Get unique parent containers
                    seen_urls = set()
                    cards = []
                    for link in listing_links:
                        url = link.get('href', '')
                        if url and url not in seen_urls and '/dijual/' in url:
                            seen_urls.add(url)
                            # Use the link itself as the card
                            cards.append(link)

                listings = []
                for card in cards:
                    try:
                        item = self._parse_card(card)
                        if item:
                            listings.append(item)
                    except Exception as e:
                        logger.debug(f"Error parsing Carmudi card: {e}")

                logger.info(f"Carmudi: Ditemukan {len(listings)} listing")
                return listings

            except Exception as e:
                logger.warning(f"Carmudi attempt {attempt + 1}/{max_retries} gagal: {e}")

        logger.error(f"Gagal fetch Carmudi setelah {max_retries} attempts")
        return []

    def _parse_card(self, card) -> Optional[dict]:
        """Parse single listing card with multiple selector fallbacks."""
        # Title & URL
        title_elem = self._select_one(card, SELECTORS['title'])
        if not title_elem:
            # Fallback: card itself might be an <a> tag
            if card.name == 'a' and card.get('href'):
                title_elem = card
            else:
                title_elem = card.select_one('a[href]')

        if not title_elem:
            return None

        title = title_elem.get('title', '') or title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.BASE_URL, url)

        # Skip non-listing URLs
        if '/dijual/' not in url and '/cars/' not in url:
            return None

        listing_id = url.split('/')[-1] if url else str(hash(title))

        # Price
        price_elem = self._select_one(card, SELECTORS['price'])
        price = 0
        if price_elem:
            price_str = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
            price = int(price_str) if price_str else 0

        # Try parsing price from title/text if not found
        if price == 0:
            card_text = card.get_text(" ", strip=True)
            price_match = re.search(r'[Rr]p\.?\s*([\d.,]+)\s*(?:jt|juta|million)?', card_text)
            if price_match:
                price_str = re.sub(r'[^\d]', '', price_match.group(1))
                price = int(price_str) if price_str else 0
                # Multiply if it's in millions (juta)
                if price < 1000000 and ('jt' in card_text.lower() or 'juta' in card_text.lower()):
                    price = price * 1000000

        # Location
        loc_elem = self._select_one(card, SELECTORS['location'])
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Image
        img_elem = card.select_one('img')
        image_url = ''
        if img_elem:
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '') or img_elem.get('data-lazy-src', '')

        # Details
        details_text = card.get_text(" ", strip=True)

        # Parse year
        year = None
        year_match = re.search(r'\b(20\d{2})\b', f"{title} {details_text}")
        if year_match:
            year = int(year_match.group(1))

        # Parse KM
        km = None
        km_match = re.search(r'(\d+[\d.,]*)\s*(?:km|kilometer|rb|ribu)', details_text, re.IGNORECASE)
        if km_match:
            km_str = re.sub(r'[^\d]', '', km_match.group(1))
            km = int(km_str) if km_str else None
            # Handle "rb" (ribu = thousand) format
            if km and ('rb' in details_text.lower() or 'ribu' in details_text.lower()):
                if km < 1000:
                    km = km * 1000

        # Parse transmission
        transmission = None
        if re.search(r'\b(man|manual|mt)\b', details_text, re.IGNORECASE):
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


def create_carmudi_fetcher() -> CarmudiFetcher:
    return CarmudiFetcher()
