import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from .models import Article

logger = logging.getLogger(__name__)

class MemoryBank:
    """
    Manages persistent storage of crawled articles to avoid duplicates.
    Uses SQLite.
    """
    def __init__(self, db_path: str = "crawled_memory.db"):
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
                        CREATE TABLE IF NOT EXISTS articles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT,
                            pub_time TEXT,
                            account_id TEXT,
                            author TEXT,
                            url TEXT,
                            raw_data TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(title, pub_time)
                        )
                    """)
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")

    def is_duplicate(self, article: Article) -> bool:
        """Check if an article already exists in the memory bank."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                # Check by title and pub_time (assuming these define uniqueness for now)
                # account_id is optional in Article model, so handle carefully
                pub_time = article.pub_time or ""
                cursor.execute(
                    "SELECT 1 FROM articles WHERE title = ? AND pub_time = ?", 
                    (article.title, pub_time)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error checking duplicate: {e}")
            return False

    def add_article(self, article: Article):
        """Add an article to the memory bank."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                with conn:
                    cursor = conn.cursor()
                    pub_time = article.pub_time or ""
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO articles (title, pub_time, account_id, author, raw_data)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            article.title, 
                            pub_time, 
                            article.account_id, 
                            article.author,
                            json.dumps(article.to_dict(), ensure_ascii=False)
                        )
                    )
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error adding article: {e}")

    def filter_new_articles(self, articles: List[Article]) -> List[Article]:
        """Filter out duplicates from a list of articles using a single connection."""
        new_articles = []
        if not articles:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                for article in articles:
                    pub_time = article.pub_time or ""
                    cursor.execute(
                        "SELECT 1 FROM articles WHERE title = ? AND pub_time = ?", 
                        (article.title, pub_time)
                    )
                    if cursor.fetchone() is None:
                        new_articles.append(article)
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error filtering articles: {e}")
            # On error, to be safe, return empty list to avoid processing duplicates
            return []
            
        return new_articles

    def batch_add_articles(self, articles: List[Article]):
        """Add multiple articles to memory bank."""
        if not articles:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            try:
                with conn:
                    cursor = conn.cursor()
                    data = [
                        (
                            a.title, 
                            a.pub_time or "", 
                            a.account_id, 
                            a.author,
                            json.dumps(a.to_dict(), ensure_ascii=False)
                        ) for a in articles
                    ]
                    cursor.executemany(
                        """
                        INSERT OR IGNORE INTO articles (title, pub_time, account_id, author, raw_data)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        data
                    )
                    logger.info(f"Added {cursor.rowcount} new items to memory bank.")
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database error in batch add: {e}")
