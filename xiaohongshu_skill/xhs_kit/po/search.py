"""搜索模块"""

import asyncio
import json
from urllib.parse import urlencode
from typing import Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.models import Feed, FeedsListResponse, FilterOption


class SearchAction:
    """搜索操作"""
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def search(self, keyword: str, filters: Optional[FilterOption] = None) -> FeedsListResponse:
        """搜索小红书内容
        
        Args:
            keyword: 搜索关键词
            filters: 筛选选项（可选）
        """
        page = await self.browser.new_page()
        
        try:
            # 构建搜索 URL
            search_url = self._make_search_url(keyword)
            logger.debug(f"搜索 URL: {search_url}")
            
            await page.goto(search_url)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待页面数据加载
            await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=30000)
            
            # 如果有筛选条件，应用筛选
            if filters:
                await self._apply_filters(page, filters)
            
            # 从页面提取搜索结果
            feeds = await self._extract_feeds(page)
            
            logger.info(f"搜索 '{keyword}' 找到 {len(feeds)} 条结果")
            
            return FeedsListResponse(feeds=feeds, count=len(feeds))
        finally:
            await page.close()
    
    def _make_search_url(self, keyword: str) -> str:
        """构建搜索 URL"""
        params = {
            "keyword": keyword,
            "source": "web_explore_feed"
        }
        return f"https://www.xiaohongshu.com/search_result?{urlencode(params)}"
    
    async def _apply_filters(self, page: Page, filters: FilterOption) -> None:
        """应用筛选条件"""
        # 悬停在筛选按钮上
        filter_button = page.locator("div.filter")
        await filter_button.hover()
        
        # 等待筛选面板出现
        await page.wait_for_selector("div.filter-panel", timeout=5000)
        
        # 筛选选项映射
        filter_map = {
            "sort_by": (1, {"综合": 1, "最新": 2, "最多点赞": 3, "最多评论": 4, "最多收藏": 5}),
            "note_type": (2, {"不限": 1, "视频": 2, "图文": 3}),
            "publish_time": (3, {"不限": 1, "一天内": 2, "一周内": 3, "半年内": 4}),
            "search_scope": (4, {"不限": 1, "已看过": 2, "未看过": 3, "已关注": 4}),
            "location": (5, {"不限": 1, "同城": 2, "附近": 3}),
        }
        
        # 应用各个筛选条件
        for field, (filter_idx, options) in filter_map.items():
            value = getattr(filters, field, None)
            if value and value in options:
                tag_idx = options[value]
                selector = f"div.filter-panel div.filters:nth-child({filter_idx}) div.tags:nth-child({tag_idx})"
                await page.click(selector)
                await asyncio.sleep(0.3)
        
        # 等待页面更新
        await asyncio.sleep(1)
    
    async def _extract_feeds(self, page: Page) -> list[Feed]:
        """从页面提取搜索结果"""
        result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.search &&
                window.__INITIAL_STATE__.search.feeds) {
                const feeds = window.__INITIAL_STATE__.search.feeds;
                const feedsData = feeds.value !== undefined ? feeds.value : feeds._value;
                if (feedsData) {
                    return JSON.stringify(feedsData);
                }
            }
            return "";
        }""")
        
        if not result:
            logger.warning("未找到搜索结果")
            return []
        
        try:
            raw_feeds = json.loads(result)
            feeds = []
            for item in raw_feeds:
                try:
                    # 获取 note_card，可能在不同层级
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
                    logger.debug(f"解析 feed 失败: {e}, item={item}")
                    continue
            return feeds
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return []
