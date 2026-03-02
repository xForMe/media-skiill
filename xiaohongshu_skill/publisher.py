import sys
import os
import asyncio
import logging
import base64
from typing import Optional, List
from pathlib import Path

# Add current directory to sys.path so that xhs_kit can be imported correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from xhs_kit.po.client import XhsClient
    from xhs_kit.po.models import PublishResponse, LoginStatus
except ImportError:
    # This might happen if dependencies are missing or path is wrong
    logging.error("Failed to import xhs_kit. Please ensure dependencies are installed and sys.path is correct.")
    # We don't raise here to allow the module to be imported even if xhs_kit fails, 
    # but methods will fail at runtime.
    pass

from .models import XiaohongshuNote

logger = logging.getLogger(__name__)

class XiaohongshuPublisher:
    """
    Publishes notes to Xiaohongshu via local Playwright automation (xhs-kit).
    """
    
    def __init__(self, headless: bool = True, mock: bool = False):
        self.headless = headless
        self.mock = mock
        self.client: Optional[XhsClient] = None
        
        # Ensure non-headless mode is allowed if requested
        if not self.headless:
            os.environ["XHS_ALLOW_NON_HEADLESS"] = "1"

    async def _ensure_client(self):
        if not self.client:
            # Re-import here to ensure it works if sys.path was just fixed
            from xhs_kit.po.client import XhsClient
            self.client = XhsClient(headless=self.headless)

    async def check_login(self) -> bool:
        """Check if logged in, return True if logged in."""
        await self._ensure_client()
        if not self.client:
            return False
            
        # First try quick check (cookies file)
        status = await self.client.check_login_status(quick=True)
        if status.is_logged_in:
            return True
        
        # If not quick check, try full check (opens browser)
        # Note: This might be slow
        return False

    async def _handle_qr_code(self, qr_res) -> bool:
        """Handle QR code saving and waiting for login."""
        if not qr_res.img:
            return False

        try:
            img_data = base64.b64decode(qr_res.img.split(",")[1])
            qr_path = os.path.join(os.getcwd(), "login_qrcode.png")
            with open(qr_path, "wb") as f:
                f.write(img_data)
            logger.info(f"Please scan the QR code saved to '{qr_path}' to login.")
            print(f"\n[LOGIN REQUIRED] QR Code saved to {qr_path}. Please scan it with Xiaohongshu app.\n")
        except Exception as e:
            logger.error(f"Failed to save QR code image: {e}")
            return False
        
        # Wait for login
        logger.info("Waiting for login (timeout: 120s)...")
        for _ in range(24): # Wait up to 2 minutes (5s * 24)
            await asyncio.sleep(5)
            if await self.client.check_login_status(quick=True):
                logger.info("Login successful!")
                return True
            
        logger.error("Login timeout.")
        return False

    async def login(self) -> bool:
        """Perform login flow (QR code)."""
        await self._ensure_client()
        if not self.client:
            return False

        if await self.check_login():
            logger.info("Already logged in.")
            return True

        logger.info("Starting login flow...")
        try:
            # Use the wrapper method on client instead of accessing login_action directly
            qr_res = await self.client.get_login_qrcode()
        except Exception as e:
            logger.error(f"Failed to get login QR code: {e}")
            return False

        if qr_res.is_logged_in:
            logger.info("Login successful (detected existing session).")
            return True
        
        return await self._handle_qr_code(qr_res)

    def _validate_images(self, images: List[str]) -> List[str]:
        """Filter out non-existent images."""
        return [img for img in images if os.path.exists(img)]

    def _prepare_images(self, note: XiaohongshuNote) -> List[str]:
        """Prepare and validate images for publication."""
        images = []
        if note.images:
            images.extend(note.images)
        
        if not images and note.cover_image_path:
            images.append(note.cover_image_path)
        
        valid_images = self._validate_images(images)
        if not valid_images:
            logger.error(f"No valid images found for note: {note.title}")
            return []
            
        return valid_images

    async def _ensure_logged_in(self) -> bool:
        """Ensure the client is logged in."""
        if not await self.check_login():
            logger.warning("Not logged in. Attempting login flow...")
            if not await self.login():
                logger.error("Failed to login. Cannot publish.")
                return False
        return True

    def _truncate_title(self, title: str) -> str:
        """Truncate title to 20 characters if needed."""
        if len(title) > 20:
            truncated = title[:20]
            logger.warning(f"Title truncated to 20 characters: {truncated}")
            return truncated
        return title

    async def _perform_publish(self, note: XiaohongshuNote, valid_images: List[str]) -> bool:
        """Execute the publish command via client."""
        final_title = self._truncate_title(note.title)
            
        # Use client.publish wrapper which handles initialization and PublishImageContent creation
        response = await self.client.publish(
            title=final_title,
            content=note.content,
            images=valid_images,
            tags=note.tags
        )
        
        if response.status == "发布完成":
            logger.info("Successfully published to Xiaohongshu.")
            return True
        else:
            logger.error(f"Failed to publish: {response.status}")
            return False

    async def _publish_logic(self, note: XiaohongshuNote) -> bool:
        """Core publishing logic."""
        await self._ensure_client()
        if not self.client:
            return False
        
        if not await self._ensure_logged_in():
            return False

        valid_images = self._prepare_images(note)
        if not valid_images:
            return False

        logger.info(f"Publishing note: {note.title}")
        
        return await self._perform_publish(note, valid_images)

    async def _publish_async(self, note: XiaohongshuNote) -> bool:
        if self.mock:
            logger.info(f"[MOCK] Would publish note: {note.title}")
            return True

        try:
            return await self._publish_logic(note)
        except Exception as e:
            logger.error(f"Error during publishing: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.client and self.client.browser:
                try:
                    await self.client.browser.close()
                except:
                    pass
                self.client = None

    def publish(self, note: XiaohongshuNote) -> bool:
        """
        Synchronous wrapper for publishing.
        """
        try:
            return asyncio.run(self._publish_async(note))
        except Exception as e:
            logger.error(f"Async execution failed: {e}")
            return False
