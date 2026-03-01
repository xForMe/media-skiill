"""互动模块：点赞、收藏、评论"""

import asyncio
import json
from typing import Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager


# 选择器常量
SELECTOR_LIKE_BUTTON = ".like-wrapper .like-lottie, .like-wrapper .like-icon"
SELECTOR_COLLECT_BUTTON = ".collect-wrapper .collect-icon"


def make_feed_detail_url(feed_id: str, xsec_token: str) -> str:
    """构建笔记详情页 URL"""
    return f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}&xsec_source=pc_feed"


class InteractAction:
    """互动操作基类"""
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def _prepare_page(self, feed_id: str, xsec_token: str) -> Page:
        """准备页面，导航到笔记详情"""
        page = await self.browser.new_page()
        url = make_feed_detail_url(feed_id, xsec_token)
        logger.debug(f"打开笔记详情页: {url}")

        await page.goto(url)
        await page.wait_for_load_state("load")
        await asyncio.sleep(2)

        # 等待互动容器加载（可选，不阻塞）
        try:
            await page.wait_for_selector(".like-lottie, .like-icon", timeout=5000)
            logger.debug("互动容器已加载")
        except Exception:
            logger.debug("等待互动容器超时，继续执行")

        return page
    
    async def _get_interact_state(self, page: Page, feed_id: str) -> tuple[bool, bool]:
        """获取点赞/收藏状态
        
        Returns:
            (liked, collected) 元组
        """
        result = await page.evaluate("""() => {
            if (window.__INITIAL_STATE__ &&
                window.__INITIAL_STATE__.note &&
                window.__INITIAL_STATE__.note.noteDetailMap) {
                return JSON.stringify(window.__INITIAL_STATE__.note.noteDetailMap);
            }
            return "";
        }""")
        
        if not result:
            return False, False
        
        try:
            note_detail_map = json.loads(result)
            detail = note_detail_map.get(feed_id, {})
            note = detail.get("note", {})
            interact_info = note.get("interactInfo", {})
            return interact_info.get("liked", False), interact_info.get("collected", False)
        except Exception as e:
            logger.debug(f"解析互动状态失败: {e}")
            return False, False


class LikeAction(InteractAction):
    """点赞操作"""
    
    async def like(self, feed_id: str, xsec_token: str) -> dict:
        """点赞笔记"""
        return await self._perform(feed_id, xsec_token, target_liked=True)
    
    async def unlike(self, feed_id: str, xsec_token: str) -> dict:
        """取消点赞"""
        return await self._perform(feed_id, xsec_token, target_liked=False)
    
    async def _perform(self, feed_id: str, xsec_token: str, target_liked: bool) -> dict:
        action_name = "点赞" if target_liked else "取消点赞"
        page = await self._prepare_page(feed_id, xsec_token)
        
        try:
            # 获取当前状态
            liked, _ = await self._get_interact_state(page, feed_id)
            
            # 检查是否需要操作
            if target_liked and liked:
                logger.info(f"笔记 {feed_id} 已点赞，跳过")
                return {"feed_id": feed_id, "success": True, "message": "已点赞"}
            if not target_liked and not liked:
                logger.info(f"笔记 {feed_id} 未点赞，跳过")
                return {"feed_id": feed_id, "success": True, "message": "未点赞"}
            
            # 点击点赞按钮
            like_btn = page.locator(SELECTOR_LIKE_BUTTON).first
            await like_btn.wait_for(state="visible", timeout=15000)
            await like_btn.click(timeout=15000)
            await asyncio.sleep(2)

            # 验证操作结果
            liked_after, _ = await self._get_interact_state(page, feed_id)
            if target_liked and liked_after:
                logger.info(f"笔记 {feed_id} {action_name}成功")
                return {"feed_id": feed_id, "success": True, "message": f"{action_name}成功"}
            elif not target_liked and not liked_after:
                logger.info(f"笔记 {feed_id} {action_name}成功")
                return {"feed_id": feed_id, "success": True, "message": f"{action_name}成功"}
            else:
                logger.warning(f"笔记 {feed_id} {action_name}可能失败，状态未改变")
                return {"feed_id": feed_id, "success": False, "message": f"{action_name}可能失败，状态未改变"}
        finally:
            await page.close()


class FavoriteAction(InteractAction):
    """收藏操作"""
    
    async def favorite(self, feed_id: str, xsec_token: str) -> dict:
        """收藏笔记"""
        return await self._perform(feed_id, xsec_token, target_collected=True)
    
    async def unfavorite(self, feed_id: str, xsec_token: str) -> dict:
        """取消收藏"""
        return await self._perform(feed_id, xsec_token, target_collected=False)
    
    async def _perform(self, feed_id: str, xsec_token: str, target_collected: bool) -> dict:
        action_name = "收藏" if target_collected else "取消收藏"
        page = await self._prepare_page(feed_id, xsec_token)
        
        try:
            # 获取当前状态
            _, collected = await self._get_interact_state(page, feed_id)
            
            # 检查是否需要操作
            if target_collected and collected:
                logger.info(f"笔记 {feed_id} 已收藏，跳过")
                return {"feed_id": feed_id, "success": True, "message": "已收藏"}
            if not target_collected and not collected:
                logger.info(f"笔记 {feed_id} 未收藏，跳过")
                return {"feed_id": feed_id, "success": True, "message": "未收藏"}
            
            # 点击收藏按钮
            collect_btn = page.locator(SELECTOR_COLLECT_BUTTON).first
            await collect_btn.wait_for(state="visible", timeout=15000)
            await collect_btn.click(timeout=15000)
            await asyncio.sleep(2)

            # 验证操作结果
            _, collected_after = await self._get_interact_state(page, feed_id)
            if target_collected and collected_after:
                logger.info(f"笔记 {feed_id} {action_name}成功")
                return {"feed_id": feed_id, "success": True, "message": f"{action_name}成功"}
            elif not target_collected and not collected_after:
                logger.info(f"笔记 {feed_id} {action_name}成功")
                return {"feed_id": feed_id, "success": True, "message": f"{action_name}成功"}
            else:
                logger.warning(f"笔记 {feed_id} {action_name}可能失败，状态未改变")
                return {"feed_id": feed_id, "success": False, "message": f"{action_name}可能失败，状态未改变"}
        finally:
            await page.close()


class CommentAction(InteractAction):
    """评论操作"""
    
    async def post_comment(self, feed_id: str, xsec_token: str, content: str) -> dict:
        """发表评论"""
        page = await self._prepare_page(feed_id, xsec_token)

        try:
            # 先点击评论按钮展开输入框
            comment_btn = page.locator(".interact-container .right .comment-wrapper").first
            if await comment_btn.count() > 0:
                await comment_btn.click(timeout=10000)
                await asyncio.sleep(0.5)

            # 点击评论输入框
            input_box = page.locator("div.input-box div.content-edit span").first
            await input_box.wait_for(state="visible", timeout=10000)
            await input_box.click(force=True, timeout=10000)
            await asyncio.sleep(0.5)

            # 输入评论内容
            content_input = page.locator("div.input-box div.content-edit p.content-input").first
            await content_input.fill(content)
            await asyncio.sleep(0.5)

            # 点击提交按钮
            submit_btn = page.locator("div.bottom button.submit").first
            await submit_btn.click(force=True, timeout=10000)
            await asyncio.sleep(1)

            logger.info(f"评论发表成功: {feed_id}")
            return {"feed_id": feed_id, "success": True, "message": "评论发表成功"}
        except Exception as e:
            logger.error(f"评论发表失败: {e}")
            return {"feed_id": feed_id, "success": False, "message": str(e)}
        finally:
            await page.close()
    
    async def reply_comment(
        self, 
        feed_id: str, 
        xsec_token: str, 
        content: str,
        comment_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """回复评论
        
        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            content: 回复内容
            comment_id: 目标评论 ID（可选）
            user_id: 目标用户 ID（可选）
        """
        if not comment_id and not user_id:
            return {"feed_id": feed_id, "success": False, "message": "缺少 comment_id 或 user_id"}
        
        page = await self._prepare_page(feed_id, xsec_token)
        
        try:
            # 等待评论列表加载
            await asyncio.sleep(2)
            
            # 查找目标评论的回复按钮
            reply_button = None
            
            if comment_id:
                # 通过 comment_id 查找
                reply_button = page.locator(f"div[data-id='{comment_id}'] .reply-btn").first
            elif user_id:
                # 通过 user_id 查找
                reply_button = page.locator(f"div[data-user-id='{user_id}'] .reply-btn").first
            
            # 如果上述方法失败，尝试通过文本查找
            if not await reply_button.count():
                reply_buttons = page.locator(".reply-btn, button:has-text('回复')")
                if await reply_buttons.count() > 0:
                    reply_button = reply_buttons.first
            
            if not await reply_button.count():
                return {"feed_id": feed_id, "success": False, "message": "未找到回复按钮"}
            
            # 点击回复按钮
            await reply_button.click()
            await asyncio.sleep(0.5)
            
            # 输入回复内容
            content_input = page.locator("div.input-box div.content-edit p.content-input")
            await content_input.fill(content)
            await asyncio.sleep(1)
            
            # 点击提交按钮
            submit_btn = page.locator("div.bottom button.submit")
            await submit_btn.click()
            await asyncio.sleep(2)
            
            logger.info(f"回复评论成功: {feed_id}, comment_id={comment_id}, user_id={user_id}")
            return {
                "feed_id": feed_id, 
                "success": True, 
                "message": "回复评论成功",
                "target_comment_id": comment_id,
                "target_user_id": user_id
            }
        except Exception as e:
            logger.error(f"回复评论失败: {e}")
            return {"feed_id": feed_id, "success": False, "message": str(e)}
        finally:
            await page.close()
