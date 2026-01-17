"""
storage.py - SQLite Storage untuk Deduplication & Rate Limiting

Menyimpan:
- seen_listings: listing yang sudah pernah ditemukan (dedup)
- notification_log: log notifikasi untuk rate limiting
- error_log: log error untuk anti-spam error notification
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from config import config


class Storage:
    """SQLite storage manager untuk bot."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize storage.

        Args:
            db_path: Path ke database file. Default dari config.
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection dengan row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tabel untuk tracking listing yang sudah dilihat
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                price INTEGER,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(listing_id, source)
            )
        ''')

        # Index untuk pencarian cepat
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_listing_source
            ON seen_listings(listing_id, source)
        ''')

        # Tabel untuk log notifikasi (rate limiting)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                listing_id TEXT,
                success INTEGER DEFAULT 1
            )
        ''')

        # Tabel untuk log error (anti-spam error notification)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT,
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def is_listing_seen(self, listing_id: str, source: str) -> bool:
        """
        Cek apakah listing sudah pernah dilihat.

        Args:
            listing_id: ID unik listing
            source: Sumber listing (olx, carmudi, dll)

        Returns:
            True jika sudah pernah dilihat
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT 1 FROM seen_listings WHERE listing_id = ? AND source = ?',
            (listing_id, source)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def mark_listing_seen(
        self,
        listing_id: str,
        source: str,
        url: str,
        title: Optional[str] = None,
        price: Optional[int] = None
    ) -> None:
        """
        Tandai listing sebagai sudah dilihat.

        Args:
            listing_id: ID unik listing
            source: Sumber listing
            url: URL listing
            title: Judul listing (opsional)
            price: Harga listing (opsional)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT OR IGNORE INTO seen_listings
                   (listing_id, source, url, title, price)
                   VALUES (?, ?, ?, ?, ?)''',
                (listing_id, source, url, title, price)
            )
            conn.commit()
        finally:
            conn.close()

    def get_notification_count_last_hour(self) -> int:
        """
        Hitung jumlah notifikasi yang dikirim dalam 1 jam terakhir.

        Returns:
            Jumlah notifikasi
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        one_hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute(
            '''SELECT COUNT(*) FROM notification_log
               WHERE sent_at > ? AND success = 1''',
            (one_hour_ago.isoformat(),)
        )
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def can_send_notification(self) -> bool:
        """
        Cek apakah masih bisa kirim notifikasi (rate limit).

        Returns:
            True jika masih dalam batas
        """
        return self.get_notification_count_last_hour() < config.MAX_NOTIFICATIONS_PER_HOUR

    def log_notification(self, listing_id: str, success: bool = True) -> None:
        """
        Log notifikasi yang dikirim.

        Args:
            listing_id: ID listing yang dikirim
            success: Apakah berhasil dikirim
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO notification_log (listing_id, success) VALUES (?, ?)',
            (listing_id, 1 if success else 0)
        )
        conn.commit()
        conn.close()

    def can_send_error_notification(self, error_type: str) -> bool:
        """
        Cek apakah bisa kirim notifikasi error (max 1 per jam per jenis error).

        Args:
            error_type: Jenis error

        Returns:
            True jika bisa kirim
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        one_hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute(
            '''SELECT COUNT(*) FROM error_log
               WHERE error_type = ? AND notified_at > ?''',
            (error_type, one_hour_ago.isoformat())
        )
        count = cursor.fetchone()[0]
        conn.close()

        return count < config.MAX_ERROR_NOTIFICATIONS_PER_HOUR

    def log_error_notification(self, error_type: str, error_message: str) -> None:
        """
        Log error notification yang dikirim.

        Args:
            error_type: Jenis error
            error_message: Pesan error
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO error_log (error_type, error_message) VALUES (?, ?)',
            (error_type, error_message)
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """
        Dapatkan statistik storage.

        Returns:
            Dict dengan statistik
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total listings
        cursor.execute('SELECT COUNT(*) FROM seen_listings')
        total_listings = cursor.fetchone()[0]

        # Listings per source
        cursor.execute(
            'SELECT source, COUNT(*) as count FROM seen_listings GROUP BY source'
        )
        by_source = {row['source']: row['count'] for row in cursor.fetchall()}

        # Notifikasi hari ini
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute(
            'SELECT COUNT(*) FROM notification_log WHERE sent_at > ?',
            (today.isoformat(),)
        )
        notifs_today = cursor.fetchone()[0]

        conn.close()

        return {
            'total_listings': total_listings,
            'by_source': by_source,
            'notifications_today': notifs_today,
            'notifications_last_hour': self.get_notification_count_last_hour()
        }

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Hapus data lama untuk menghemat ruang.

        Args:
            days: Hapus data lebih tua dari X hari

        Returns:
            Jumlah baris yang dihapus
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=days)

        # Hapus notification log lama
        cursor.execute(
            'DELETE FROM notification_log WHERE sent_at < ?',
            (cutoff.isoformat(),)
        )
        deleted_notifs = cursor.rowcount

        # Hapus error log lama
        cursor.execute(
            'DELETE FROM error_log WHERE notified_at < ?',
            (cutoff.isoformat(),)
        )
        deleted_errors = cursor.rowcount

        conn.commit()
        conn.close()

        return deleted_notifs + deleted_errors


# Singleton instance
storage = Storage()
