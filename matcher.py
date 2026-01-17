"""
matcher.py - Filter Logic & Scoring untuk Listing Mobil

Memfilter listing berdasarkan kriteria:
- Model: Toyota Avanza/Veloz
- Warna: Putih
- Tahun: 2019-2021
- KM: 0-60.000
- Harga: 120-190 juta
- Transmisi: Manual

Bonus: Deteksi plat "F" dari judul/deskripsi
"""

import re
from typing import Optional

from config import config


class ListingMatcher:
    """Matcher untuk memfilter listing mobil."""

    # Pattern untuk deteksi plat nomor (case insensitive - akan di-upper dulu)
    PLAT_PATTERNS = [
        r'\bPLAT\s+([A-Z])\b',  # Format: plat F atau Plat F
        r'\bNOPOL\s+([A-Z])\b',  # Format: nopol F
        r'\b([A-Z])\s+\d{1,4}\s*[A-Z]{0,3}\b',  # Format: F 1234 ABC atau F 1234
        r'\b([A-Z])-\d{1,4}\b',  # Format: F-1234
    ]

    # Keywords yang menunjukkan Avanza
    AVANZA_KEYWORDS = [
        'avanza', 'veloz', 'avansa', 'avnza'  # termasuk typo umum
    ]

    # Keywords yang menunjukkan BUKAN Avanza (exclude)
    NON_AVANZA_KEYWORDS = [
        'innova', 'fortuner', 'rush', 'calya', 'sigra', 'xenia',
        'terios', 'ayla', 'agya', 'yaris', 'vios', 'camry', 'alphard',
        'xpander', 'ertiga', 'livina', 'mobilio', 'brv', 'hrv', 'crv'
    ]

    def __init__(self):
        """Initialize matcher dengan konfigurasi dari config."""
        self.min_year = config.FILTER_MIN_YEAR
        self.max_year = config.FILTER_MAX_YEAR
        self.min_price = config.FILTER_MIN_PRICE
        self.max_price = config.FILTER_MAX_PRICE
        self.max_km = config.FILTER_MAX_KM
        self.transmission = config.FILTER_TRANSMISSION.lower()
        self.color = config.FILTER_COLOR.lower()

    def is_avanza(self, title: str, description: str = '') -> bool:
        """
        Cek apakah listing adalah Avanza/Veloz.

        Args:
            title: Judul listing
            description: Deskripsi listing (opsional)

        Returns:
            True jika Avanza/Veloz
        """
        text = f"{title} {description}".lower()

        # Cek ada keyword Avanza
        has_avanza = any(kw in text for kw in self.AVANZA_KEYWORDS)

        # Cek tidak ada keyword non-Avanza
        has_non_avanza = any(kw in text for kw in self.NON_AVANZA_KEYWORDS)

        return has_avanza and not has_non_avanza

    def check_year(self, year: Optional[int]) -> bool:
        """
        Cek apakah tahun dalam range.

        Args:
            year: Tahun produksi

        Returns:
            True jika dalam range
        """
        if year is None:
            return False
        return self.min_year <= year <= self.max_year

    def check_price(self, price: Optional[int]) -> bool:
        """
        Cek apakah harga dalam range.

        Args:
            price: Harga dalam Rupiah

        Returns:
            True jika dalam range
        """
        if price is None:
            return False
        return self.min_price <= price <= self.max_price

    def check_km(self, km: Optional[int]) -> bool:
        """
        Cek apakah kilometer dalam range.

        Args:
            km: Kilometer

        Returns:
            True jika dalam range (0 sampai max_km)
        """
        if km is None:
            return True  # Jika tidak ada info KM, tetap lolos (opsional check)
        return 0 <= km <= self.max_km

    def check_transmission(self, transmission: Optional[str]) -> bool:
        """
        Cek apakah transmisi sesuai.

        Args:
            transmission: Jenis transmisi

        Returns:
            True jika sesuai
        """
        if transmission is None:
            return True  # Jika tidak ada info, tetap lolos
        return transmission.lower() == self.transmission

    def check_color(self, color: Optional[str]) -> bool:
        """
        Cek apakah warna sesuai.

        Args:
            color: Warna mobil

        Returns:
            True jika sesuai
        """
        if color is None:
            return True  # Jika tidak ada info, tetap lolos
        return self.color in color.lower()

    def detect_plat(self, title: str, description: str = '') -> str:
        """
        Deteksi plat nomor dari judul/deskripsi.

        Args:
            title: Judul listing
            description: Deskripsi listing

        Returns:
            Huruf plat (misalnya "F") atau "unknown"
        """
        text = f"{title} {description}".upper()

        for pattern in self.PLAT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return "unknown"

    def calculate_score(self, listing: dict) -> int:
        """
        Hitung skor prioritas listing.

        Skor lebih tinggi = lebih prioritas.

        Args:
            listing: Dict data listing

        Returns:
            Skor (0-100)
        """
        score = 50  # Base score

        # Bonus untuk plat F (prioritas tinggi)
        plat = listing.get('plat', 'unknown')
        if plat == 'F':
            score += 30

        # Bonus untuk KM rendah
        km = listing.get('km')
        if km is not None:
            if km < 20000:
                score += 15
            elif km < 40000:
                score += 10
            elif km < 60000:
                score += 5

        # Bonus untuk tahun lebih baru
        year = listing.get('year')
        if year is not None:
            if year == 2021:
                score += 10
            elif year == 2020:
                score += 5

        # Penalty untuk harga tinggi
        price = listing.get('price')
        if price is not None:
            if price > 180000000:
                score -= 5
            elif price < 140000000:
                score += 5

        return min(100, max(0, score))

    def match(self, listing: dict) -> tuple[bool, dict]:
        """
        Cek apakah listing match dengan kriteria.

        Args:
            listing: Dict dengan keys:
                - title: str
                - description: str (opsional)
                - price: int
                - year: int
                - km: int
                - transmission: str
                - color: str

        Returns:
            Tuple (is_match: bool, enriched_listing: dict)
            enriched_listing akan punya tambahan 'plat' dan 'score' jika match
        """
        title = listing.get('title', '')
        description = listing.get('description', '')

        # 1. Cek model Avanza
        if not self.is_avanza(title, description):
            return False, listing

        # 2. Cek tahun
        if not self.check_year(listing.get('year')):
            return False, listing

        # 3. Cek harga
        if not self.check_price(listing.get('price')):
            return False, listing

        # 4. Cek kilometer
        if not self.check_km(listing.get('km')):
            return False, listing

        # 5. Cek transmisi
        if not self.check_transmission(listing.get('transmission')):
            return False, listing

        # 6. Cek warna (opsional, karena sudah filter di URL)
        # if not self.check_color(listing.get('color')):
        #     return False, listing

        # Match! Enrich data
        enriched = listing.copy()
        enriched['plat'] = self.detect_plat(title, description)
        enriched['score'] = self.calculate_score(enriched)

        return True, enriched

    def filter_listings(self, listings: list[dict]) -> list[dict]:
        """
        Filter list of listings dan return yang match.

        Args:
            listings: List of listing dicts

        Returns:
            List of matched & enriched listings, sorted by score (desc)
        """
        matched = []

        for listing in listings:
            is_match, enriched = self.match(listing)
            if is_match:
                matched.append(enriched)

        # Sort by score descending
        matched.sort(key=lambda x: x.get('score', 0), reverse=True)

        return matched


# Singleton instance
matcher = ListingMatcher()
