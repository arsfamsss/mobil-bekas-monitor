"""
olx_fetcher.py - OLX Listing Fetcher & Parser

Mengambil dan parse listing dari OLX Indonesia.
Strategi:
1. Cari JSON data di <script> tag (lebih stabil)
2. Fallback ke HTML parsing jika JSON tidak ada

SELECTOR CONFIGURATION:
Jika OLX mengubah struktur HTML, update selector di bagian SELECTORS di bawah.
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import config

logger = logging.getLogger(__name__)


# =============================================================================
# SELECTORS - Update di sini jika OLX mengubah struktur HTML
# =============================================================================
SELECTORS = {
    # JSON data di script tag (prioritas utama)
    'json_script_pattern': r'window\.__PRELOADED_STATE__\s*=\s*({.+?});?\s*</script>',

    # Fallback HTML selectors
    'listing_card': 'li[data-aut-id="itemBox"]',
    'listing_link': 'a[data-aut-id="itemTitle"]',
    'listing_title': '[data-aut-id="itemTitle"]',
    'listing_price': '[data-aut-id="itemPrice"]',
    'listing_location': '[data-aut-id="item-location"]',
    'listing_details': '[data-aut-id="itemDetails"]',
    'listing_image': 'img[data-aut-id="itemImage"]',

    # Alternative selectors (jika primary tidak work)
    'alt_listing_card': 'li[class*="EIR5N"]',
    'alt_price': 'span[class*="Price"]',
}

# Request headers untuk menghindari block
HEADERS = {
    'User-Agent': config.USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}


class OLXFetcher:
    """Fetcher untuk OLX Indonesia."""

    SOURCE_NAME = 'olx'
    BASE_URL = 'https://www.olx.co.id'

    def __init__(self, search_url: Optional[str] = None):
        """
        Initialize fetcher.

        Args:
            search_url: URL pencarian OLX. Default dari config.
        """
        self.search_url = search_url or config.OLX_SEARCH_URL
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: Optional[str] = None) -> Optional[str]:
        """
        Fetch HTML dari URL.

        Args:
            url: URL untuk di-fetch. Default: search_url

        Returns:
            HTML content atau None jika gagal
        """
        target_url = url or self.search_url

        try:
            response = self.session.get(
                target_url,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            logger.error(f"Gagal fetch OLX: {e}")
            return None

    def _extract_json_data(self, html: str) -> Optional[dict]:
        """
        Ekstrak JSON data dari script tag.

        Args:
            html: HTML content

        Returns:
            Dict data atau None jika tidak ada
        """
        try:
            # Cari pattern JSON di script
            match = re.search(SELECTORS['json_script_pattern'], html, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"Tidak bisa parse JSON dari script: {e}")

        return None

    def _parse_json_listings(self, data: dict) -> list[dict]:
        """
        Parse listings dari JSON data.

        Args:
            data: JSON data dari __PRELOADED_STATE__

        Returns:
            List of listing dicts
        """
        listings = []

        try:
            # Navigasi ke data listings (struktur bisa berubah)
            # Biasanya di: data.search.items atau data.listing.items
            items = None

            # Coba beberapa path yang mungkin
            paths_to_try = [
                ['search', 'items'],
                ['listing', 'items'],
                ['data', 'items'],
                ['items'],
            ]

            for path in paths_to_try:
                current = data
                try:
                    for key in path:
                        current = current[key]
                    if isinstance(current, list):
                        items = current
                        break
                except (KeyError, TypeError):
                    continue

            if not items:
                logger.warning("Tidak bisa temukan items di JSON data")
                return listings

            for item in items:
                try:
                    listing = self._parse_json_item(item)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing JSON listings: {e}")

        return listings

    def _parse_json_item(self, item: dict) -> Optional[dict]:
        """
        Parse single item dari JSON.

        Args:
            item: Item dict dari JSON

        Returns:
            Parsed listing dict atau None
        """
        try:
            # Extract ID
            listing_id = str(item.get('id', ''))
            if not listing_id:
                return None

            # Extract basic info
            title = item.get('title', '')

            # Extract price
            price_data = item.get('price', {})
            if isinstance(price_data, dict):
                price = price_data.get('value', {}).get('raw', 0)
            else:
                price = int(price_data) if price_data else 0

            # Extract location
            location_data = item.get('locations_resolved', {})
            if isinstance(location_data, dict):
                location = location_data.get('ADMIN_LEVEL_3_name', '')
                if not location:
                    location = location_data.get('ADMIN_LEVEL_1_name', '')
            else:
                location = str(location_data) if location_data else ''

            # Extract URL
            url = item.get('url', '')
            if url and not url.startswith('http'):
                url = urljoin(self.BASE_URL, url)

            # Extract image
            images = item.get('images', [])
            image_url = ''
            if images and isinstance(images, list) and len(images) > 0:
                img = images[0]
                if isinstance(img, dict):
                    image_url = img.get('url', '')
                else:
                    image_url = str(img)

            # Extract parameters (tahun, km, transmisi, dll)
            params = item.get('parameters', [])
            year = None
            km = None
            transmission = None
            color = None

            for param in params:
                if isinstance(param, dict):
                    key = param.get('key', '').lower()
                    value = param.get('value', '')
                    value_name = param.get('value_name', value)

                    if 'year' in key or 'tahun' in key:
                        try:
                            year = int(value)
                        except (ValueError, TypeError):
                            pass

                    elif 'mileage' in key or 'kilometer' in key:
                        try:
                            # Remove non-numeric
                            km_str = re.sub(r'[^\d]', '', str(value))
                            km = int(km_str) if km_str else None
                        except (ValueError, TypeError):
                            pass

                    elif 'transmission' in key or 'transmisi' in key:
                        transmission = str(value_name).lower()

                    elif 'color' in key or 'warna' in key:
                        color = str(value_name).lower()

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
                'color': color,
            }

        except Exception as e:
            logger.debug(f"Error parsing JSON item: {e}")
            return None

    def _parse_html_listings(self, html: str) -> list[dict]:
        """
        Fallback: Parse listings dari HTML.

        Args:
            html: HTML content

        Returns:
            List of listing dicts
        """
        listings = []
        soup = BeautifulSoup(html, 'lxml')

        # Coba primary selector
        cards = soup.select(SELECTORS['listing_card'])

        # Fallback ke alternative selector
        if not cards:
            cards = soup.select(SELECTORS['alt_listing_card'])

        if not cards:
            logger.warning("Tidak bisa temukan listing cards di HTML")
            return listings

        for card in cards:
            try:
                listing = self._parse_html_card(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing HTML card: {e}")
                continue

        return listings

    def _parse_html_card(self, card) -> Optional[dict]:
        """
        Parse single listing card dari HTML.

        Args:
            card: BeautifulSoup element

        Returns:
            Parsed listing dict atau None
        """
        try:
            # Extract link & title
            link_elem = card.select_one(SELECTORS['listing_link'])
            if not link_elem:
                link_elem = card.select_one('a')

            if not link_elem:
                return None

            url = link_elem.get('href', '')
            if url and not url.startswith('http'):
                url = urljoin(self.BASE_URL, url)

            # Generate listing_id from URL
            listing_id = url.split('-')[-1].replace('.html', '') if url else ''
            if not listing_id:
                listing_id = str(hash(url))

            # Extract title
            title_elem = card.select_one(SELECTORS['listing_title'])
            title = title_elem.get_text(strip=True) if title_elem else ''
            if not title:
                title = link_elem.get_text(strip=True)

            # Extract price
            price_elem = card.select_one(SELECTORS['listing_price'])
            if not price_elem:
                price_elem = card.select_one(SELECTORS['alt_price'])

            price = 0
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_num = re.sub(r'[^\d]', '', price_text)
                price = int(price_num) if price_num else 0

            # Extract location
            loc_elem = card.select_one(SELECTORS['listing_location'])
            location = loc_elem.get_text(strip=True) if loc_elem else ''

            # Extract image
            img_elem = card.select_one(SELECTORS['listing_image'])
            if not img_elem:
                img_elem = card.select_one('img')
            image_url = img_elem.get('src', '') if img_elem else ''

            # Extract details (tahun, km, dll) dari text
            details_elem = card.select_one(SELECTORS['listing_details'])
            details_text = details_elem.get_text(strip=True) if details_elem else ''

            # Parse tahun dari judul/details
            year = None
            year_match = re.search(r'\b(20\d{2})\b', f"{title} {details_text}")
            if year_match:
                year = int(year_match.group(1))

            # Parse KM
            km = None
            km_match = re.search(r'(\d+[\d.,]*)\s*(?:km|kilometer)',
                                f"{title} {details_text}", re.IGNORECASE)
            if km_match:
                km_str = re.sub(r'[^\d]', '', km_match.group(1))
                km = int(km_str) if km_str else None

            # Parse transmisi
            transmission = None
            if re.search(r'\bmanual\b', f"{title} {details_text}", re.IGNORECASE):
                transmission = 'manual'
            elif re.search(r'\b(matic|automatic|at)\b', f"{title} {details_text}", re.IGNORECASE):
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

        except Exception as e:
            logger.debug(f"Error parsing HTML card: {e}")
            return None

    def fetch_listings(self) -> list[dict]:
        """
        Fetch dan parse semua listings dari OLX.

        Returns:
            List of listing dicts
        """
        logger.info(f"Fetching OLX: {self.search_url[:80]}...")

        html = self.fetch_page()
        if not html:
            logger.error("Gagal fetch halaman OLX")
            return []

        # Coba parse JSON dulu (lebih stabil)
        json_data = self._extract_json_data(html)
        if json_data:
            logger.debug("Parsing dari JSON data")
            listings = self._parse_json_listings(json_data)
            if listings:
                logger.info(f"Ditemukan {len(listings)} listing dari JSON")
                return listings

        # Fallback ke HTML parsing
        logger.debug("Fallback ke HTML parsing")
        listings = self._parse_html_listings(html)
        logger.info(f"Ditemukan {len(listings)} listing dari HTML")

        return listings


# Factory function
def create_olx_fetcher(search_url: Optional[str] = None) -> OLXFetcher:
    """Create OLX fetcher instance."""
    return OLXFetcher(search_url)
