import sqlite3
import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

class WeChatMemory:
    """
    Manages persistent storage of published WeChat articles to avoid duplicates.
    Uses SQLite.
    """
    def __init__(self, db_path: str = "wechat_published.db"):
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
                        CREATE TABLE IF NOT EXISTS published_articles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT UNIQUE,
                            content_hash TEXT,
                            publish_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            media_id TEXT,
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
        """Check if an article with the given title has already been published."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM published_articles WHERE title = ? AND status = 'published'", 
                    (title,)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error checking duplicate: {e}")
            return False

    def add_record(self, title: str, content: str, media_id: Optional[str] = None, status: str = "published"):
        """Add a published article record to the memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                content_hash = self._calculate_hash(content)
                with conn:
                    cursor = conn.cursor()
                    
                    # Check if exists
                    cursor.execute("SELECT id FROM published_articles WHERE title = ?", (title,))
                    row = cursor.fetchone()
                    
                    if row:
                        # Update existing record
                        cursor.execute(
                            """
                            UPDATE published_articles 
                            SET content_hash = ?, publish_time = CURRENT_TIMESTAMP, media_id = ?, status = ?
                            WHERE title = ?
                            """,
                            (content_hash, media_id, status, title)
                        )
                    else:
                        # Insert new record
                        cursor.execute(
                            """
                            INSERT INTO published_articles (title, content_hash, media_id, status)
                            VALUES (?, ?, ?, ?)
                            """,
                            (title, content_hash, media_id, status)
                        )
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error adding record: {e}")
