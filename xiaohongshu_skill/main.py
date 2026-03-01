import argparse
import json
import os
import sys
import re
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

DEFAULT_MCP_PORT = 9999 # Deprecated
DEFAULT_MCP_URL = f"http://127.0.0.1:{DEFAULT_MCP_PORT}/mcp" # Deprecated

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process and publish articles to Xiaohongshu")
    parser.add_argument("--input", required=True, help="Input file (JSON or text)")
    parser.add_argument("--title", help="Title of the article (if input is text)")
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL, help="[Deprecated] Xiaohongshu MCP service URL")
    parser.add_argument("--dry-run", action="store_true", help="Generate content only, do not publish")
    parser.add_argument("--mock", action="store_true", help="Mock publication (print only)")
    parser.add_argument("--non-headless", action="store_true", help="Run browser in non-headless mode (visible UI)")
    parser.add_argument("--model", default="qwen-plus", help="OpenAI model to use (default: qwen-plus)")
    parser.add_argument("--api-key", help="API Key (overrides env vars DASHSCOPE_API_KEY/OPENAI_API_KEY)")
    parser.add_argument("--no-cover", action="store_true", help="Skip cover image generation")
    return parser.parse_args()

def read_input_file(input_path: str, title_override: Optional[str]) -> Tuple[str, str]:
    """Reads input file and returns (title, content)."""
    with open(input_path, 'r', encoding='utf-8') as f:
        if input_path.endswith('.json'):
            data = json.load(f)
            # Handle list of articles (take first) or single object
            if isinstance(data, list):
                if len(data) > 0:
                    article = data[0]
                    return article.get('title', '无标题'), article.get('content', '')
                else:
                    raise ValueError("JSON file is empty list.")
            else:
                return data.get('title', '无标题'), data.get('content', '')
        else:
            return title_override or "未命名文章", f.read()

def print_note_preview(note: XiaohongshuNote):
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
        print("Generating cover image...")
        cover_gen = CoverGenerator(output_dir=output_dir) if output_dir else CoverGenerator()
        # Use first tag as subtitle if available, else empty
        subtitle = note.tags[0] if note.tags else ""
        cover_path = cover_gen.generate_cover(note.title, subtitle)
        note.cover_image_path = cover_path
    except Exception as e:
        print(f"Warning: Failed to generate cover image: {e}")

def process_article(title: str, content: str, args):
    """Generates content and publishes it."""
    print(f"Processing article: {title}...")

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
        print(f"Note content saved to: {content_path}")
        
        # 1.5 Generate Cover Image
        if not args.no_cover:
            _generate_cover_image(note, output_dir)

        print_note_preview(note)
        
        if args.dry_run:
            print("Dry run completed. Content not published.")
            return

        # 2. Publish
        # publisher = XiaohongshuPublisher(service_url=args.mcp_url, mock=args.mock)
        # Updated to use direct xhs-kit integration
        publisher = XiaohongshuPublisher(headless=not args.non_headless, mock=args.mock)
        success = publisher.publish(note)
        
        if success:
            print("✅ Successfully published/queued.")
        else:
            print("❌ Failed to publish.")
            sys.exit(1)
            
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def main():
    args = parse_arguments()

    try:
        title, content = read_input_file(args.input, args.title)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON file '{args.input}'.")
        return
    except ValueError as e:
        print(f"Error: {e}")
        return

    if not content:
        print("Error: Content is empty.")
        return

    process_article(title, content, args)

if __name__ == "__main__":
    main()
