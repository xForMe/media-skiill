"""用户主页模块"""

import asyncio
import json
from typing import Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager


def make_user_profile_url(user_id: str, xsec_token: str) -> str:
    """构建用户主页 URL"""
    return f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={xsec_token}&xsec_source=pc_note"


class UserProfileAction:
    """获取用户主页"""
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def get_user_profile(self, user_id: str, xsec_token: str) -> dict:
        """获取用户主页信息
        
        Args:
            user_id: 用户 ID
            xsec_token: 访问令牌
        """
        page = await self.browser.new_page()
        url = make_user_profile_url(user_id, xsec_token)
        
        try:
            logger.debug(f"打开用户主页: {url}")
            await page.goto(url)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待数据加载
            await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=30000)
            
            return await self._extract_profile(page)
        finally:
            await page.close()
    
    async def _extract_profile(self, page: Page) -> dict:
        """提取用户信息"""
        # 获取用户基本信息
        user_data_result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.user &&
                window.__INITIAL_STATE__.user.userPageData) {
                const userPageData = window.__INITIAL_STATE__.user.userPageData;
                const data = userPageData.value !== undefined ? userPageData.value : userPageData._value;
                if (data) {
                    return JSON.stringify(data);
                }
            }
            return "";
        }""")
        
        # 获取用户笔记
        notes_result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.user &&
                window.__INITIAL_STATE__.user.notes) {
                const notes = window.__INITIAL_STATE__.user.notes;
                const data = notes.value !== undefined ? notes.value : notes._value;
                if (data) {
                    return JSON.stringify(data);
                }
            }
            return "";
        }""")
        
        result = {"user": {}, "interactions": [], "notes": []}
        
        # 解析用户信息
        if user_data_result:
            try:
                user_page_data = json.loads(user_data_result)
                basic_info = user_page_data.get("basicInfo", {})
                result["user"] = {
                    "user_id": basic_info.get("userId", ""),
                    "nickname": basic_info.get("nickname", ""),
                    "avatar": basic_info.get("imageb", ""),
                    "desc": basic_info.get("desc", ""),
                    "gender": basic_info.get("gender", 0),
                    "ip_location": basic_info.get("ipLocation", ""),
                }
                result["interactions"] = user_page_data.get("interactions", [])
            except Exception as e:
                logger.debug(f"解析用户信息失败: {e}")
        
        # 解析笔记列表
        if notes_result:
            try:
                notes_feeds = json.loads(notes_result)
                # 展平双重数组
                for feeds in notes_feeds:
                    if isinstance(feeds, list):
                        for feed in feeds:
                            result["notes"].append({
                                "id": feed.get("id", ""),
                                "xsec_token": feed.get("xsec_token") or feed.get("xsecToken", ""),
                                "title": feed.get("note_card", {}).get("display_title") or feed.get("noteCard", {}).get("displayTitle", ""),
                                "type": feed.get("note_card", {}).get("type") or feed.get("noteCard", {}).get("type", ""),
                                "liked_count": feed.get("note_card", {}).get("interact_info", {}).get("liked_count") or "0",
                            })
            except Exception as e:
                logger.debug(f"解析笔记列表失败: {e}")
        
        return result
