import os
import logging
import json
from typing import Optional, List
from openai import OpenAI
from .models import XiaohongshuNote

logger = logging.getLogger(__name__)

# Constants
MAX_INPUT_LENGTH = 5000
TRUNCATE_LENGTH = 200
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

COMMON_TAGS_MAP = { 
    "AI": ["#AI", "#人工智能", "#AIGC"], 
    "模型": ["#大模型", "#AI模型", "#LLM"], 
    "工具": ["#AI工具", "#效率工具", "#生产力工具"], 
    "编程": ["#编程", "#代码", "#开发者"], 
    "ChatGPT": ["#ChatGPT", "#OpenAI"], 
    "Claude": ["#Claude", "#Anthropic"], 
    "GPT": ["#GPT", "#OpenAI"], 
    "Python": ["#Python", "#编程"], 
    "数据": ["#数据分析", "#大数据"], 
    "学习": ["#学习", "#知识分享"], 
    "科技": ["#科技", "#黑科技"], 
    "教程": ["#教程", "#入门教程"], 
}

class ContentGenerator:
    """
    Generates Xiaohongshu-style content from articles using an LLM.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "qwen-plus"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("API Key not set (DASHSCOPE_API_KEY or OPENAI_API_KEY). Content generation may fail.")
        
        # Determine base_url based on model if not provided
        if not base_url:
            base_url = os.getenv("OPENAI_BASE_URL")
            if not base_url and (model.startswith("qwen") or "aliyun" in model):
                 base_url = DEFAULT_QWEN_BASE_URL
        
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.model = model

    def _generate_default_tags(self, title: str, content: str) -> List[str]:
        """
        Generates default tags based on keywords in title and content.
        """
        tags = set()
        text_to_search = (title + " " + content).upper()
        
        for keyword, keyword_tags in COMMON_TAGS_MAP.items():
            if keyword.upper() in text_to_search:
                tags.update(keyword_tags)
                
        # If no tags matched, add a generic one
        if not tags:
            tags.add("#知识分享")
            
        return list(tags)[:5] # Return max 5 unique tags

    def _create_prompt(self, article_title: str, article_content: str) -> str:
        return f"""
        你是一个专业的小红书博主。请将以下文章内容改写成一篇小红书笔记。
        
        文章标题：{article_title}
        文章内容：
        {article_content[:MAX_INPUT_LENGTH]}  # Limit input length to avoid token limits if necessary
        
        要求：
        1. **标题**：吸引人，带有情绪或悬念，加上适当的Emoji。
        2. **正文**：
           - 字数控制在1000字以内。
           - 风格活泼，多使用Emoji（如✨、🔥、💡、👉等）。
           - 提取文章的核心要点，分点陈述。
           - 将长段落压缩，使用短句。
           - 结尾引导互动（如“大家怎么看？评论区聊聊👇”）。
        3. **标签**：生成3-5个相关标签（#）。
        
        请以JSON格式返回结果，包含 'title', 'content' (正文), 'tags' (列表)。
        注意：content字段中不需要包含标题和标签，只包含正文内容。
        """

    def generate_note(self, article_content: str, article_title: str) -> XiaohongshuNote:
        """
        Converts article content into a Xiaohongshu-style note.
        """
        logger.info(f"Generating Xiaohongshu note for article: {article_title}")
        
        prompt = self._create_prompt(article_title, article_content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个熟练的小红书文案专家，擅长将长文章转化为吸引人的笔记。输出必须是JSON格式。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_content = response.choices[0].message.content
            data = json.loads(result_content)
            
            generated_tags = data.get("tags", [])
            
            # If no tags generated or empty list, use default logic
            if not generated_tags:
                generated_tags = self._generate_default_tags(article_title, article_content)
            
            return XiaohongshuNote(
                title=data.get("title", article_title),
                content=data.get("content", ""),
                tags=generated_tags
            )
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            # Fallback: simple truncation if LLM fails
            return XiaohongshuNote(
                title=f"✨{article_title}✨",
                content=article_content[:TRUNCATE_LENGTH] + "... (生成失败，显示原文摘要)",
                tags=self._generate_default_tags(article_title, article_content)
            )
