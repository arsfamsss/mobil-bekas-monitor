"""
test_matcher.py - Unit Tests untuk Matcher

Menguji logic filter:
- Filter tahun
- Filter harga
- Filter kilometer
- Filter transmisi
- Deteksi plat
- Deteksi model Avanza
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path untuk import module
sys.path.insert(0, str(Path(__file__).parent.parent))

from matcher import ListingMatcher


# =============================================================================
# FIXTURES
# =============================================================================
@pytest.fixture
def matcher_instance():
    """Create fresh matcher instance untuk setiap test."""
    return ListingMatcher()


@pytest.fixture
def sample_valid_listing():
    """Sample listing yang valid (match semua kriteria)."""
    return {
        'listing_id': '12345',
        'source': 'olx',
        'title': 'Toyota Avanza Veloz 1.5 MT 2020 Putih',
        'description': 'Kondisi mulus, plat F Bogor',
        'price': 160000000,
        'year': 2020,
        'km': 35000,
        'transmission': 'manual',
        'color': 'putih',
        'location': 'Bogor',
        'url': 'https://olx.co.id/item/12345',
    }


@pytest.fixture
def sample_listings():
    """Kumpulan sample listings untuk testing."""
    return [
        {
            'listing_id': '1',
            'title': 'Toyota Avanza G 2020 Manual Putih',
            'price': 150000000,
            'year': 2020,
            'km': 30000,
            'transmission': 'manual',
        },
        {
            'listing_id': '2',
            'title': 'Toyota Innova 2020 Manual',  # Non-Avanza
            'price': 280000000,
            'year': 2020,
            'km': 25000,
            'transmission': 'manual',
        },
        {
            'listing_id': '3',
            'title': 'Toyota Avanza Veloz 2018 MT',  # Tahun di luar range
            'price': 140000000,
            'year': 2018,
            'km': 50000,
            'transmission': 'manual',
        },
        {
            'listing_id': '4',
            'title': 'Toyota Avanza 2021 Matic',  # Transmisi matic
            'price': 170000000,
            'year': 2021,
            'km': 20000,
            'transmission': 'automatic',
        },
        {
            'listing_id': '5',
            'title': 'Toyota Avanza 2019 Manual',
            'price': 130000000,
            'year': 2019,
            'km': 45000,
            'transmission': 'manual',
        },
    ]


# =============================================================================
# TESTS - FILTER TAHUN
# =============================================================================
class TestFilterYear:
    """Tests untuk filter tahun."""

    def test_year_in_range_2019(self, matcher_instance):
        """Tahun 2019 harus lolos."""
        assert matcher_instance.check_year(2019) is True

    def test_year_in_range_2020(self, matcher_instance):
        """Tahun 2020 harus lolos."""
        assert matcher_instance.check_year(2020) is True

    def test_year_in_range_2021(self, matcher_instance):
        """Tahun 2021 harus lolos."""
        assert matcher_instance.check_year(2021) is True

    def test_year_below_range(self, matcher_instance):
        """Tahun 2018 harus ditolak."""
        assert matcher_instance.check_year(2018) is False

    def test_year_above_range(self, matcher_instance):
        """Tahun 2022 harus ditolak."""
        assert matcher_instance.check_year(2022) is False

    def test_year_none(self, matcher_instance):
        """Tahun None harus ditolak."""
        assert matcher_instance.check_year(None) is False


# =============================================================================
# TESTS - FILTER HARGA
# =============================================================================
class TestFilterPrice:
    """Tests untuk filter harga."""

    def test_price_in_range_min(self, matcher_instance):
        """Harga tepat di minimum (120 juta) harus lolos."""
        assert matcher_instance.check_price(120000000) is True

    def test_price_in_range_max(self, matcher_instance):
        """Harga tepat di maximum (190 juta) harus lolos."""
        assert matcher_instance.check_price(190000000) is True

    def test_price_in_range_middle(self, matcher_instance):
        """Harga di tengah range harus lolos."""
        assert matcher_instance.check_price(155000000) is True

    def test_price_below_range(self, matcher_instance):
        """Harga di bawah range harus ditolak."""
        assert matcher_instance.check_price(100000000) is False

    def test_price_above_range(self, matcher_instance):
        """Harga di atas range harus ditolak."""
        assert matcher_instance.check_price(200000000) is False

    def test_price_none(self, matcher_instance):
        """Harga None harus ditolak."""
        assert matcher_instance.check_price(None) is False


# =============================================================================
# TESTS - FILTER KILOMETER
# =============================================================================
class TestFilterKm:
    """Tests untuk filter kilometer."""

    def test_km_zero(self, matcher_instance):
        """KM 0 harus lolos."""
        assert matcher_instance.check_km(0) is True

    def test_km_in_range(self, matcher_instance):
        """KM dalam range harus lolos."""
        assert matcher_instance.check_km(35000) is True

    def test_km_at_max(self, matcher_instance):
        """KM tepat di maximum (60.000) harus lolos."""
        assert matcher_instance.check_km(60000) is True

    def test_km_above_max(self, matcher_instance):
        """KM di atas maximum harus ditolak."""
        assert matcher_instance.check_km(70000) is False

    def test_km_none(self, matcher_instance):
        """KM None harus lolos (opsional check)."""
        assert matcher_instance.check_km(None) is True


# =============================================================================
# TESTS - FILTER TRANSMISI
# =============================================================================
class TestFilterTransmission:
    """Tests untuk filter transmisi."""

    def test_transmission_manual(self, matcher_instance):
        """Transmisi manual harus lolos."""
        assert matcher_instance.check_transmission('manual') is True

    def test_transmission_manual_uppercase(self, matcher_instance):
        """Transmisi MANUAL (uppercase) harus lolos."""
        assert matcher_instance.check_transmission('MANUAL') is True

    def test_transmission_automatic(self, matcher_instance):
        """Transmisi automatic harus ditolak."""
        assert matcher_instance.check_transmission('automatic') is False

    def test_transmission_matic(self, matcher_instance):
        """Transmisi matic harus ditolak."""
        assert matcher_instance.check_transmission('matic') is False

    def test_transmission_none(self, matcher_instance):
        """Transmisi None harus lolos (opsional)."""
        assert matcher_instance.check_transmission(None) is True


# =============================================================================
# TESTS - DETEKSI PLAT
# =============================================================================
class TestPlatDetection:
    """Tests untuk deteksi plat nomor."""

    def test_detect_plat_f_in_title(self, matcher_instance):
        """Deteksi plat F dari judul."""
        plat = matcher_instance.detect_plat('Avanza F 1234 ABC Putih')
        assert plat == 'F'

    def test_detect_plat_with_keyword(self, matcher_instance):
        """Deteksi plat dengan keyword 'plat'."""
        plat = matcher_instance.detect_plat('Avanza Plat F Bogor')
        assert plat == 'F'

    def test_detect_plat_from_description(self, matcher_instance):
        """Deteksi plat dari deskripsi."""
        plat = matcher_instance.detect_plat('Avanza Putih', 'Plat F Bogor')
        assert plat == 'F'

    def test_detect_plat_b(self, matcher_instance):
        """Deteksi plat B (Jakarta)."""
        plat = matcher_instance.detect_plat('Avanza B 1234 XYZ')
        assert plat == 'B'

    def test_detect_plat_unknown(self, matcher_instance):
        """Return 'unknown' jika tidak ada plat."""
        plat = matcher_instance.detect_plat('Toyota Avanza 2020 Putih')
        assert plat == 'unknown'


# =============================================================================
# TESTS - DETEKSI AVANZA
# =============================================================================
class TestAvanzaDetection:
    """Tests untuk deteksi model Avanza."""

    def test_is_avanza_with_avanza(self, matcher_instance):
        """Judul dengan 'Avanza' harus terdeteksi."""
        assert matcher_instance.is_avanza('Toyota Avanza 2020') is True

    def test_is_avanza_with_veloz(self, matcher_instance):
        """Judul dengan 'Veloz' harus terdeteksi."""
        assert matcher_instance.is_avanza('Toyota Veloz 2020') is True

    def test_is_avanza_case_insensitive(self, matcher_instance):
        """Deteksi harus case insensitive."""
        assert matcher_instance.is_avanza('TOYOTA AVANZA 2020') is True

    def test_is_not_avanza_innova(self, matcher_instance):
        """Innova harus ditolak meski ada 'Toyota'."""
        assert matcher_instance.is_avanza('Toyota Innova 2020') is False

    def test_is_not_avanza_xpander(self, matcher_instance):
        """Xpander harus ditolak."""
        assert matcher_instance.is_avanza('Mitsubishi Xpander 2020') is False

    def test_is_not_avanza_random(self, matcher_instance):
        """Mobil random tanpa keyword harus ditolak."""
        assert matcher_instance.is_avanza('Honda Jazz 2020') is False


# =============================================================================
# TESTS - FULL MATCH
# =============================================================================
class TestFullMatch:
    """Tests untuk full matching process."""

    def test_valid_listing_matches(self, matcher_instance, sample_valid_listing):
        """Listing valid harus match."""
        is_match, enriched = matcher_instance.match(sample_valid_listing)

        assert is_match is True
        assert 'plat' in enriched
        assert 'score' in enriched
        assert enriched['plat'] == 'F'

    def test_filter_listings_returns_matched(self, matcher_instance, sample_listings):
        """filter_listings harus return hanya yang match."""
        matched = matcher_instance.filter_listings(sample_listings)

        # Hanya listing 1 dan 5 yang harusnya match
        # (listing 2 = innova, 3 = tahun 2018, 4 = matic)
        assert len(matched) == 2

        # Harus sorted by score
        assert matched[0]['score'] >= matched[1]['score']

    def test_enriched_listing_has_plat(self, matcher_instance, sample_valid_listing):
        """Matched listing harus punya field plat."""
        _, enriched = matcher_instance.match(sample_valid_listing)
        assert 'plat' in enriched

    def test_enriched_listing_has_score(self, matcher_instance, sample_valid_listing):
        """Matched listing harus punya field score."""
        _, enriched = matcher_instance.match(sample_valid_listing)
        assert 'score' in enriched
        assert 0 <= enriched['score'] <= 100


# =============================================================================
# TESTS - SCORING
# =============================================================================
class TestScoring:
    """Tests untuk sistem scoring."""

    def test_score_bonus_plat_f(self, matcher_instance):
        """Listing dengan plat F harus dapat bonus score."""
        listing_f = {'plat': 'F', 'km': 30000, 'year': 2020, 'price': 150000000}
        listing_b = {'plat': 'B', 'km': 30000, 'year': 2020, 'price': 150000000}

        score_f = matcher_instance.calculate_score(listing_f)
        score_b = matcher_instance.calculate_score(listing_b)

        assert score_f > score_b

    def test_score_bonus_low_km(self, matcher_instance):
        """Listing dengan KM rendah harus dapat bonus."""
        listing_low = {'plat': 'unknown', 'km': 15000, 'year': 2020}
        listing_high = {'plat': 'unknown', 'km': 55000, 'year': 2020}

        score_low = matcher_instance.calculate_score(listing_low)
        score_high = matcher_instance.calculate_score(listing_high)

        assert score_low > score_high

    def test_score_bonus_newer_year(self, matcher_instance):
        """Listing dengan tahun lebih baru harus dapat bonus."""
        listing_2021 = {'plat': 'unknown', 'km': 30000, 'year': 2021}
        listing_2019 = {'plat': 'unknown', 'km': 30000, 'year': 2019}

        score_2021 = matcher_instance.calculate_score(listing_2021)
        score_2019 = matcher_instance.calculate_score(listing_2019)

        assert score_2021 > score_2019


# =============================================================================
# RUN TESTS
# =============================================================================
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
