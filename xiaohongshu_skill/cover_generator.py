import os
import random
import logging
import re
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageColor

logger = logging.getLogger(__name__)

# Canvas Constants
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440
MARGIN = 100
MAX_TEXT_WIDTH = CANVAS_WIDTH - (2 * MARGIN)

# Font Constants
TITLE_FONT_SIZE = 120
SUBTITLE_FONT_SIZE = 60
TITLE_LINE_SPACING = 20
SUBTITLE_SPACING = 40
SUBTITLE_EXTRA_MARGIN = 20
SUBTITLE_MAX_CHARS = 20

# Color Schemes (Background, Text, Accent, Name)
COLOR_SCHEMES = [
    ("#1a1a2e", "#ffffff", "#e94560", "深蓝红"),  # 深蓝背景+红色强调
    ("#0f3460", "#ffffff", "#e94560", "午夜蓝"),
    ("#16213e", "#ffffff", "#0f3460", "深空蓝"),
    ("#1a1a2e", "#ffffff", "#ffd700", "黑金"),    # 深蓝背景+金色强调
    ("#2d132c", "#ffffff", "#801336", "深紫红"),
    ("#4a0e4e", "#ffffff", "#81007f", "深紫色"),
    ("#0c0032", "#ffffff", "#5b189a", "星空紫"),
    ("#190028", "#ffffff", "#7b2cbf", "暗夜紫"),
    ("#000000", "#ffffff", "#ff6b6b", "经典黑"),
    ("#1e3a5f", "#ffffff", "#4fc3f7", "冰蓝色"),
]

class CoverGenerator:
    """
    Generates Xiaohongshu-style text cover images.
    """

    def __init__(self, output_dir: str = "output/covers", color_scheme: Optional[str] = None):
        self.output_dir = output_dir
        self.color_scheme_name = color_scheme
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Try to find a system font that supports Chinese
        self.font_path = self._find_font()
        
    def _find_font(self) -> Optional[str]:
        """Finds a suitable Chinese font on Windows."""
        potential_fonts = [
            "simhei.ttf",   # SimHei (Windows) - Often safer than TTC
            "msyh.ttc",     # Microsoft YaHei (Windows)
            "simsun.ttc",   # SimSun
            "arialuni.ttf", # Arial Unicode MS
        ]
        
        font_dirs = [
            "C:\\Windows\\Fonts",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft\\Windows\\Fonts"),
        ]
        
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
            for font_name in potential_fonts:
                path = os.path.join(font_dir, font_name)
                if os.path.exists(path):
                    logger.info(f"Using font: {path}")
                    return path
                
        logger.warning("No standard Chinese font found. Using default PIL font (may not support Chinese).")
        return None

    def _find_emoji_font(self) -> Optional[str]:
        """Finds the Segoe UI Emoji font on Windows."""
        font_dirs = [
            "C:\\Windows\\Fonts",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft\\Windows\\Fonts"),
        ]
        for font_dir in font_dirs:
            path = os.path.join(font_dir, "seguiemj.ttf")
            if os.path.exists(path):
                return path
        return None

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, emoji_font: Optional[ImageFont.FreeTypeFont] = None) -> List[str]:
        """Wraps text to fit within max_width, considering emoji width."""
        lines = []
        current_line = []
        current_width = 0
        
        for char in text:
            # Check if it's an emoji (simple check for SMP or specific ranges could be added)
            is_emoji = ord(char) > 0xFFFF
            current_font = emoji_font if (is_emoji and emoji_font) else font
            
            char_width = current_font.getlength(char)
            
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

    def _get_color_scheme(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
        """Returns the selected or random color scheme (bg, text, accent)."""
        scheme = None
        if self.color_scheme_name:
            for s in COLOR_SCHEMES:
                if s[3] == self.color_scheme_name:
                    scheme = s
                    break
        
        if not scheme:
            scheme = random.choice(COLOR_SCHEMES)
            
        bg_hex, text_hex, accent_hex, _ = scheme
        return (
            ImageColor.getrgb(bg_hex),
            ImageColor.getrgb(text_hex),
            ImageColor.getrgb(accent_hex)
        )

    def _is_light(self, color: Tuple[int, int, int]) -> bool:
        """Determines if a color is light or dark."""
        r, g, b = color
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness > 128

    def _draw_text_line(self, draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: ImageFont.FreeTypeFont, emoji_font: Optional[ImageFont.FreeTypeFont], fill: Tuple[int, int, int]):
        """Draws a line of text with emoji support."""
        x, y = xy
        for char in text:
            is_emoji = ord(char) > 0xFFFF
            current_font = emoji_font if (is_emoji and emoji_font) else font
            
            # For emoji font, we might need to adjust y-offset if baselines differ significantly
            # But usually for title/subtitle it's okay.
            # Note: Segoe UI Emoji often has built-in color (COLR/CPAL). 
            # PIL 10+ handles this better. If older PIL, it might be monochrome.
            
            draw.text((x, y), char, font=current_font, fill=fill)
            x += current_font.getlength(char)

    def generate_cover(self, title: str, subtitle: str = "") -> str:
        """
        Generates a cover image with title and optional subtitle.
        """
        # Load emoji font if available
        emoji_font_path = self._find_emoji_font()
        
        bg_color, text_color, accent_color = self._get_color_scheme()
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), bg_color)
        draw = ImageDraw.Draw(image)
        
        try:
            # Title
            if self.font_path:
                title_font = ImageFont.truetype(self.font_path, TITLE_FONT_SIZE)
                subtitle_font = ImageFont.truetype(self.font_path, SUBTITLE_FONT_SIZE)
                footer_font = ImageFont.truetype(self.font_path, 40)
            else:
                logger.warning("Loading default font (no Chinese support)")
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                footer_font = ImageFont.load_default()

            # Emoji Fonts
            title_emoji_font = None
            subtitle_emoji_font = None
            if emoji_font_path:
                title_emoji_font = ImageFont.truetype(emoji_font_path, TITLE_FONT_SIZE)
                subtitle_emoji_font = ImageFont.truetype(emoji_font_path, SUBTITLE_FONT_SIZE)

            wrapped_title = self._wrap_text(title, title_font, MAX_TEXT_WIDTH, title_emoji_font)
            wrapped_subtitle = self._wrap_text(subtitle, subtitle_font, MAX_TEXT_WIDTH, subtitle_emoji_font) if subtitle else []
            
            # Footer
            footer_text = "贝壳分享"
            footer_bbox = footer_font.getbbox(footer_text)
            footer_width = footer_bbox[2] - footer_bbox[0]
            footer_height = footer_bbox[3] - footer_bbox[1]
            footer_x = (CANVAS_WIDTH - footer_width) / 2
            footer_y = CANVAS_HEIGHT - footer_height - 60  # 60px from bottom

            draw.text((footer_x, footer_y), footer_text, font=footer_font, fill=text_color)
            
            # Calculate total height
            title_height = 0
            for line in wrapped_title:
                # Approximate height using max height of font (simplified)
                # Or measure line
                line_bbox = title_font.getbbox(line) # This might be inaccurate for emoji-only lines
                h = line_bbox[3] - line_bbox[1]
                if h == 0: h = TITLE_FONT_SIZE # Fallback
                title_height += h + TITLE_LINE_SPACING
                
            subtitle_height = 0
            if wrapped_subtitle:
                for line in wrapped_subtitle:
                    line_bbox = subtitle_font.getbbox(line)
                    h = line_bbox[3] - line_bbox[1]
                    if h == 0: h = SUBTITLE_FONT_SIZE
                    subtitle_height += h + TITLE_LINE_SPACING
                subtitle_height += SUBTITLE_SPACING
                
            total_content_height = title_height + subtitle_height
            
            # Center vertically
            start_y = (CANVAS_HEIGHT - total_content_height) / 2
            
            current_y = start_y
            
            # Draw Title
            for line in wrapped_title:
                # Calculate line width for centering
                line_width = 0
                for char in line:
                    is_emoji = ord(char) > 0xFFFF
                    f = title_emoji_font if (is_emoji and title_emoji_font) else title_font
                    line_width += f.getlength(char)
                    
                line_bbox = title_font.getbbox(line) # Use main font for height reference
                line_height = line_bbox[3] - line_bbox[1]
                if line_height == 0: line_height = TITLE_FONT_SIZE

                x = (CANVAS_WIDTH - line_width) / 2
                self._draw_text_line(draw, (x, current_y), line, title_font, title_emoji_font, text_color)
                current_y += line_height + TITLE_LINE_SPACING
                
            current_y += SUBTITLE_SPACING
            
            # Draw Subtitle with Pill Background
            if wrapped_subtitle:
                subtitle_text_color = (0, 0, 0) if self._is_light(accent_color) else (255, 255, 255)
                
                for line in wrapped_subtitle:
                    # Calculate line width
                    line_width = 0
                    for char in line:
                        is_emoji = ord(char) > 0xFFFF
                        f = subtitle_emoji_font if (is_emoji and subtitle_emoji_font) else subtitle_font
                        line_width += f.getlength(char)
                        
                    line_bbox = subtitle_font.getbbox(line)
                    line_height = line_bbox[3] - line_bbox[1]
                    if line_height == 0: line_height = SUBTITLE_FONT_SIZE
                    
                    # Pill padding
                    pad_x = 30
                    pad_y = 10
                    
                    # Pill coordinates
                    rect_x1 = (CANVAS_WIDTH - line_width) / 2 - pad_x
                    rect_y1 = current_y - pad_y
                    rect_x2 = (CANVAS_WIDTH + line_width) / 2 + pad_x
                    rect_y2 = current_y + line_height + pad_y + 5 # Add a bit more for descenders
                    
                    # Draw rounded rectangle (Pill)
                    draw.rounded_rectangle((rect_x1, rect_y1, rect_x2, rect_y2), radius=20, fill=accent_color)
                    
                    # Draw text
                    x = (CANVAS_WIDTH - line_width) / 2
                    self._draw_text_line(draw, (x, current_y), line, subtitle_font, subtitle_emoji_font, subtitle_text_color)
                    
                    current_y += line_height + TITLE_LINE_SPACING + (pad_y * 2)

        except Exception as e:
            logger.error(f"Error drawing text: {e}")
            # Fallback for font errors
            draw.text((100, 100), title, fill=(0,0,0))
            
        filename = f"cover_{random.randint(1000, 9999)}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath, quality=90)
        logger.info(f"Cover image generated: {filepath}")
        
        return filepath

if __name__ == "__main__":
    # Test
    gen = CoverGenerator()
    path = gen.generate_cover("测试标题：这是一个非常长的标题用于测试换行功能是否正常工作", "副标题：测试副标题")
    print(f"Generated at: {path}")
