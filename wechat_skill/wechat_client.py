import requests
import json
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class WeChatClient:
    """
    Client for WeChat Official Account API.
    Handles authentication and content publishing (drafts).
    """
    
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    DEFAULT_TOKEN_EXPIRY = 7200
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token: Optional[str] = None
        self.expires_at: float = 0
        
    def get_access_token(self) -> str:
        """
        Retrieves access token using app_id and app_secret.
        If current token is valid, returns it. Otherwise fetches a new one.
        """
        if self.access_token and time.time() < self.expires_at:
            return self.access_token

        url = f"{self.BASE_URL}/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        try:
            response = requests.get(url)
            data = response.json()
            if "access_token" in data:
                self.access_token = data["access_token"]
                self.expires_at = time.time() + data.get("expires_in", self.DEFAULT_TOKEN_EXPIRY) - 60 # Refresh 60s early
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {data}")
                raise Exception(f"WeChat API Error: {data.get('errmsg', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error fetching access token: {e}")
            raise

    def upload_image(self, image_path: str) -> str:
        """
        Uploads an image to WeChat material library.
        Returns media_id.
        """
        if not self.access_token:
            self.get_access_token()
            
        url = f"{self.BASE_URL}/material/add_material?access_token={self.access_token}&type=image"
        
        try:
            with open(image_path, "rb") as f:
                files = {"media": (image_path.split("/")[-1], f, "image/jpeg")}
                response = requests.post(url, files=files)
                data = response.json()
                if "media_id" in data:
                    logger.info(f"Image uploaded successfully. Media ID: {data['media_id']}")
                    return data["media_id"]
                else:
                    logger.error(f"Failed to upload image: {data}")
                    raise Exception(f"WeChat API Error: {data.get('errmsg', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise

    def add_draft(self, articles: list) -> str:
        """
        Adds articles to draft box.
        articles: List of dicts matching WeChat article structure.
        Returns media_id of the draft.
        """
        if not self.access_token:
            self.get_access_token()
            
        url = f"{self.BASE_URL}/draft/add?access_token={self.access_token}"
        
        payload = {"articles": articles}
        
        try:
            # Ensure proper JSON encoding with ensure_ascii=False for Chinese characters
            response = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            data = response.json()
            if "media_id" in data:
                logger.info(f"Draft added successfully. Media ID: {data['media_id']}")
                return data["media_id"]
            else:
                logger.error(f"Failed to add draft: {data}")
                raise Exception(f"WeChat API Error: {data.get('errmsg', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error adding draft: {e}")
            raise

