"""发布模块"""

import asyncio
import os
from typing import Optional
from datetime import datetime, timedelta
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.models import PublishImageContent, PublishVideoContent, PublishResponse


class PublishAction:
    """发布操作"""
    
    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def publish_image(self, content: PublishImageContent) -> PublishResponse:
        """发布图文内容"""
        # 验证标题长度
        if self._calc_title_length(content.title) > 20:
            raise ValueError("标题长度超过限制（最多20个字）")
        
        # 验证图片文件存在
        valid_images = []
        for img_path in content.images:
            if os.path.exists(img_path):
                valid_images.append(img_path)
            else:
                logger.warning(f"图片文件不存在: {img_path}")
        
        if not valid_images:
            raise ValueError("没有有效的图片文件")
        
        # 验证定时发布时间
        if content.schedule_at:
            self._validate_schedule_time(content.schedule_at)
        
        page = await self.browser.new_page()
        
        try:
            # 导航到发布页面
            await page.goto(self.PUBLISH_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 等待 DOM 稳定
            await asyncio.sleep(1)
            
            # 点击"上传图文" Tab
            await self._click_publish_tab(page, "上传图文")
            await asyncio.sleep(1)
            
            # 上传图片
            await self._upload_images(page, valid_images)
            
            # 填写标题和内容
            await self._submit_publish(
                page, 
                content.title, 
                content.content, 
                content.tags,
                content.schedule_at
            )
            
            logger.info(f"发布成功: {content.title}")
            
            return PublishResponse(
                title=content.title,
                content=content.content,
                images=len(valid_images),
                status="发布完成"
            )
        finally:
            await page.close()
    
    async def publish_video(self, content: PublishVideoContent) -> PublishResponse:
        """发布视频内容"""
        # 验证标题长度
        if self._calc_title_length(content.title) > 20:
            raise ValueError("标题长度超过限制（最多20个字）")
        
        # 验证视频文件存在
        if not os.path.exists(content.video):
            raise ValueError(f"视频文件不存在: {content.video}")
        
        # 验证定时发布时间
        if content.schedule_at:
            self._validate_schedule_time(content.schedule_at)
        
        page = await self.browser.new_page()
        
        try:
            # 导航到发布页面
            await page.goto(self.PUBLISH_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            
            # 点击"上传视频" Tab
            await self._click_publish_tab(page, "上传视频")
            await asyncio.sleep(1)
            
            # 上传视频
            await self._upload_video(page, content.video)
            
            # 填写标题和内容
            await self._submit_publish(
                page,
                content.title,
                content.content,
                content.tags,
                content.schedule_at
            )
            
            logger.info(f"视频发布成功: {content.title}")
            
            return PublishResponse(
                title=content.title,
                content=content.content,
                video=content.video,
                status="发布完成"
            )
        finally:
            await page.close()
    
    def _calc_title_length(self, title: str) -> int:
        """计算标题长度（中文算1个字，英文单词算1个字）"""
        # 简化处理：直接返回字符数
        return len(title)
    
    def _validate_schedule_time(self, schedule_time: datetime) -> None:
        """验证定时发布时间"""
        now = datetime.now()
        min_time = now + timedelta(hours=1)
        max_time = now + timedelta(days=14)
        
        if schedule_time < min_time:
            raise ValueError(f"定时发布时间必须至少在1小时后")
        if schedule_time > max_time:
            raise ValueError(f"定时发布时间不能超过14天")
    
    async def _click_publish_tab(self, page: Page, tab_name: str) -> None:
        """点击发布 Tab"""
        # 等待上传区域出现
        await page.wait_for_selector("div.upload-content", timeout=15000)
        
        # 尝试点击对应的 Tab
        for _ in range(30):  # 最多尝试 15 秒
            tabs = await page.locator("div.creator-tab").all()
            for tab in tabs:
                text = await tab.text_content()
                if text and text.strip() == tab_name:
                    # 检查是否被遮挡
                    is_visible = await tab.is_visible()
                    if is_visible:
                        try:
                            await tab.click()
                            logger.debug(f"已点击 Tab: {tab_name}")
                            return
                        except Exception as e:
                            logger.debug(f"点击 Tab 失败，重试: {e}")
            
            # 尝试移除弹窗遮挡
            await self._remove_popup(page)
            await asyncio.sleep(0.5)
        
        raise Exception(f"无法点击 Tab: {tab_name}")
    
    async def _remove_popup(self, page: Page) -> None:
        """移除弹窗遮挡"""
        try:
            popup = page.locator("div.d-popover")
            if await popup.count() > 0:
                await page.evaluate("document.querySelector('div.d-popover')?.remove()")
        except:
            pass
        
        # 点击空白位置
        try:
            await page.mouse.click(400, 50)
        except:
            pass
    
    async def _upload_images(self, page: Page, image_paths: list[str]) -> None:
        """上传图片"""
        for i, path in enumerate(image_paths):
            # 第一张图片使用 .upload-input，后续使用 input[type="file"]
            selector = ".upload-input" if i == 0 else 'input[type="file"]'
            
            file_input = page.locator(selector).first
            await file_input.set_input_files(path)
            logger.info(f"已上传图片 {i+1}: {path}")
            
            # 等待上传完成
            await self._wait_upload_complete(page, i + 1)
            await asyncio.sleep(1)
    
    async def _wait_upload_complete(self, page: Page, expected_count: int) -> None:
        """等待图片上传完成"""
        max_wait = 60  # 最多等待 60 秒
        for _ in range(max_wait * 2):
            preview_count = await page.locator(".img-preview-area .pr").count()
            if preview_count >= expected_count:
                logger.debug(f"图片上传完成: {preview_count}/{expected_count}")
                return
            await asyncio.sleep(0.5)
        
        raise Exception(f"图片上传超时")
    
    async def _upload_video(self, page: Page, video_path: str) -> None:
        """上传视频"""
        file_input = page.locator(".upload-input").first
        await file_input.set_input_files(video_path)
        logger.info(f"已上传视频: {video_path}")
        
        # 等待视频处理完成（视频处理时间较长）
        await self._wait_video_process(page)
    
    async def _wait_video_process(self, page: Page) -> None:
        """等待视频处理完成"""
        max_wait = 300  # 最多等待 5 分钟
        for _ in range(max_wait):
            # 检查视频预览是否出现
            video_preview = page.locator(".video-preview, .upload-success")
            if await video_preview.count() > 0:
                logger.info("视频处理完成")
                return
            await asyncio.sleep(1)
        
        raise Exception("视频处理超时")
    
    async def _submit_publish(
        self, 
        page: Page, 
        title: str, 
        content: str, 
        tags: list[str],
        schedule_time: Optional[datetime] = None
    ) -> None:
        """提交发布"""
        # 输入标题
        title_input = page.locator("div.d-input input")
        await title_input.fill(title)
        await asyncio.sleep(0.5)
        
        # 检查标题长度
        await self._check_title_length(page)
        logger.debug("标题长度检查通过")
        
        await asyncio.sleep(1)
        
        # 输入正文
        content_elem = await self._get_content_element(page)
        await content_elem.fill(content)
        
        # 输入标签
        if tags:
            await self._input_tags(page, content_elem, tags)
        
        await asyncio.sleep(1)
        
        # 检查正文长度
        await self._check_content_length(page)
        logger.debug("正文长度检查通过")
        
        # 设置定时发布
        if schedule_time:
            await self._set_schedule_publish(page, schedule_time)
        
        # 点击发布按钮
        submit_btn = page.locator(".publish-page-publish-btn button.bg-red")
        await submit_btn.click()
        
        await asyncio.sleep(3)
    
    async def _get_content_element(self, page: Page):
        """获取正文输入框"""
        # 尝试两种选择器
        ql_editor = page.locator("div.ql-editor")
        if await ql_editor.count() > 0:
            return ql_editor.first
        
        # 备用方案：查找带 placeholder 的元素
        textbox = page.locator('[role="textbox"]')
        if await textbox.count() > 0:
            return textbox.first
        
        raise Exception("无法找到正文输入框")
    
    async def _check_title_length(self, page: Page) -> None:
        """检查标题长度"""
        error_elem = page.locator("div.title-container div.max_suffix")
        if await error_elem.count() > 0:
            text = await error_elem.text_content()
            raise ValueError(f"标题长度超过限制: {text}")
    
    async def _check_content_length(self, page: Page) -> None:
        """检查正文长度"""
        error_elem = page.locator("div.edit-container div.length-error")
        if await error_elem.count() > 0:
            text = await error_elem.text_content()
            raise ValueError(f"正文长度超过限制: {text}")
    
    async def _input_tags(self, page: Page, content_elem, tags: list[str]) -> None:
        """输入标签"""
        if not tags or len(tags) == 0:
            return
        
        # 限制最多 10 个标签
        if len(tags) > 10:
            logger.warning("标签数量超过10，截取前10个")
            tags = tags[:10]
        
        await asyncio.sleep(1)
        
        # 移动到内容末尾
        for _ in range(20):
            await content_elem.press("ArrowDown")
            await asyncio.sleep(0.01)
        
        await content_elem.press("Enter")
        await content_elem.press("Enter")
        await asyncio.sleep(1)
        
        # 逐个输入标签
        for tag in tags:
            tag = tag.lstrip("#")
            await self._input_single_tag(page, content_elem, tag)
    
    async def _input_single_tag(self, page: Page, content_elem, tag: str) -> None:
        """输入单个标签"""
        # 输入 #
        await content_elem.type("#")
        await asyncio.sleep(0.2)
        
        # 逐字输入标签
        for char in tag:
            await content_elem.type(char)
            await asyncio.sleep(0.05)
        
        await asyncio.sleep(1)
        
        # 尝试点击标签联想
        topic_container = page.locator("#creator-editor-topic-container")
        if await topic_container.count() > 0:
            first_item = topic_container.locator(".item").first
            if await first_item.count() > 0:
                try:
                    await first_item.click()
                    logger.debug(f"已选择标签: {tag}")
                    await asyncio.sleep(0.5)
                    return
                except:
                    pass
        
        # 如果没有联想，直接输入空格
        await content_elem.type(" ")
        await asyncio.sleep(0.5)
    
    async def _set_schedule_publish(self, page: Page, schedule_time: datetime) -> None:
        """设置定时发布"""
        # 点击定时发布开关
        switch = page.locator(".post-time-wrapper .d-switch")
        await switch.click()
        logger.debug("已点击定时发布开关")
        await asyncio.sleep(0.8)
        
        # 设置日期时间
        date_str = schedule_time.strftime("%Y-%m-%d %H:%M")
        date_input = page.locator(".date-picker-container input")
        await date_input.select_text()
        await date_input.fill(date_str)
        logger.info(f"已设置定时发布: {date_str}")
        
        await asyncio.sleep(0.5)
