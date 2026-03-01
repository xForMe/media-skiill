"""登录模块"""

import asyncio
from typing import Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.models import LoginStatus, LoginQrcodeResponse


class LoginAction:
    """登录操作"""
    
    XHS_URL = "https://www.xiaohongshu.com/explore"
    LOGIN_SUCCESS_SELECTOR = ".main-container .user .link-wrapper .channel"
    QRCODE_SELECTOR = ".login-container .qrcode-img"
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    def has_cookies(self) -> bool:
        """快速检查是否有 cookies 文件（不打开浏览器）"""
        from xhs_kit.po.cookies import get_cookies_file_path
        return get_cookies_file_path().exists()
    
    async def check_login_status(self, quick: bool = False) -> LoginStatus:
        """检查登录状态
        
        Args:
            quick: 如果为 True，只检查 cookies 文件是否存在，不打开浏览器验证
        """
        if quick:
            # 快速检查：只看 cookies 文件是否存在
            return LoginStatus(is_logged_in=self.has_cookies())
        
        page = await self.browser.new_page()
        try:
            await page.goto(self.XHS_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(3)
            
            # 检查登录成功元素（多次尝试）
            for _ in range(5):
                count = await page.locator(self.LOGIN_SUCCESS_SELECTOR).count()
                if count > 0:
                    return LoginStatus(is_logged_in=True)
                await asyncio.sleep(1)
            
            return LoginStatus(is_logged_in=False)
        finally:
            await page.close()
    
    async def get_login_qrcode(self) -> LoginQrcodeResponse:
        """获取登录二维码
        
        返回二维码图片的 base64 数据，并在后台等待扫码登录
        """
        page = await self.browser.new_page()
        
        await page.goto(self.XHS_URL)
        await page.wait_for_load_state("load")
        await asyncio.sleep(2)
        
        # 检查是否已登录
        if await page.locator(self.LOGIN_SUCCESS_SELECTOR).count() > 0:
            await page.close()
            return LoginQrcodeResponse(
                timeout="0s",
                is_logged_in=True,
                img=None
            )
        
        # 获取二维码图片
        qrcode_elem = page.locator(self.QRCODE_SELECTOR)
        img_src = await qrcode_elem.get_attribute("src")
        
        if not img_src:
            await page.close()
            raise Exception("无法获取二维码图片")
        
        # 启动后台任务等待登录
        timeout_seconds = 240
        asyncio.create_task(self._wait_for_login(page, timeout_seconds))
        
        return LoginQrcodeResponse(
            timeout=f"{timeout_seconds}s",
            is_logged_in=False,
            img=img_src
        )
    
    async def _wait_for_login(self, page: Page, timeout: int) -> bool:
        """等待扫码登录完成"""
        try:
            # 轮询检测登录成功
            for _ in range(timeout * 2):  # 每 0.5 秒检查一次
                await asyncio.sleep(0.5)
                if await page.locator(self.LOGIN_SUCCESS_SELECTOR).count() > 0:
                    logger.info("登录成功")
                    await self.browser.save_cookies(page)
                    await page.close()
                    return True
            
            logger.warning("登录超时")
            await page.close()
            return False
        except Exception as e:
            logger.error(f"等待登录时出错: {e}")
            try:
                await page.close()
            except:
                pass
            return False
    
    async def login_interactive(self) -> bool:
        """交互式登录（非 headless 模式下使用）
        
        打开浏览器，等待用户扫码登录
        返回 True 表示已登录（包括之前已登录和本次登录成功）
        """
        logger.info("login_interactive 被调用，准备打开浏览器")
        page = await self.browser.new_page()
        logger.info("login_interactive: 浏览器页面已创建")
        
        try:
            await page.goto(self.XHS_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 检查是否已登录
            if await page.locator(self.LOGIN_SUCCESS_SELECTOR).count() > 0:
                logger.info("已经登录，无需重复登录")
                return True
            
            logger.info("请扫描二维码登录...")
            
            # 等待登录成功，最多 4 分钟
            try:
                await page.wait_for_selector(
                    self.LOGIN_SUCCESS_SELECTOR,
                    timeout=240000
                )
                logger.info("登录成功")
                await self.browser.save_cookies(page)
                return True
            except Exception:
                logger.warning("登录超时")
                return False
        finally:
            await page.close()
