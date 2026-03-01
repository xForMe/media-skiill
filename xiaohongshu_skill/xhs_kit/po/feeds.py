"""首页推荐列表模块"""

import asyncio
import json
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.models import Feed, FeedsListResponse


class FeedsListAction:
    """获取首页推荐列表"""
    
    XHS_HOME_URL = "https://www.xiaohongshu.com"
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def get_feeds_list(self) -> FeedsListResponse:
        """获取首页推荐列表"""
        page = await self.browser.new_page()
        
        try:
            await page.goto(self.XHS_HOME_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待数据加载
            await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=30000)
            
            feeds = await self._extract_feeds(page)
            logger.info(f"获取到 {len(feeds)} 条首页推荐")
            
            return FeedsListResponse(feeds=feeds, count=len(feeds))
        finally:
            await page.close()
    
    async def _extract_feeds(self, page: Page) -> list[Feed]:
        """提取首页推荐列表"""
        result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.feed &&
                window.__INITIAL_STATE__.feed.feeds) {
                const feeds = window.__INITIAL_STATE__.feed.feeds;
                const feedsData = feeds.value !== undefined ? feeds.value : feeds._value;
                if (feedsData) {
                    return JSON.stringify(feedsData);
                }
            }
            return "";
        }""")
        
        if not result:
            logger.warning("未找到首页推荐数据")
            return []
        
        try:
            raw_feeds = json.loads(result)
            feeds = []
            for item in raw_feeds:
                try:
                    note_card = item.get("note_card") or item.get("noteCard") or {}
                    user = note_card.get("user") or {}
                    interact_info = note_card.get("interact_info") or note_card.get("interactInfo") or {}
                    cover = note_card.get("cover") or {}
                    
                    feed = Feed(
                        id=item.get("id", ""),
                        model_type=item.get("model_type") or item.get("modelType") or "",
                        xsec_token=item.get("xsec_token") or item.get("xsecToken") or "",
                        display_title=note_card.get("display_title") or note_card.get("displayTitle") or "",
                        note_type=note_card.get("type") or "",
                        user_id=user.get("user_id") or user.get("userId") or "",
                        nickname=user.get("nickname") or user.get("nick_name") or "",
                        liked_count=str(interact_info.get("liked_count") or interact_info.get("likedCount") or "0"),
                        cover_url=cover.get("url_default") or cover.get("urlDefault") or "",
                    )
                    feeds.append(feed)
                except Exception as e:
                    logger.debug(f"解析 feed 失败: {e}")
                    continue
            return feeds
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return []
