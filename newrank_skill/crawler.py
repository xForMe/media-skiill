import json
import logging
from typing import List, Optional
from playwright.sync_api import sync_playwright, Response
from .models import Article
from .memory import MemoryBank

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewRankCrawler:
    """
    Crawler for NewRank hot subjects.
    Target URL: https://www.newrank.cn/hotInfo?module=hotSubject
    """
    
    BASE_URL = "https://www.newrank.cn/hotInfo?module=hotSubject"
    TARGET_API_PART = "queryMsgs"

    def __init__(self, output_file: str = "newrank_hot_subjects.json", db_path: str = "crawled_memory.db"):
        self.output_file = output_file
        self.results: List[Article] = []
        self.memory_bank = MemoryBank(db_path)


    def _handle_response(self, response: Response):
        """Callback to handle intercepted network responses."""
        if self.TARGET_API_PART in response.url:
            try:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    logger.info(f"Intercepted API response: {response.url}")
                    try:
                        data = response.json()
                        if "data" in data and isinstance(data["data"], dict) and "list" in data["data"]:
                            items = data["data"]["list"]
                            logger.info(f"Found {len(items)} items in this response.")
                            for item in items:
                                article = Article.from_dict(item)
                                self.results.append(article)
                        else:
                            logger.warning(f"Data format mismatch. Keys in data: {list(data.keys())}")
                    except Exception as e:
                        logger.error(f"Error parsing JSON: {e}")
                else:
                     logger.debug(f"Response not JSON: {ct}")
            except Exception as e:
                logger.error(f"Error handling response: {e}")

    def run(self):
        """Execute the crawling process."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Intercept responses
            page.on("response", self._handle_response)
            
            logger.info(f"Navigating to {self.BASE_URL}...")
            page.goto(self.BASE_URL)
            
            # Wait for the API call to complete.
            # Using a fixed timeout for simplicity as the API call is triggered on page load.
            # A more robust approach would be to wait for a specific network idle state or element.
            page.wait_for_timeout(10000)
            
            browser.close()
            
        self._save_results()

    def _save_results(self):
        """Save unique results to JSON file and update memory bank."""
        logger.info(f"Total items collected: {len(self.results)}")
        
        # 1. Deduplicate within current run
        unique_results = {}
        for r in self.results:
            key = f"{r.title}_{r.pub_time}"
            unique_results[key] = r
            
        current_unique_list = list(unique_results.values())
        logger.info(f"Unique items in this run: {len(current_unique_list)}")

        # 2. Filter against memory bank
        new_items = self.memory_bank.filter_new_articles(current_unique_list)
        logger.info(f"New items (not in memory): {len(new_items)}")
        
        if not new_items:
            logger.info("No new items found. Skipping save.")
            return

        # 3. Add to memory bank
        self.memory_bank.batch_add_articles(new_items)
        
        # 4. Save to JSON
        final_list = [item.to_dict() for item in new_items]
        
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(final_list, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(final_list)} new items to {self.output_file}")
        except IOError as e:
            logger.error(f"Failed to save results to {self.output_file}: {e}")

if __name__ == "__main__":
    crawler = NewRankCrawler()
    crawler.run()
