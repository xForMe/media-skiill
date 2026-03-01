import os
import sys
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from xiaohongshu_skill.publisher import XiaohongshuPublisher
from xiaohongshu_skill.models import XiaohongshuNote
from xhs_kit.po.models import PublishResponse

class TestXiaohongshuDeduplication(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_xhs_published.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_deduplication(self):
        # Create publisher with test DB
        publisher = XiaohongshuPublisher(headless=True, memory_db_path=self.test_db)
        
        # Mock the client
        mock_client = AsyncMock()
        mock_client.check_login_status.return_value = MagicMock(is_logged_in=True)
        mock_client.publish.return_value = PublishResponse(status="发布完成", note_id="123")
        publisher.client = mock_client
        
        # Also mock _ensure_client to prevent overwriting our mock client
        publisher._ensure_client = AsyncMock()
        
        # Mock _prepare_images to return dummy images
        publisher._prepare_images = MagicMock(return_value=["/path/to/image.jpg"])
        
        # Create a test note
        note = XiaohongshuNote(
            title="Test Unique Title 1",
            content="This is a test content.",
            tags=["test"]
        )
        
        # First publish attempt - should succeed
        print("\n--- First Publish Attempt ---")
        result1 = publisher.publish(note)
        self.assertTrue(result1, "First publish should succeed")
        
        # Verify client.publish was called
        mock_client.publish.assert_called_once()
        mock_client.publish.reset_mock()
        
        # Second publish attempt - should be skipped
        print("\n--- Second Publish Attempt (Duplicate) ---")
        result2 = publisher.publish(note)
        self.assertTrue(result2, "Second publish should return True (as skipped success)")
        
        # Verify client.publish was NOT called
        mock_client.publish.assert_not_called()
        
        print("\n--- Verification Successful: Duplicate publish was skipped ---")

if __name__ == "__main__":
    unittest.main()
