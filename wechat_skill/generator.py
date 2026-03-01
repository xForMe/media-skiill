import os
import logging
import json
from typing import Optional, List, Dict
from openai import OpenAI
from .models import WeChatArticle

logger = logging.getLogger(__name__)

# Constants
MAX_INPUT_LENGTH = 5000
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DIGEST_LENGTH = 50
ARTICLE_MIN_LENGTH = 1500
ARTICLE_MAX_LENGTH = 2500

class WeChatContentGenerator:
    """
    Generates WeChat Official Account articles from input content using an LLM.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "qwen-plus"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("API Key not set (DASHSCOPE_API_KEY or OPENAI_API_KEY). Content generation may fail.")
        
        if not base_url:
            base_url = os.getenv("OPENAI_BASE_URL")
            if not base_url and (model.startswith("qwen") or "aliyun" in model):
                 base_url = DEFAULT_QWEN_BASE_URL
        
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.model = model

    def _create_prompt(self, article_title: str, article_content: str) -> str:
        return f"""
        你是一个资深的微信公众号运营专家。请将以下文章内容改写成一篇适合微信公众号发布的文章。
        
        原文标题：{article_title}
        原文内容：
        {article_content[:MAX_INPUT_LENGTH]}
        
        要求：
        1. **标题**：吸引人点击，带有深度或情绪价值，长度控制在20字以内。
        2. **摘要（Digest）**：简明扼要，吸引读者打开，{DIGEST_LENGTH}字以内。
        3. **作者**：根据内容推测合适的作者名（如“科技观察”、“深度思考”等），或者留空。
        4. **正文**：
           - 字数：{ARTICLE_MIN_LENGTH}-{ARTICLE_MAX_LENGTH}字左右，保持深度和连贯性。
           - 结构清晰，分段落，使用小标题（Markdown格式 `##` 或 HTML `<h2>`）。
           - 语言风格：专业、有深度、易于阅读，适当加入引导互动的语句。
           - 排版：尽量使用Markdown格式，或者简单的HTML标签（<p>, <strong>, <ul>, <li>, <blockquote>）。
           - 结尾：包含引导关注或点赞的结束语。
        
        请以JSON格式返回结果，包含以下字段：
        - `title`: 标题
        - `author`: 作者（可选）
        - `digest`: 摘要
        - `content`: 正文（Markdown或HTML格式）
        
        注意：content字段中不需要包含标题，只包含正文内容。
        """

    def _get_style_suggestion(self, title: str, content: str) -> str:
        """Helper to suggest visual style based on keywords."""
        text = title + content[:200]
        if any(k in text for k in ["AI", "科技", "模型", "芯片", "代码", "未来", "机器人"]):
            return "Futuristic, Sci-fi, High-tech, 3D abstract, Cyberpunk"
        if any(k in text for k in ["财经", "股市", "商业", "经济", "英伟达", "投资", "市场"]):
            return "Minimalist business, Data visualization style, Professional, Clean, Isometric"
        if any(k in text for k in ["生活", "情感", "故事", "家庭", "教育"]):
            return "Warm photography, Ghibli style, Soft lighting, Illustration"
        return "Modern digital art, Creative, Abstract, High quality, 8k resolution"

    def _create_image_prompt(self, article_title: str, article_content: str) -> str:
        style = self._get_style_suggestion(article_title, article_content)
        return f"""
        你是一个专业的AI视觉艺术指导和提示词（Prompt）生成专家。请根据以下文章标题和内容摘要，设计一个用于生成微信公众号封面图的提示词。
        
        文章标题：{article_title}
        文章内容摘要：
        {article_content[:2000]}
        
        任务要求：
        1. **深度理解**：首先分析文章的核心主题、关键隐喻和情感基调。
        2. **视觉转化**：将文章主题转化为具体的视觉场景、物体或抽象符号。
        3. **构图与风格**：
           - 建议风格：{style}
           - 构图：主体突出，适合横版展示（2.35:1），留有一定呼吸感。
           - 色调：与文章情感一致。
        4. **Prompt输出格式**：
           - 请直接返回一段英文Prompt（英文在绘图模型中效果更好）。
           - 包含：主体描述 + 环境/背景 + 艺术风格 + 构图/视角 + 光影/色彩 + 质量修饰词（如 8k resolution, highly detailed, cinematic lighting）。
           - 长度适中，关键词丰富。
        5. **限制**：
           - 严禁包含任何文字（Text）、字母或水印。
           - 不要返回任何解释性文字，只返回Prompt本身。
        """

    def generate_cover_prompt(self, article_title: str, article_content: str) -> str:
        """
        Generates an image prompt for the article cover.
        """
        prompt = self._create_image_prompt(article_title, article_content)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的AI绘画提示词生成专家。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating cover prompt: {e}")
            return f"A creative cover image for an article titled '{article_title}', modern style, abstract background."

    def generate_article(self, article_content: str, article_title: str) -> WeChatArticle:
        """
        Converts article content into a WeChat Official Account article.
        """
        logger.info(f"Generating WeChat article for: {article_title}")
        
        prompt = self._create_prompt(article_title, article_content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的微信公众号文章写手，擅长将素材转化为高质量的公众号文章。输出必须是JSON格式。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content_str = response.choices[0].message.content
            if not content_str:
                raise ValueError("Empty response from LLM")
                
            data = json.loads(content_str)
            
            return WeChatArticle(
                title=data.get("title", article_title),
                content=data.get("content", ""),
                author=data.get("author", "AI助手"),
                digest=data.get("digest", "")
            )
            
        except Exception as e:
            logger.error(f"Error generating WeChat article: {e}")
            # Return a basic article if generation fails
            return WeChatArticle(
                title=f"【自动生成】{article_title}",
                content=article_content,
                digest=article_content[:50] + "...",
                author="System"
            )
