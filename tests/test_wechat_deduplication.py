import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wechat_skill.memory import WeChatMemory
from wechat_skill.main import process_article
from wechat_skill.generator import WeChatContentGenerator
from wechat_skill.models import WeChatArticle

class TestWeChatDeduplication(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_wechat_published.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.memory = WeChatMemory(db_path=self.test_db)
        
    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    @patch("wechat_skill.main.os.makedirs")
    @patch("wechat_skill.main.open")
    @patch("wechat_skill.main.json.dump")
    def test_deduplication(self, mock_json, mock_open, mock_makedirs):
        # Mock generator
        mock_generator = MagicMock(spec=WeChatContentGenerator)
        mock_article = WeChatArticle(title="Test Title", content="Content", author="Author")
        mock_generator.generate_article.return_value = mock_article
        mock_generator.generate_cover_prompt.return_value = "prompt"
        
        # Mock args
        mock_args = MagicMock()
        mock_args.output_dir = "test_output"
        mock_args.sync = True
        mock_args.dry_run = False
        mock_args.no_ai_cover = True # Skip cover gen
        
        # Mock client
        mock_client = MagicMock()
        mock_client.upload_image.return_value = "media_123"
        mock_client.add_draft.return_value = "draft_456"
        
        # Manually set cover path to bypass file check or mock os.path.exists
        mock_article.cover_image_path = "dummy.jpg"
        
        with patch("os.path.exists", return_value=True):
             # First run - should succeed and add to memory
            process_article(
                {"title": "Test Title", "content": "Content"}, 
                mock_generator, 
                mock_args, 
                mock_client,
                memory=self.memory
            )
            
            # Verify added to memory
            self.assertTrue(self.memory.is_published("Test Title"))
            mock_client.add_draft.assert_called_once()
            mock_client.add_draft.reset_mock()
            
            # Second run - should be skipped
            process_article(
                {"title": "Test Title", "content": "Content"}, 
                mock_generator, 
                mock_args, 
                mock_client,
                memory=self.memory
            )
            
            # Verify NOT called again
            mock_client.add_draft.assert_not_called()

if __name__ == "__main__":
    unittest.main()
