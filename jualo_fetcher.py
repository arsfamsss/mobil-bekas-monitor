"""
jualo_fetcher.py - Jualo Listing Fetcher

Mengambil dan parse listing dari Jualo.com.
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
# SELECTORS - Updated based on Jualo's structure
# =============================================================================
SELECTORS = {
    'card': [
        '.post-card',
        '.listing-card',
        '.col-6',
        '.product-card',
        'article.listing',
        '[data-listing]',
    ],
    'title': [
        '.post-card__title',
        '.listing-title',
        'h4',
        'h3',
        '.product-title',
    ],
    'price': [
        '.post-card__price',
        '.price',
        '.listing-price',
        '[class*="price"]',
    ],
    'location': [
        '.post-card__location',
        '.location',
        '.listing-location',
    ],
}


class JualoFetcher:
    """Fetcher untuk Jualo dengan retry mechanism."""

    SOURCE_NAME = 'jualo'
    BASE_URL = 'https://www.jualo.com'

    def __init__(self, search_url: Optional[str] = None):
        """Initialize fetcher."""
        self.search_url = search_url or config.JUALO_SEARCH_URL
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
            'Referer': 'https://www.jualo.com/',
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
        """Fetch listings from Jualo with retry."""
        if not self.search_url or str(self.search_url).lower() == 'none':
            return []

        logger.info(f"Fetching Jualo: {self.search_url[:60]}...")

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(1, 3)
                    logger.info(f"Jualo retry {attempt + 1}/{max_retries} setelah {delay:.1f}s...")
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

                # Fallback: Find all links that look like listing URLs
                if not cards:
                    links = soup.select('a[href*="/iklan/"], a[href*="/item/"]')
                    seen_urls = set()
                    cards = []
                    for link in links:
                        url = link.get('href', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            cards.append(link)

                listings = []
                for card in cards:
                    try:
                        item = self._parse_card(card)
                        if item:
                            listings.append(item)
                    except Exception as e:
                        logger.debug(f"Error parsing Jualo card: {e}")

                logger.info(f"Jualo: Ditemukan {len(listings)} listing")
                return listings

            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [400, 502, 503]:
                    logger.warning(f"Jualo returned {e.response.status_code} - server error or bad request")
                else:
                    logger.warning(f"Jualo HTTP error: {e}")
            except Exception as e:
                logger.warning(f"Jualo attempt {attempt + 1}/{max_retries} gagal: {e}")

        logger.error(f"Gagal fetch Jualo setelah {max_retries} attempts")
        return []

    def _parse_card(self, card) -> Optional[dict]:
        """Parse single listing card with multiple selector fallbacks."""
        # Get link element
        link_elem = card.select_one('a')
        if card.name == 'a':
            link_elem = card

        if not link_elem:
            return None

        url = link_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.BASE_URL, url)

        # Title
        title_elem = self._select_one(card, SELECTORS['title'])
        if not title_elem:
            title = link_elem.get_text(strip=True)
        else:
            title = title_elem.get_text(strip=True)

        if not title:
            return None

        listing_id = url.split('/')[-1] if url else str(hash(title))

        # Price
        price_elem = self._select_one(card, SELECTORS['price'])
        price = 0
        if price_elem:
            price_str = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
            price = int(price_str) if price_str else 0

        # Try parsing price from card text if not found
        if price == 0:
            card_text = card.get_text(" ", strip=True)
            price_match = re.search(r'[Rr]p\.?\s*([\d.,]+)', card_text)
            if price_match:
                price_str = re.sub(r'[^\d]', '', price_match.group(1))
                price = int(price_str) if price_str else 0

        # Location
        loc_elem = self._select_one(card, SELECTORS['location'])
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Image
        img_elem = card.select_one('img')
        image_url = ''
        if img_elem:
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '')

        # Parse year from title
        year = None
        year_match = re.search(r'\b(20\d{2})\b', title)
        if year_match:
            year = int(year_match.group(1))

        # Parse KM from title/text
        km = None
        card_text = card.get_text(" ", strip=True)
        km_match = re.search(r'(\d+[\d.,]*)\s*(?:km|kilometer)', card_text, re.IGNORECASE)
        if km_match:
            km_str = re.sub(r'[^\d]', '', km_match.group(1))
            km = int(km_str) if km_str else None

        # Parse transmission
        transmission = None
        if re.search(r'\b(man|manual|mt)\b', f"{title} {card_text}", re.IGNORECASE):
            transmission = 'manual'
        elif re.search(r'\b(auto|matic|at|cvt)\b', f"{title} {card_text}", re.IGNORECASE):
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


def create_jualo_fetcher() -> JualoFetcher:
    return JualoFetcher()
