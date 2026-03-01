import os
import sys
import json
import unittest

# Add project root to sys.path to ensure newrank_skill can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from newrank_skill.crawler import NewRankCrawler

class TestNewRankCrawler(unittest.TestCase):
    def setUp(self):
        self.output_file = "test_output.json"
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_crawl(self):
        db_path = "test_crawl_memory.db"
        # Ensure clean state for DB
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except:
                pass

        crawler = NewRankCrawler(output_file=self.output_file, db_path=db_path)
        
        try:
            crawler.run()
            
            self.assertTrue(os.path.exists(self.output_file), "Output file should exist")
            
            with open(self.output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.assertTrue(len(data) > 0, "Should have collected at least one item")
            
            first_item = data[0]
            self.assertIn("title", first_item)
            self.assertIn("content", first_item)
            print(f"Verified {len(data)} items collected.")
        finally:
            if os.path.exists("test_crawl_memory.db"):
                try:
                    os.remove("test_crawl_memory.db")
                except:
                    pass

if __name__ == "__main__":
    unittest.main()
