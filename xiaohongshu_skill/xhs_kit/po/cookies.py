"""Cookie 管理模块"""

import json
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_cookies_file_path() -> Path:
    """获取 cookies 文件路径
    
    优先级:
    1. 环境变量 COOKIES_PATH
    2. 当前目录 cookies.json
    """
    env_path = os.getenv("COOKIES_PATH")
    if env_path:
        return Path(env_path)
    return Path("cookies.json")


class CookieManager:
    """Cookie 管理器"""
    
    def __init__(self, path: Optional[Path] = None):
        self.path = path or get_cookies_file_path()
    
    def load_cookies(self) -> Optional[list[dict]]:
        """加载 cookies"""
        if not self.path.exists():
            logger.debug(f"Cookies 文件不存在: {self.path}")
            return None
        
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            logger.debug(f"成功加载 cookies: {self.path}")
            return cookies
        except Exception as e:
            logger.warning(f"加载 cookies 失败: {e}")
            return None
    
    def save_cookies(self, cookies: list[dict]) -> None:
        """保存 cookies"""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies 已保存: {self.path}")
        except Exception as e:
            logger.error(f"保存 cookies 失败: {e}")
            raise
    
    def delete_cookies(self) -> None:
        """删除 cookies 文件"""
        if self.path.exists():
            self.path.unlink()
            logger.info(f"Cookies 已删除: {self.path}")
        else:
            logger.debug(f"Cookies 文件不存在，无需删除: {self.path}")
