import argparse
import os
import sys
import logging
import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wechat_skill.generator import WeChatContentGenerator
from wechat_skill.models import WeChatArticle
from wechat_skill.wechat_client import WeChatClient
from wechat_skill.cover_generator import WeChatCoverGenerator
from wechat_skill.memory import WeChatMemory

# Configure logging
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "wechat.log"), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

PREVIEW_CONTENT_LENGTH = 500
FILENAME_MAX_LENGTH = 50

def setup_args():
    parser = argparse.ArgumentParser(description="Generate and Sync WeChat Official Account Articles")
    parser.add_argument("--input", help="Path to input JSON file (e.g., newrank_hot_subjects.json)", required=True)
    parser.add_argument("--output-dir", default="output", help="Directory to save generated content")
    parser.add_argument("--sync", action="store_true", help="Synchronize generated articles to WeChat Draft Box")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but do not save or sync")
    parser.add_argument("--api-key", help="DashScope API Key")
    parser.add_argument("--app-id", help="WeChat App ID")
    parser.add_argument("--app-secret", help="WeChat App Secret")
    parser.add_argument("--image-model", default="qwen-image-max", help="AI Image Generation Model (e.g., qwen-image-max, wanx-v1)")
    parser.add_argument("--no-ai-cover", action="store_true", help="Disable AI cover generation (use solid color)")
    return parser.parse_args()

def _save_article_locally(article: WeChatArticle, output_dir: str):
    """Save article content to local file."""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "article.json"), "w", encoding="utf-8") as f:
        json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Article saved to: {output_dir}")

def _generate_cover_image(article: WeChatArticle, generator: WeChatContentGenerator, args, api_key: str, output_dir: str):
    """Generate cover image for the article."""
    image_prompt = None
    if not args.no_ai_cover:
        try:
            image_prompt = generator.generate_cover_prompt(article.title, article.content)
            logger.info(f"Generated AI Image Prompt: {image_prompt}")
        except Exception as e:
            logger.error(f"Failed to generate image prompt: {e}")

    cover_generator = WeChatCoverGenerator(output_dir=output_dir, api_key=api_key, model=args.image_model)
    try:
        cover_path = cover_generator.generate_cover(article.title, article.author, prompt=image_prompt)
        article.cover_image_path = cover_path
    except Exception as e:
        logger.error(f"Failed to generate cover image: {e}")

def _sync_to_wechat(article: WeChatArticle, client: WeChatClient, memory: Optional[WeChatMemory]):
    """Sync article to WeChat draft box."""
    try:
        logger.info("Syncing to WeChat...")
        thumb_media_id = None
        if article.cover_image_path and os.path.exists(article.cover_image_path):
            thumb_media_id = client.upload_image(article.cover_image_path)
            article.thumb_media_id = thumb_media_id
        else:
            logger.warning("No cover image available. Sync might fail if thumb_media_id is required.")
            
        if thumb_media_id:
            media_id = client.add_draft([article.to_dict()])
            logger.info(f"Draft synced successfully! Media ID: {media_id}")
            if memory:
                memory.add_record(article.title, article.content, media_id=media_id)
        else:
            logger.error("Skipping sync because cover image upload failed (thumb_media_id missing).")
    except Exception as e:
        logger.error(f"Sync failed: {e}")

def _print_preview(article: WeChatArticle):
    """Print article preview to console."""
    print("\n" + "="*20 + " GENERATED ARTICLE " + "="*20)
    print(f"Title: {article.title}")
    print(f"Author: {article.author}")
    print(f"Digest: {article.digest}")
    print("-" * 50)
    content_preview = article.content[:PREVIEW_CONTENT_LENGTH] + "..." if len(article.content) > PREVIEW_CONTENT_LENGTH else article.content
    print(content_preview)
    print("="*60 + "\n")

def process_article(article_data: dict, generator: WeChatContentGenerator, args, client: WeChatClient = None, api_key: str = None, memory: WeChatMemory = None):
    title = article_data.get("title", "")
    content = article_data.get("content", "")
    
    if not title or not content:
        logger.warning(f"Skipping empty article: {title}")
        return

    # Check memory before processing
    if memory and memory.is_published(title):
        logger.info(f"Article '{title}' already published. Skipping.")
        return

    logger.info(f"Processing article: {title}")
    
    # 1. Generate Content
    article = generator.generate_article(content, title)
    
    # 2. Save to Output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join([c for c in article.title if c.isalnum() or c in (' ', '-', '_')]).strip()[:FILENAME_MAX_LENGTH]
    output_dir = os.path.join(args.output_dir, f"wechat_{timestamp}_{safe_title}")
    
    if not args.dry_run:
        _save_article_locally(article, output_dir)
        _generate_cover_image(article, generator, args, api_key, output_dir)
        
        # Update article json with cover path
        _save_article_locally(article, output_dir)

    # 4. Sync to WeChat (Draft Box)
    if args.sync and client:
        _sync_to_wechat(article, client, memory)

    if args.dry_run:
        _print_preview(article)

def _init_client(args) -> Optional[WeChatClient]:
    """Initialize WeChat Client if syncing is enabled."""
    if not args.sync:
        return None
        
    app_id = args.app_id or os.getenv("WECHAT_APP_ID")
    app_secret = args.app_secret or os.getenv("WECHAT_APP_SECRET")
    
    if not app_id or not app_secret:
        logger.error("WeChat App ID and Secret are required for syncing. Set WECHAT_APP_ID and WECHAT_APP_SECRET env vars.")
        return None
        
    return WeChatClient(app_id, app_secret)

def _load_input_data(input_path: str) -> List[dict]:
    """Load articles from input JSON file or directory of JSON files."""
    articles = []
    
    if os.path.isdir(input_path):
        import glob
        logger.info(f"Loading articles from directory: {input_path}")
        json_files = glob.glob(os.path.join(input_path, "*.json"))
        for file_path in json_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        articles.extend(data)
                    elif isinstance(data, dict) and "articles" in data:
                        articles.extend(data["articles"])
                    else:
                        articles.append(data)
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {e}")
    else:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    articles = data
                elif isinstance(data, dict) and "articles" in data:
                    articles = data["articles"]
                else:
                    articles = [data]
        except Exception as e:
            logger.error(f"Error loading input file: {e}")
            
    return articles

def main():
    load_dotenv()
    args = setup_args()
    
    api_key = args.api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("API Key is required. Set DASHSCOPE_API_KEY env var or use --api-key.")
        return

    # Initialize WeChat Client if syncing
    client = _init_client(args)
    if args.sync and not client:
        return

    # Initialize memory for deduplication
    memory = WeChatMemory()

    generator = WeChatContentGenerator(api_key=api_key)
    
    # Load Input
    articles = _load_input_data(args.input)
    if not articles:
        return

    # Process each article
    for item in articles:
        process_article(item, generator, args, client, api_key=api_key, memory=memory)
        if args.dry_run:
            break # Only process one for dry run

if __name__ == "__main__":
    main()
