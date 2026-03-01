import unittest
import os
import sys
import time
import json
import sqlite3

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from newrank_skill.memory import MemoryBank
from newrank_skill.models import Article

class TestMemoryBank(unittest.TestCase):
    def setUp(self):
        # Use a unique DB file for each test to avoid locking issues
        self.test_db = f"test_memory_{self._testMethodName}_{int(time.time())}.db"
        self.memory = MemoryBank(self.test_db)

    def tearDown(self):
        del self.memory
        import gc
        gc.collect() # Force garbage collection
        
        time.sleep(0.1)
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                print(f"Warning: Could not remove {self.test_db} (locked).")

    def test_add_and_check_duplicate(self):
        article = Article(
            title="Test Title",
            pub_time="2023-01-01",
            author="Author",
            account_id="acc1",
            summary="Summary",
            content="Content",
            read_count=100,
            like_count=10
        )
        
        # Should not be duplicate initially
        self.assertFalse(self.memory.is_duplicate(article))
        
        # Add article
        self.memory.add_article(article)
        
        # Should be duplicate now
        self.assertTrue(self.memory.is_duplicate(article))
        
        # Verify raw_data is JSON
        conn = sqlite3.connect(self.test_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_data FROM articles WHERE title=?", (article.title,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            raw_data = row[0]
            try:
                json_obj = json.loads(raw_data)
                self.assertEqual(json_obj["title"], "Test Title")
            except json.JSONDecodeError:
                self.fail("raw_data is not valid JSON")
        finally:
            conn.close()

    def test_filter_new_articles(self):
        a1 = Article(title="A1", pub_time="2023-01-01", author="A", account_id="1", summary="", content="", read_count=0, like_count=0)
        a2 = Article(title="A2", pub_time="2023-01-01", author="A", account_id="1", summary="", content="", read_count=0, like_count=0)
        
        self.memory.add_article(a1)
        
        filtered = self.memory.filter_new_articles([a1, a2])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "A2")

    def test_batch_add(self):
        articles = [
            Article(title=f"Title {i}", pub_time="2023-01-01", author="A", account_id="1", summary="", content="", read_count=0, like_count=0)
            for i in range(5)
        ]
        
        self.memory.batch_add_articles(articles)
        
        # Verify all added
        for a in articles:
            self.assertTrue(self.memory.is_duplicate(a))
            
        # Verify count
        conn = sqlite3.connect(self.test_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM articles")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 5)
        finally:
            conn.close()

if __name__ == "__main__":
    unittest.main()
