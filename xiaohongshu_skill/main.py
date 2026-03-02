import argparse
import json
import os
import sys
import re
import logging
from datetime import datetime
from typing import Tuple, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure correct path resolution when running script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaohongshu_skill.generator import ContentGenerator
from xiaohongshu_skill.publisher import XiaohongshuPublisher
from xiaohongshu_skill.models import XiaohongshuNote
from xiaohongshu_skill.cover_generator import CoverGenerator

# Configure logging
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "xiaohongshu.log"), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

DEFAULT_MCP_PORT = 9999 # Deprecated
DEFAULT_MCP_URL = f"http://127.0.0.1:{DEFAULT_MCP_PORT}/mcp" # Deprecated

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process and publish articles to Xiaohongshu")
    parser.add_argument("--input", help="Input file (JSON or text)")
    parser.add_argument("--content", help="Direct content input (string)")
    parser.add_argument("--title", help="Title of the article")
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL, help="[Deprecated] Xiaohongshu MCP service URL")
    parser.add_argument("--dry-run", action="store_true", help="Generate content only, do not publish")
    parser.add_argument("--mock", action="store_true", help="Mock publication (print only)")
    parser.add_argument("--non-headless", action="store_true", help="Run browser in non-headless mode (visible UI)")
    parser.add_argument("--model", default="qwen-plus", help="OpenAI model to use (default: qwen-plus)")
    parser.add_argument("--api-key", help="API Key (overrides env vars DASHSCOPE_API_KEY/OPENAI_API_KEY)")
    parser.add_argument("--no-cover", action="store_true", help="Skip cover image generation")
    return parser.parse_args()

def read_input_data(input_path: str, title_override: Optional[str]) -> list[Tuple[str, str]]:
    """Reads input file or directory and returns list of (title, content)."""
    articles = []
    
    if os.path.isdir(input_path):
        import glob
        logger.info(f"Loading articles from directory: {input_path}")
        json_files = glob.glob(os.path.join(input_path, "*.json"))
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            articles.append((item.get('title', '无标题'), item.get('content', '')))
                    else:
                        articles.append((data.get('title', '无标题'), data.get('content', '')))
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {e}")
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            if input_path.endswith('.json'):
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        articles.append((item.get('title', '无标题'), item.get('content', '')))
                else:
                    articles.append((data.get('title', '无标题'), data.get('content', '')))
            else:
                articles.append((title_override or "未命名文章", f.read()))
                
    return articles

def print_note_preview(note: XiaohongshuNote):
    # Keep print for visual separation in console, but also log content
    logger.info(f"Generated Note: {note.title}")
    print("\n" + "="*20 + " GENERATED NOTE " + "="*20)
    print(f"Title: {note.title}")
    print(f"Tags: {note.tags}")
    if note.cover_image_path:
        print(f"Cover Image: {note.cover_image_path}")
    print("-" * 50)
    print(note.content)
    print("="*56 + "\n")

def _generate_cover_image(note: XiaohongshuNote, output_dir: Optional[str] = None):
    """Generates cover image for the note."""
    try:
        logger.info("Generating cover image...")
        cover_gen = CoverGenerator(output_dir=output_dir) if output_dir else CoverGenerator()
        # Use first tag as subtitle if available, else empty
        subtitle = note.tags[0] if note.tags else ""
        cover_path = cover_gen.generate_cover(note.title, subtitle)
        note.cover_image_path = cover_path
        logger.info(f"Cover image generated: {cover_path}")
    except Exception as e:
        logger.warning(f"Failed to generate cover image: {e}")

def process_article(title: str, content: str, args) -> bool:
    """Generates content and publishes it. Returns True if successful."""
    logger.info(f"Processing article: {title}...")

    # 1. Generate Content
    try:
        generator = ContentGenerator(model=args.model, api_key=args.api_key)
        note = generator.generate_note(content, title)
        
        # Prepare output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize title for folder name
        safe_title = re.sub(r'[\\/*?:"<>|]', "", note.title)[:20]
        output_dir = os.path.join("output", f"{timestamp}_{safe_title}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save content
        content_path = os.path.join(output_dir, "note.json")
        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(note.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Note content saved to: {content_path}")
        
        # 1.5 Generate Cover Image
        if not args.no_cover:
            _generate_cover_image(note, output_dir)

        print_note_preview(note)
        
        if args.dry_run:
            logger.info("Dry run completed. Content not published.")
            return True

        # 2. Publish
        # publisher = XiaohongshuPublisher(service_url=args.mcp_url, mock=args.mock)
        # Updated to use direct xhs-kit integration
        publisher = XiaohongshuPublisher(headless=not args.non_headless, mock=args.mock)
        success = publisher.publish(note)
        
        if success:
            logger.info("✅ Successfully published/queued.")
            return True
        else:
            logger.error("❌ Failed to publish.")
            return False
            
    except Exception as e:
        logger.error(f"An error occurred processing {title}: {e}")
        return False

def main():
    args = parse_arguments()

    if args.content:
        title = args.title or "未命名文章"
        articles = [(title, args.content)]
        logger.info(f"Processing content from command line argument (Title: {title})")
    elif args.input:
        try:
            articles = read_input_data(args.input, args.title)
        except FileNotFoundError:
            logger.error(f"Input file or directory '{args.input}' not found.")
            return
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON file '{args.input}'.")
            return
        except ValueError as e:
            logger.error(f"{e}")
            return
    else:
        logger.error("Error: Either --input or --content must be provided.")
        return

    if not articles:
        logger.warning("No articles found.")
        return

    logger.info(f"Found {len(articles)} articles to process.")
    
    success_count = 0
    fail_count = 0
    
    for title, content in articles:
        if not content:
            logger.warning(f"Skipping empty content for '{title}'")
            continue
            
        if process_article(title, content, args):
            success_count += 1
        else:
            fail_count += 1
            
    logger.info(f"Batch processing complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
