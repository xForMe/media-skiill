import unittest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wechat_skill.models import WeChatArticle
from wechat_skill.generator import WeChatContentGenerator
from wechat_skill.cover_generator import WeChatCoverGenerator

class TestWeChatSkill(unittest.TestCase):

    def setUp(self):
        # Set up a dummy API key for testing
        self.api_key = "test_key"
        self.generator = WeChatContentGenerator(api_key=self.api_key)

    def test_article_model(self):
        """Test WeChatArticle model serialization."""
        article = WeChatArticle(
            title="Test Title",
            content="Test Content",
            author="Test Author",
            digest="Test Digest"
        )
        data = article.to_dict()
        self.assertEqual(data["title"], "Test Title")
        self.assertEqual(data["author"], "Test Author")
        self.assertEqual(data["digest"], "Test Digest")
        self.assertEqual(data["content"], "Test Content")

    def test_style_suggestion(self):
        """Test style suggestion logic based on keywords."""
        # AI/Tech keywords
        style_ai = self.generator._get_style_suggestion("AI技术发展", "未来大模型")
        self.assertIn("Futuristic", style_ai)
        
        # Finance keywords
        style_finance = self.generator._get_style_suggestion("股市行情", "英伟达财报")
        self.assertIn("Minimalist business", style_finance)
        
        # Life/Emotion keywords
        style_life = self.generator._get_style_suggestion("家庭教育", "感人故事")
        self.assertIn("Warm photography", style_life)
        
        # Default
        style_default = self.generator._get_style_suggestion("普通文章", "无特殊关键词")
        self.assertIn("Modern digital art", style_default)

    def test_create_image_prompt_template(self):
        """Test that the image prompt template is generated correctly."""
        title = "Test Article"
        content = "This is a test article content about AI."
        
        prompt = self.generator._create_image_prompt(title, content)
        
        self.assertIn("你是一个专业的AI视觉艺术指导", prompt)
        self.assertIn(f"文章标题：{title}", prompt)
        self.assertIn("Futuristic", prompt) # Should match AI keywords in content
        self.assertIn("**深度理解**", prompt)
        self.assertIn("**视觉转化**", prompt)

    @patch("wechat_skill.generator.OpenAI")
    def test_generate_cover_prompt_mock(self, mock_openai):
        """Test generate_cover_prompt with mocked OpenAI response."""
        # Mock OpenAI client and response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "A futuristic city skyline with glowing neon lights."
        mock_client.chat.completions.create.return_value = mock_response

        # Re-initialize generator to use the mocked client
        generator = WeChatContentGenerator(api_key="test_key")
        
        prompt = generator.generate_cover_prompt("AI City", "Future technology")
        
        self.assertEqual(prompt, "A futuristic city skyline with glowing neon lights.")
        mock_client.chat.completions.create.assert_called_once()

    @unittest.skipIf(not os.getenv("DASHSCOPE_API_KEY"), "DASHSCOPE_API_KEY not set")
    def test_generate_cover_prompt_integration(self):
        """Integration test with real API (skipped if no key)."""
        real_generator = WeChatContentGenerator() # Uses env var
        title = "AI大模型重塑未来教育"
        content = "随着人工智能技术的飞速发展，大模型正在深刻改变教育行业的面貌。"
        
        prompt = real_generator.generate_cover_prompt(title, content)
        print(f"\nGenerated Prompt (Integration): {prompt}")
        
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 10)

if __name__ == "__main__":
    unittest.main()
