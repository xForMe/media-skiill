import os
import random
import logging
import requests
import time
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO

logger = logging.getLogger(__name__)

# WeChat Cover Constants (2.35:1 aspect ratio)
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 383
BG_COLOR = (255, 255, 255) # Default white
TITLE_FONT_SIZE = 60
AUTHOR_FONT_SIZE = 30
MAX_TEXT_WIDTH = 800
TITLE_LINE_SPACING = 20
RANDOM_FILENAME_MIN = 1000
RANDOM_FILENAME_MAX = 9999
FALLBACK_TEXT_POS = (100, 100)
OVERLAY_OPACITY = 100
AUTHOR_PADDING = 20
POLLING_INTERVAL = 2
POLLING_MAX_RETRIES = 60
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

# Simple color schemes
COLOR_SCHEMES = [
    ("#1aad19", "#ffffff"), # WeChat Green
    ("#000000", "#ffffff"), # Black & White
    ("#ffffff", "#000000"), # White & Black
    ("#FF5733", "#ffffff"), # Vibrant Orange
    ("#3498DB", "#ffffff"), # Blue
]

class WeChatCoverGenerator:
    """
    Generates cover images for WeChat Official Account articles.
    """
    
    def __init__(self, output_dir: str = "output", api_key: Optional[str] = None, model: Optional[str] = None):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.font_path = self._find_font()
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model or "wanx-v1" # Default to wanx-v1 if not specified, but user requested qwen-image-max

    def _generate_ai_image(self, prompt: str) -> Optional[Image.Image]:
        """
        Generates an image using DashScope API.
        """
        if not self.api_key:
            logger.warning("No API Key provided for AI image generation. Skipping.")
            return None

        # Determine endpoint and payload based on model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.model == "qwen-image-max":
            # Qwen Image Max (Multimodal Generation)
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ]
                },
                "parameters": {
                    "size": "1024*1024"  # Use standard square size
                }
            }
        else:
            # Wanx (Task-based Async)
            api_url = DASHSCOPE_API_URL
            headers["X-DashScope-Async"] = "enable"
            payload = {
                "model": self.model,
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "size": "1280*720", 
                    "n": 1
                }
            }
        
        try:
            logger.info(f"Submitting AI image generation request... Model: {self.model}")
            response = requests.post(api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Error calling DashScope API: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            data = response.json()
            
            # Handle synchronous response (Qwen)
            if self.model == "qwen-image-max":
                if "output" in data and "choices" in data["output"]:
                    try:
                        image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]
                        logger.info(f"Image generated successfully. URL: {image_url}")
                        img_resp = requests.get(image_url)
                        img_resp.raise_for_status()
                        return Image.open(BytesIO(img_resp.content))
                    except (KeyError, IndexError) as e:
                        logger.error(f"Failed to parse Qwen response: {e}")
                        return None
                else:
                    logger.error(f"Unexpected response structure for Qwen: {data}")
                    return None

            # Handle asynchronous task response (Wanx)
            if "output" not in data or "task_id" not in data["output"]:
                logger.error(f"Failed to submit task: {data}")
                return None
                
            task_id = data["output"]["task_id"]
            logger.info(f"Task submitted. ID: {task_id}. Waiting for completion...")
            
            # Poll for result
            for _ in range(POLLING_MAX_RETRIES): 
                time.sleep(POLLING_INTERVAL)
                task_url = DASHSCOPE_TASK_URL.format(task_id=task_id)
                task_resp = requests.get(task_url, headers={"Authorization": f"Bearer {self.api_key}"})
                
                if task_resp.status_code != 200:
                    continue
                    
                task_result = task_resp.json()
                task_status = task_result.get("output", {}).get("task_status", "")
                
                if task_status == "SUCCEEDED":
                    logger.info("Image generation succeeded.")
                    results = task_result.get("output", {}).get("results", [])
                    if results and "url" in results[0]:
                        image_url = results[0]["url"]
                        img_resp = requests.get(image_url)
                        return Image.open(BytesIO(img_resp.content))
                    break
                elif task_status in ["FAILED", "CANCELED"]:
                    logger.error(f"Image generation failed: {task_result}")
                    return None
            
            logger.warning("Image generation timed out.")
            return None
            
        except Exception as e:
            logger.error(f"Error calling DashScope API: {e}")
            return None

    def _find_font(self) -> Optional[str]:
        """Finds a suitable Chinese font on Windows/Linux/Mac."""
        potential_fonts = [
            # Windows
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
            "C:\\Windows\\Fonts\\arialuni.ttf",
            # Linux (e.g., Ubuntu)
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            # Mac
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf"
        ]
        
        # Check env var first
        env_font = os.getenv("WECHAT_COVER_FONT")
        if env_font and os.path.exists(env_font):
            return env_font
            
        for path in potential_fonts:
            if os.path.exists(path):
                return path
                
        logger.warning("No standard Chinese font found. Using default PIL font (may not support Chinese).")
        return None

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wraps text to fit within max_width."""
        lines = []
        current_line = []
        current_width = 0
        
        for char in text:
            # Simple width estimation (getbbox is more accurate but slower per char)
            bbox = font.getbbox(char)
            char_width = bbox[2] - bbox[0]
            
            if current_width + char_width <= max_width:
                current_line.append(char)
                current_width += char_width
            else:
                lines.append("".join(current_line))
                current_line = [char]
                current_width = char_width
                
        if current_line:
            lines.append("".join(current_line))
            
        return lines

    def _process_ai_image(self, ai_img: Image.Image) -> Image.Image:
        """Resizes and crops AI image to fit cover dimensions."""
        target_ratio = CANVAS_WIDTH / CANVAS_HEIGHT
        img_ratio = ai_img.width / ai_img.height
        
        if img_ratio > target_ratio:
            # Image is wider than target, crop width
            new_height = CANVAS_HEIGHT
            new_width = int(new_height * img_ratio)
            ai_img = ai_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - CANVAS_WIDTH) // 2
            ai_img = ai_img.crop((left, 0, left + CANVAS_WIDTH, CANVAS_HEIGHT))
        else:
            # Image is taller/narrower, crop height
            new_width = CANVAS_WIDTH
            new_height = int(new_width / img_ratio)
            ai_img = ai_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - CANVAS_HEIGHT) // 2
            ai_img = ai_img.crop((0, top, CANVAS_WIDTH, top + CANVAS_HEIGHT))
            
        # Darken image to make text readable
        overlay = Image.new('RGBA', ai_img.size, (0, 0, 0, OVERLAY_OPACITY))
        return Image.alpha_composite(ai_img.convert('RGBA'), overlay).convert('RGB')

    def _draw_text_on_image(self, image: Image.Image, title: str, author: str, text_color: Tuple[int, int, int]) -> None:
        """Draws title and author text on the image."""
        draw = ImageDraw.Draw(image)
        try:
            # Title
            title_font = ImageFont.truetype(self.font_path, TITLE_FONT_SIZE) if self.font_path else ImageFont.load_default()
            wrapped_title = self._wrap_text(title, title_font, MAX_TEXT_WIDTH)
            
            # Author
            author_font = ImageFont.truetype(self.font_path, AUTHOR_FONT_SIZE) if self.font_path else ImageFont.load_default()
            
            # Calculate total height for centering
            total_text_height = sum([title_font.getbbox(line)[3] - title_font.getbbox(line)[1] + TITLE_LINE_SPACING for line in wrapped_title])
            
            # Center vertically
            start_y = (CANVAS_HEIGHT - total_text_height) / 2
            current_y = start_y
            
            # Draw Title
            for line in wrapped_title:
                line_bbox = title_font.getbbox(line)
                line_width = line_bbox[2] - line_bbox[0]
                line_height = line_bbox[3] - line_bbox[1]
                x = (CANVAS_WIDTH - line_width) / 2
                draw.text((x, current_y), line, font=title_font, fill=text_color)
                current_y += line_height + TITLE_LINE_SPACING
            
            # Draw Author (bottom right)
            if author:
                author_bbox = author_font.getbbox(author)
                author_width = author_bbox[2] - author_bbox[0]
                author_height = author_bbox[3] - author_bbox[1]
                x = CANVAS_WIDTH - author_width - AUTHOR_PADDING
                y = CANVAS_HEIGHT - author_height - AUTHOR_PADDING
                draw.text((x, y), author, font=author_font, fill=text_color)
                
        except Exception as e:
            logger.error(f"Error drawing text: {e}")
            # Fallback
            draw.text(FALLBACK_TEXT_POS, title, fill=(0,0,0))

    def generate_cover(self, title: str, author: str = "", prompt: Optional[str] = None) -> str:
        """
        Generates a cover image with title and optional author.
        If prompt is provided and API key is set, tries to generate AI background.
        """
        image = None
        
        # Try AI generation first if prompt is available
        if prompt and self.api_key:
            try:
                ai_img = self._generate_ai_image(prompt)
                if ai_img:
                    image = self._process_ai_image(ai_img)
            except Exception as e:
                logger.error(f"AI generation pipeline failed: {e}")

        # Fallback to solid color if no AI image
        if not image:
            bg_hex, text_hex = random.choice(COLOR_SCHEMES)
            bg_color = ImageColor.getrgb(bg_hex)
            text_color = ImageColor.getrgb(text_hex)
            image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), bg_color)
        else:
            text_color = (255, 255, 255) # White text on darkened AI image
        
        self._draw_text_on_image(image, title, author, text_color)
            
        filename = f"wechat_cover_{random.randint(RANDOM_FILENAME_MIN, RANDOM_FILENAME_MAX)}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath, quality=95)
        logger.info(f"Cover image generated: {filepath}")
        return filepath
