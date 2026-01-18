"""
jualo_fetcher.py - Jualo Listing Fetcher

Mengambil dan parse listing dari Jualo.com.
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

class JualoFetcher:
    """Fetcher untuk Jualo."""

    SOURCE_NAME = 'jualo'
    BASE_URL = 'https://www.jualo.com'

    def __init__(self, search_url: Optional[str] = None):
        """Initialize fetcher."""
        self.search_url = search_url or config.JUALO_SEARCH_URL
        
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
        if not self.search_url or self.search_url == 'None':
            return []

        logger.info(f"Fetching Jualo: {self.search_url[:50]}...")
        
        try:
            response = self.session.get(self.search_url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Jualo selectors often involve 'post-card'
            cards = soup.select('.post-card, .col-6') # Generic grid cols
            
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

        except Exception as e:
            logger.error(f"Gagal fetch Jualo: {e}")
            return []

    def _parse_card(self, card) -> Optional[dict]:
        # Links
        link_elem = card.select_one('a')
        if not link_elem:
            return None
            
        url = link_elem.get('href', '')
        if url and not url.startswith('http'):
            url = urljoin(self.BASE_URL, url)
            
        # Title
        title_elem = card.select_one('.post-card__title, h4')
        if not title_elem:
             # Try getting from text inside link
             title = link_elem.get_text(strip=True)
        else:
             title = title_elem.get_text(strip=True)
             
        if not title:
            return None
            
        listing_id = url.split('/')[-1] if url else str(hash(title))

        # Price
        price_elem = card.select_one('.post-card__price, .price')
        price = 0
        if price_elem:
            price_str = re.sub(r'[^\d]', '', price_elem.get_text(strip=True))
            price = int(price_str) if price_str else 0

        # Location
        loc_elem = card.select_one('.post-card__location')
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Image
        img_elem = card.select_one('img')
        image_url = img_elem.get('src', '') if img_elem else ''
        if not image_url and img_elem:
            image_url = img_elem.get('data-src', '')

        # Jualo cards often minimal details, mostly in title
        year = None
        year_match = re.search(r'\b(20\d{2})\b', title)
        if year_match:
            year = int(year_match.group(1))
            
        # Try to guess KM or Trans from title but it's unreliable on Jualo cards
        km = None
        transmission = None
        if re.search(r'\b(man|manual)\b', title, re.IGNORECASE):
            transmission = 'manual'
        elif re.search(r'\b(auto|matic|at)\b', title, re.IGNORECASE):
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
