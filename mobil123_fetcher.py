"""
mobil123_fetcher.py - Mobil123 Listing Fetcher

Mengambil dan parse listing dari Mobil123.com.
"""

import logging
import re
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
# SELECTORS
# =============================================================================
SELECTORS = {
    'card': 'article.listing-item',
    'title': '.listing-item-title a',
    'price': '.price',
    'location': '.listing-item-location',
    'image': 'img.listing-item-img',
    'details': '.listing-item-info',  # Contains year, km, transmission
    'url': '.listing-item-title a',
}


class Mobil123Fetcher:
    """Fetcher untuk Mobil123."""

    SOURCE_NAME = 'mobil123'
    BASE_URL = 'https://www.mobil123.com'

    def __init__(self, search_url: Optional[str] = None):
        """Initialize fetcher."""
        self.search_url = search_url or config.MOBIL123_SEARCH_URL
        
        # Setup session
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'ios', 'mobile': True}
            )
        else:
            self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def fetch_listings(self) -> list[dict]:
        """Fetch listings from Mobil123."""
        if not self.search_url or self.search_url == 'None':
            return []

        logger.info(f"Fetching Mobil123: {self.search_url[:50]}...")
        
        try:
            response = self.session.get(self.search_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.select(SELECTORS['card'])
            
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

        except Exception as e:
            logger.error(f"Gagal fetch Mobil123: {e}")
            return []

    def _parse_card(self, card) -> Optional[dict]:
        """Parse single listing card."""
        # Title & URL
        title_elem = card.select_one(SELECTORS['title'])
        if not title_elem:
            return None
            
        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.BASE_URL, url)
            
        listing_id = url.split('/')[-1] if url else str(hash(title))

        # Price
        price_elem = card.select_one(SELECTORS['price'])
        price = 0
        if price_elem:
            price_str = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
            price = int(price_str) if price_str else 0

        # Location
        loc_elem = card.select_one(SELECTORS['location'])
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Image
        img_elem = card.select_one(SELECTORS['image'])
        image_url = img_elem.get('src', '') if img_elem else ''
        if not image_url and img_elem:
            image_url = img_elem.get('data-src', '')

        # Details (Year, KM, Trans)
        details_elem = card.select_one(SELECTORS['details'])
        details_text = details_elem.get_text(" ", strip=True) if details_elem else ""
        
        year = None
        year_match = re.search(r'\b(20\d{2})\b', f"{title} {details_text}")
        if year_match:
            year = int(year_match.group(1))

        km = None
        km_match = re.search(r'(\d+)\s*(?:km|kilometer)', details_text, re.IGNORECASE)
        if km_match:
            km = int(km_match.group(1))

        transmission = None
        if re.search(r'\b(man|manual)\b', details_text, re.IGNORECASE):
            transmission = 'manual'
        elif re.search(r'\b(auto|matic|at)\b', details_text, re.IGNORECASE):
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
