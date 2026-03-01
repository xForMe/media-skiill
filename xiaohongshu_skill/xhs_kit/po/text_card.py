"""文字配图发布模块"""

import asyncio
from typing import Optional, List
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.models import PublishResponse


# 卡片样式映射
CARD_STYLES = [
    "基础", "边框", "备忘", "手写", "便签", "涂写", 
    "简约", "光影", "几何"
]


class TextCardAction:
    """文字配图发布操作"""
    
    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
    
    # 选择器
    SELECTOR_UPLOAD_IMAGE_TAB = "text=上传图文"
    SELECTOR_TEXT_CARD_BTN = "text=文字配图"
    SELECTOR_TEXT_INPUT = "[contenteditable='true']"
    SELECTOR_ADD_PAGE_BTN = "text=再写一张"
    SELECTOR_GENERATE_BTN = "text=生成图片"
    SELECTOR_TITLE_INPUT = "[class*='title'] input, input[placeholder*='标题']"
    SELECTOR_CONTENT_INPUT = "[class*='content'] textarea, textarea[placeholder*='正文']"
    SELECTOR_PUBLISH_BTN = "button:has-text('发布')"
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def publish_text_card(
        self,
        cover_text: str,
        pages: Optional[List[str]] = None,
        style: str = "基础",
        title: str = "",
        content: str = "",
        tags: Optional[List[str]] = None
    ) -> PublishResponse:
        """
        发布文字配图笔记
        
        Args:
            cover_text: 封面文字
            pages: 正文页列表（最多17页）
            style: 卡片样式（基础、边框、备忘、手写、便签、涂写、简约、光影、几何）
            title: 文字标题
            content: 文字正文内容
            tags: 话题标签列表
        
        Returns:
            PublishResponse: 发布结果
        """
        page = await self.browser.new_page()
        
        try:
            # 1. 导航到发布页面
            logger.info("正在打开发布页面...")
            await page.goto(self.PUBLISH_URL)
            await asyncio.sleep(2)
            
            # 2. 点击"上传图文"标签 - 直接导航到图文上传页面
            logger.info("导航到图文上传页面...")
            await page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image")
            await asyncio.sleep(2)
            
            # 3. 点击"文字配图"按钮
            logger.info("点击文字配图按钮...")
            text_card_btn = await page.wait_for_selector("button:has-text('文字配图')", timeout=10000)
            if text_card_btn:
                await text_card_btn.click()
            await asyncio.sleep(2)  # 等待页面加载
            
            # 4. 填写封面文字
            logger.info(f"填写封面文字: {cover_text[:20]}...")
            textarea = await page.wait_for_selector(self.SELECTOR_TEXT_INPUT, timeout=10000)
            if textarea:
                # contenteditable 元素需要用 type 而不是 fill
                await textarea.click()
                await textarea.type(cover_text)
            else:
                logger.warning("未找到文字输入框")
            await asyncio.sleep(0.5)
            
            # 5. 添加正文页
            if pages:
                for i, page_text in enumerate(pages[:17]):  # 最多17页
                    logger.info(f"添加第 {i+2} 页...")
                    # 点击"再写一张"
                    add_btn = await page.query_selector(self.SELECTOR_ADD_PAGE_BTN)
                    if add_btn:
                        await add_btn.click()
                        await asyncio.sleep(0.5)
                        
                        # 找到最新的文本框并填写
                        textareas = await page.query_selector_all(self.SELECTOR_TEXT_INPUT)
                        if textareas and len(textareas) > i + 1:
                            await textareas[-1].click()
                            await textareas[-1].type(page_text)
                        await asyncio.sleep(0.3)
            
            # 6. 点击"生成图片"
            logger.info("生成图片...")
            generate_btn = await page.query_selector(self.SELECTOR_GENERATE_BTN)
            if generate_btn:
                await generate_btn.click()
                await asyncio.sleep(5)  # 等待图片生成，需要更长时间
            else:
                logger.warning("未找到生成图片按钮")
            
            # 7. 选择卡片样式
            if style and style in CARD_STYLES:
                logger.info(f"选择卡片样式: {style}")
                style_selector = f"text={style}"
                style_btn = await page.query_selector(style_selector)
                if style_btn:
                    await style_btn.click()
                    await asyncio.sleep(2)
            
            # 8. 点击确认/下一步按钮进入编辑页面
            logger.info("进入编辑页面...")
            # 可能需要点击确认按钮
            confirm_btn = await page.query_selector("button:has-text('确认'), button:has-text('下一步'), button:has-text('完成')")
            if confirm_btn:
                await confirm_btn.click()
                await asyncio.sleep(2)
            
            # 9. 填写标题和正文
            logger.info("填写标题和正文...")
            await asyncio.sleep(2)
            
            # 填写标题 - 使用与 publish.py 相同的选择器
            if title:
                title_selectors = [
                    "div.d-input input",
                    "input[placeholder*='标题']",
                    "[class*='title'] input",
                    "input[type='text']"
                ]
                title_filled = False
                for sel in title_selectors:
                    title_input = await page.query_selector(sel)
                    if title_input:
                        try:
                            await title_input.fill(title)
                            logger.info(f"标题已填写，使用选择器: {sel}")
                            title_filled = True
                            break
                        except Exception as e:
                            logger.warning(f"使用选择器 {sel} 填写标题失败: {e}")
                            continue
                
                if not title_filled:
                    logger.warning("未能找到标题输入框")
            
            # 填写正文 - 使用与 publish.py 相同的选择器
            if content:
                content_selectors = [
                    "div.ql-editor",
                    "[role='textbox']",
                    "textarea[placeholder*='正文']",
                    "[class*='content'] textarea",
                    "[class*='desc'] textarea"
                ]
                content_filled = False
                for sel in content_selectors:
                    content_input = await page.query_selector(sel)
                    if content_input:
                        try:
                            # ql-editor 需要先点击再填写
                            await content_input.click()
                            await asyncio.sleep(0.3)
                            await content_input.fill(content)
                            logger.info(f"正文已填写，使用选择器: {sel}")
                            content_filled = True
                            break
                        except Exception as e:
                            logger.warning(f"使用选择器 {sel} 填写正文失败: {e}")
                            continue
                
                if not content_filled:
                    logger.warning("未能找到正文输入框，尝试使用 JavaScript 填写")
                    # 尝试使用 JavaScript 直接设置内容
                    await page.evaluate(f'''() => {{
                        const editor = document.querySelector('div.ql-editor');
                        if (editor) {{
                            editor.innerHTML = '<p>{content}</p>';
                            return true;
                        }}
                        return false;
                    }}''')
            
            # 10. 添加标签（暂时跳过，标签功能有问题）
            # if tags:
            #     logger.info(f"添加标签: {tags}")
            #     # TODO: 修复标签功能
            
            # 11. 点击发布
            logger.info("点击发布按钮...")
            publish_selectors = [
                "button:has-text('发布')",
                "[class*='publish'] button",
                "button[class*='submit']"
            ]
            for sel in publish_selectors:
                publish_btn = await page.query_selector(sel)
                if publish_btn:
                    await publish_btn.click()
                    logger.info(f"发布按钮已点击，使用选择器: {sel}")
                    await asyncio.sleep(3)
                    break
            
            # 10. 检查发布结果
            # 检查是否有成功提示或跳转
            current_url = page.url
            if "publish" not in current_url or "success" in current_url:
                logger.info("发布成功！")
                return PublishResponse(
                    status="success",
                    message="文字配图发布成功"
                )
            else:
                # 检查是否有错误提示
                error_msg = await page.query_selector("[class*='error'], [class*='toast']")
                if error_msg:
                    error_text = await error_msg.text_content()
                    return PublishResponse(
                        status="failed",
                        message=f"发布失败: {error_text}"
                    )
                
                return PublishResponse(
                    status="unknown",
                    message="发布状态未知，请手动检查"
                )
                
        except Exception as e:
            logger.error(f"发布文字配图失败: {e}")
            return PublishResponse(
                status="failed",
                message=f"发布失败: {str(e)}"
            )
        finally:
            await page.close()
