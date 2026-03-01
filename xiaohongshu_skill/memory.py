import sqlite3
import logging
import hashlib
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class XiaohongshuMemory:
    """
    Manages persistent storage of published Xiaohongshu notes to avoid duplicates.
    Uses SQLite.
    """
    def __init__(self, db_path: str = "xiaohongshu_published.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS published_notes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT UNIQUE,
                            content_hash TEXT,
                            publish_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status TEXT
                        )
                    """)
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")

    def _calculate_hash(self, content: str) -> str:
        """Calculate MD5 hash of the content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def is_published(self, title: str) -> bool:
        """Check if a note with the given title has already been published."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM published_notes WHERE title = ? AND status = 'published'", 
                    (title,)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error checking duplicate: {e}")
            return False

    def add_record(self, title: str, content: str, status: str = "published"):
        """Add a published note record to the memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                content_hash = self._calculate_hash(content)
                with conn:
                    cursor = conn.cursor()
                    # Use INSERT OR REPLACE to update status if re-publishing a failed attempt
                    # or if we want to allow overwriting (though business logic might prevent it first)
                    # Here we use INSERT OR REPLACE to update the timestamp and status if it exists.
                    # But wait, if is_published checks for 'published' status, we should be careful.
                    # If it was failed, we want to allow retry.
                    
                    # First check if it exists
                    cursor.execute("SELECT id FROM published_notes WHERE title = ?", (title,))
                    row = cursor.fetchone()
                    
                    if row:
                        # Update existing record
                        cursor.execute(
                            """
                            UPDATE published_notes 
                            SET content_hash = ?, publish_time = CURRENT_TIMESTAMP, status = ?
                            WHERE title = ?
                            """,
                            (content_hash, status, title)
                        )
                    else:
                        # Insert new record
                        cursor.execute(
                            """
                            INSERT INTO published_notes (title, content_hash, status)
                            VALUES (?, ?, ?)
                            """,
                            (title, content_hash, status)
                        )
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error adding record: {e}")
