"""浏览器管理模块"""

from typing import Optional
import os
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.cookies import CookieManager


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, headless: bool = True, bin_path: Optional[str] = None):
        if headless is False:
            allow = os.getenv("XHS_ALLOW_NON_HEADLESS", "").strip().lower()
            if allow not in {"1", "true", "yes", "y"}:
                raise RuntimeError("non-headless 模式已被禁用，请设置环境变量 XHS_ALLOW_NON_HEADLESS=1 后再使用")
        self.headless = headless
        self.bin_path = bin_path
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._cookie_manager = CookieManager()
    
    async def _ensure_browser(self) -> Browser:
        """确保浏览器已启动"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            
            # 使用 new headless 模式，在 macOS 上不会显示 Dock 图标
            launch_options = {
                "headless": self.headless,
            }
            # Chromium 新版 headless 模式参数
            if self.headless:
                launch_options["args"] = ["--headless=new"]
            if self.bin_path:
                launch_options["executable_path"] = self.bin_path
            
            self._browser = await self._playwright.chromium.launch(**launch_options)
            logger.debug(f"浏览器已启动, headless={self.headless}")
        
        return self._browser
    
    async def new_page(self) -> Page:
        """创建新页面，自动加载 cookies"""
        browser = await self._ensure_browser()
        
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 加载 cookies
        cookies = self._cookie_manager.load_cookies()
        if cookies:
            # 转换 cookies 格式以兼容 Playwright
            converted_cookies = []
            for cookie in cookies:
                c = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie.get("path", "/"),
                }
                # Playwright 需要 sameSite 为特定值
                same_site = cookie.get("sameSite", "Lax")
                if same_site in ["Strict", "Lax", "None"]:
                    c["sameSite"] = same_site
                # 处理 expires（Playwright 需要整数或 -1）
                expires = cookie.get("expires", -1)
                if expires and expires > 0:
                    c["expires"] = int(expires)
                # 其他属性
                if cookie.get("httpOnly"):
                    c["httpOnly"] = True
                if cookie.get("secure"):
                    c["secure"] = True
                converted_cookies.append(c)
            
            await context.add_cookies(converted_cookies)
            logger.debug(f"已加载 {len(converted_cookies)} 个 cookies")
        
        page = await context.new_page()
        return page
    
    async def save_cookies(self, page: Page) -> None:
        """保存页面的 cookies"""
        context = page.context
        cookies = await context.cookies()
        self._cookie_manager.save_cookies(cookies)
    
    def delete_cookies(self) -> None:
        """删除 cookies"""
        self._cookie_manager.delete_cookies()
    
    async def close(self) -> None:
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.debug("浏览器已关闭")
