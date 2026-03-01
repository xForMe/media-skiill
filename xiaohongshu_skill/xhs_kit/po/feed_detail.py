"""笔记详情模块"""

import asyncio
import json
from typing import Optional, TYPE_CHECKING
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.interact import make_feed_detail_url

if TYPE_CHECKING:
    from xhs_kit.po.models import CommentLoadConfig


class FeedDetailAction:
    """获取笔记详情"""
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def get_feed_detail(self, feed_id: str, xsec_token: str, load_comments: bool = False) -> dict:
        """获取笔记详情
        
        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            load_comments: 是否加载评论
        """
        page = await self.browser.new_page()
        url = make_feed_detail_url(feed_id, xsec_token)
        
        try:
            logger.debug(f"打开笔记详情页: {url}")
            await page.goto(url)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待数据加载
            await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=30000)
            # 等待 noteDetailMap 里出现目标 feed_id（避免只有 undefined 占位数据）
            try:
                await page.wait_for_function(
                    "(fid) => !!(window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note && window.__INITIAL_STATE__.note.noteDetailMap && window.__INITIAL_STATE__.note.noteDetailMap[fid] && window.__INITIAL_STATE__.note.noteDetailMap[fid].note)",
                    arg=feed_id,
                    timeout=30000,
                )
            except Exception:
                logger.debug("等待 noteDetailMap[feed_id] 超时，继续尝试解析")
            
            # 提取笔记详情
            detail = await self._extract_detail(page, feed_id)
            
            # 加载评论
            if load_comments:
                comments = await self._extract_comments(page)
                detail["comments"] = comments
            
            return detail
        finally:
            await page.close()
    
    async def _extract_detail(self, page: Page, feed_id: str) -> dict:
        """提取笔记详情"""
        # 重试获取 noteDetailMap，直到其包含目标 feed_id 或超时
        result = ""
        for _ in range(10):
            result = await page.evaluate("""(fid) => {
                if (window.__INITIAL_STATE__ &&
                    window.__INITIAL_STATE__.note &&
                    window.__INITIAL_STATE__.note.noteDetailMap) {
                    const m = window.__INITIAL_STATE__.note.noteDetailMap;
                    // 有些情况下会先出现 {undefined: {...}} 的占位数据
                    if (m && m[fid]) {
                        return JSON.stringify(m);
                    }
                    return JSON.stringify(m);
                }
                return "";
            }""", feed_id)
            if result:
                try:
                    note_detail_map = json.loads(result)
                    if feed_id in note_detail_map and (note_detail_map.get(feed_id) or {}).get("note"):
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)
        
        if not result:
            return {"feed_id": feed_id, "error": "未找到笔记详情"}
        
        try:
            note_detail_map = json.loads(result)
            if feed_id not in note_detail_map or not (note_detail_map.get(feed_id) or {}).get("note"):
                return {
                    "feed_id": feed_id,
                    "error": "未找到笔记详情（可能 xsec_token 失效、未登录或触发风控）",
                }
            detail = note_detail_map.get(feed_id, {})
            note = detail.get("note", {})
            
            # 提取关键信息
            return {
                "feed_id": feed_id,
                "title": note.get("title", ""),
                "desc": note.get("desc", ""),
                "type": note.get("type", ""),
                "time": note.get("time", ""),
                "user": {
                    "user_id": note.get("user", {}).get("userId", ""),
                    "nickname": note.get("user", {}).get("nickname", ""),
                    "avatar": note.get("user", {}).get("avatar", ""),
                },
                "interact_info": {
                    "liked": note.get("interactInfo", {}).get("liked", False),
                    "liked_count": note.get("interactInfo", {}).get("likedCount", "0"),
                    "collected": note.get("interactInfo", {}).get("collected", False),
                    "collected_count": note.get("interactInfo", {}).get("collectedCount", "0"),
                    "comment_count": note.get("interactInfo", {}).get("commentCount", "0"),
                    "share_count": note.get("interactInfo", {}).get("shareCount", "0"),
                },
                "images": [img.get("urlDefault", "") for img in note.get("imageList", [])],
                "tags": [tag.get("name", "") for tag in note.get("tagList", [])],
            }
        except Exception as e:
            logger.error(f"解析笔记详情失败: {e}")
            return {"feed_id": feed_id, "error": str(e)}
    
    async def get_feed_detail_with_config(
        self, 
        feed_id: str, 
        xsec_token: str, 
        config: "CommentLoadConfig"
    ) -> dict:
        """获取笔记详情（带评论加载配置）
        
        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            config: 评论加载配置
        """
        page = await self.browser.new_page()
        url = make_feed_detail_url(feed_id, xsec_token)
        
        try:
            logger.debug(f"打开笔记详情页: {url}")
            await page.goto(url)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待数据加载
            await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=30000)
            
            # 提取笔记详情
            detail = await self._extract_detail(page, feed_id)
            
            # 根据配置加载评论
            if config.load_all_comments:
                comments = await self._load_all_comments(page, config)
                detail["comments"] = comments
                detail["comment_config"] = {
                    "loaded_count": len(comments),
                    "limit": config.limit,
                    "click_more_replies": config.click_more_replies,
                    "scroll_speed": config.scroll_speed
                }
            else:
                comments = await self._extract_comments(page)
                detail["comments"] = comments
            
            return detail
        finally:
            await page.close()
    
    async def _load_all_comments(self, page: Page, config: "CommentLoadConfig") -> list:
        """加载所有评论（滚动加载）
        
        Args:
            page: 页面对象
            config: 评论加载配置
        """
        comments = []
        scroll_count = 0
        max_scrolls = config.limit // 10 + 1  # 每次滚动大约加载10条
        
        # 根据 scroll_speed 设置等待时间
        wait_time = {
            "slow": 2.0,
            "normal": 1.0,
            "fast": 0.5
        }.get(config.scroll_speed, 1.0)
        
        logger.info(f"开始加载评论，目标数量: {config.limit}, 滚动速度: {config.scroll_speed}")
        
        while scroll_count < max_scrolls:
            # 提取当前评论
            current_comments = await self._extract_comments(page)
            
            if len(current_comments) >= config.limit:
                logger.info(f"已达到目标评论数量: {len(current_comments)}")
                break
            
            # 滚动页面
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(wait_time)
            scroll_count += 1
            
            # 检查是否还有更多评论
            has_more = await page.evaluate("""() => {
                const loadMore = document.querySelector('.load-more, .more-comments');
                return loadMore !== null;
            }""")
            
            if not has_more and len(current_comments) == len(comments):
                logger.info(f"没有更多评论了，当前数量: {len(current_comments)}")
                break
            
            comments = current_comments
        
        # 如果需要展开二级回复
        if config.click_more_replies:
            await self._expand_replies(page, config.reply_limit)
        
        return comments[:config.limit]
    
    async def _expand_replies(self, page: Page, reply_limit: int) -> None:
        """展开二级回复
        
        Args:
            page: 页面对象
            reply_limit: 跳过回复数超过此值的评论
        """
        logger.info(f"开始展开二级回复，跳过回复数超过 {reply_limit} 的评论")
        
        # 查找所有"展开回复"按钮
        expand_buttons = await page.locator(".expand-replies, button:has-text('展开')").all()
        
        for btn in expand_buttons[:10]:  # 限制最多展开10个
            try:
                # 检查回复数量
                reply_count_text = await btn.text_content()
                if reply_count_text and any(char.isdigit() for char in reply_count_text):
                    count = int(''.join(filter(str.isdigit, reply_count_text)))
                    if count > reply_limit:
                        logger.debug(f"跳过回复数过多的评论: {count} > {reply_limit}")
                        continue
                
                await btn.click()
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"展开回复失败: {e}")
    
    async def _extract_comments(self, page: Page) -> list:
        """提取评论列表"""
        result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.note &&
                window.__INITIAL_STATE__.note.noteDetailMap) {
                const map = window.__INITIAL_STATE__.note.noteDetailMap;
                const keys = Object.keys(map);
                if (keys.length > 0) {
                    const detail = map[keys[0]];
                    if (detail && detail.comments) {
                        return JSON.stringify(detail.comments);
                    }
                }
            }
            return "[]";
        }""")
        
        try:
            comments_data = json.loads(result)
            comments = []
            for c in comments_data:
                comments.append({
                    "id": c.get("id", ""),
                    "content": c.get("content", ""),
                    "user_id": c.get("userInfo", {}).get("userId", ""),
                    "nickname": c.get("userInfo", {}).get("nickname", ""),
                    "like_count": c.get("likeCount", "0"),
                    "create_time": c.get("createTime", ""),
                })
            return comments
        except Exception as e:
            logger.debug(f"解析评论失败: {e}")
            return []
