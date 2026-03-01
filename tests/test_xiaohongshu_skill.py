import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaohongshu_skill.models import XiaohongshuNote
from xiaohongshu_skill.generator import ContentGenerator
from xiaohongshu_skill.publisher import XiaohongshuPublisher

class TestXiaohongshuSkill(unittest.TestCase):

    def test_note_model(self):
        note = XiaohongshuNote(title="Test", content="Content", tags=["#test"])
        self.assertEqual(note.title, "Test")
        self.assertEqual(note.to_dict()["title"], "Test")

    @patch("xiaohongshu_skill.generator.OpenAI")
    def test_generator_success(self, mock_openai):
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"title": "Emoji Title✨", "content": "Short content", "tags": ["#fun"]}'
        mock_client.chat.completions.create.return_value = mock_response

        generator = ContentGenerator(api_key="fake-key")
        note = generator.generate_note("Long article content...", "Original Title")

        self.assertEqual(note.title, "Emoji Title✨")
        self.assertEqual(note.content, "Short content")
        self.assertIn("#fun", note.tags)

    @patch("xiaohongshu_skill.generator.OpenAI")
    def test_generator_failure_fallback(self, mock_openai):
        # Mock OpenAI to raise exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        generator = ContentGenerator(api_key="fake-key")
        note = generator.generate_note("Long article content...", "Original Title")

        # Check fallback behavior
        self.assertIn("Original Title", note.title)
        self.assertIn("生成失败", note.content)

if __name__ == "__main__":
    unittest.main()
