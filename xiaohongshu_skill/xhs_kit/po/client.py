"""小红书客户端"""

from typing import Optional
from datetime import datetime
import time

from xhs_kit.po.browser import BrowserManager
from xhs_kit.po.login import LoginAction
from xhs_kit.po.publish import PublishAction
from xhs_kit.po.search import SearchAction
from xhs_kit.po.feeds import FeedsListAction
from xhs_kit.po.feed_detail import FeedDetailAction
from xhs_kit.po.user_profile import UserProfileAction
from xhs_kit.po.interact import LikeAction, FavoriteAction, CommentAction
from xhs_kit.po.text_card import TextCardAction
from xhs_kit.po.models import (
    LoginStatus,
    LoginQrcodeResponse,
    PublishImageContent,
    PublishVideoContent,
    PublishResponse,
    FeedsListResponse,
    FilterOption,
)


class XhsClient:
    """小红书客户端

    提供登录、发布等功能的统一接口
    优化：浏览器延迟初始化，只在需要时才打开
    """

    def __init__(self, headless: bool = True, bin_path: Optional[str] = None):
        """初始化客户端

        Args:
            headless: 是否无头模式运行浏览器
            bin_path: 浏览器可执行文件路径（可选）
        """
        self._headless = headless
        self._bin_path = bin_path
        self._browser: Optional[BrowserManager] = None
        self._login_action: Optional[LoginAction] = None
        self._publish_action: Optional[PublishAction] = None
        self._search_action: Optional[SearchAction] = None
        self._feeds_action: Optional[FeedsListAction] = None
        self._feed_detail_action: Optional[FeedDetailAction] = None
        self._user_profile_action: Optional[UserProfileAction] = None
        self._like_action: Optional[LikeAction] = None
        self._favorite_action: Optional[FavoriteAction] = None
        self._comment_action: Optional[CommentAction] = None
        self._text_card_action: Optional[TextCardAction] = None

        self._login_verify_cache_at: Optional[float] = None
        self._login_verify_cache_ok: Optional[bool] = None
    
    def _ensure_browser(self) -> BrowserManager:
        """确保浏览器已初始化（延迟加载）"""
        if self._browser is None:
            self._browser = BrowserManager(headless=self._headless, bin_path=self._bin_path)
            # 初始化所有依赖 browser 的 actions
            self._login_action = LoginAction(self._browser)
            self._publish_action = PublishAction(self._browser)
            self._search_action = SearchAction(self._browser)
            self._feeds_action = FeedsListAction(self._browser)
            self._feed_detail_action = FeedDetailAction(self._browser)
            self._user_profile_action = UserProfileAction(self._browser)
            self._like_action = LikeAction(self._browser)
            self._favorite_action = FavoriteAction(self._browser)
            self._comment_action = CommentAction(self._browser)
            self._text_card_action = TextCardAction(self._browser)
        return self._browser

    @property
    def browser(self) -> BrowserManager:
        """获取浏览器实例（延迟初始化）"""
        return self._ensure_browser()

    async def check_login_status(self, quick: bool = False) -> LoginStatus:
        """检查登录状态

        Args:
            quick: 如果为 True，只检查 cookies 文件是否存在，不打开浏览器验证
        """
        if quick:
            # quick 模式下不初始化 browser，直接检查 cookies 文件
            from xhs_kit.po.cookies import get_cookies_file_path
            from xhs_kit.po.models import LoginStatus
            has_cookies = get_cookies_file_path().exists()
            return LoginStatus(is_logged_in=has_cookies, user_info=None)
        # 非 quick 模式需要 browser
        self._ensure_browser()
        return await self._login_action.check_login_status(quick=quick)

    async def is_logged_in(self, quick: bool = False) -> bool:
        """是否已登录

        Args:
            quick: 如果为 True，只检查 cookies 文件是否存在，不打开浏览器验证
        """
        status = await self.check_login_status(quick=quick)
        return status.is_logged_in

    async def verify_login(self, ttl_seconds: int = 0, force: bool = False) -> bool:
        """验证登录状态（会打开 headless 浏览器检查 DOM）

        Args:
            ttl_seconds: 缓存有效期（秒）。为 0 表示不缓存。
            force: 为 True 时忽略缓存，强制重新验证。
        """
        now = time.time()
        if (
            not force
            and ttl_seconds > 0
            and self._login_verify_cache_at is not None
            and self._login_verify_cache_ok is not None
            and (now - self._login_verify_cache_at) < ttl_seconds
        ):
            return self._login_verify_cache_ok

        status = await self.check_login_status(quick=False)
        ok = bool(status.is_logged_in)
        if ttl_seconds > 0:
            self._login_verify_cache_at = now
            self._login_verify_cache_ok = ok
        return ok

    def has_cookies(self) -> bool:
        """快速检查是否有 cookies 文件（同步方法，不打开浏览器）"""
        from xhs_kit.po.cookies import get_cookies_file_path
        return get_cookies_file_path().exists()

    async def get_login_qrcode(self) -> LoginQrcodeResponse:
        """获取登录二维码

        返回二维码图片数据，扫码后自动保存 cookies
        """
        self._ensure_browser()
        return await self._login_action.get_login_qrcode()

    async def login(self) -> bool:
        """交互式登录

        打开浏览器窗口，等待用户扫码登录
        注意：需要 headless=False 才能看到浏览器窗口
        """
        self._ensure_browser()
        return await self._login_action.login_interactive()

    def delete_cookies(self) -> None:
        """删除 cookies，重置登录状态"""
        if self._browser:
            self._browser.delete_cookies()
        else:
            # 即使没有初始化 browser 也能删除 cookies
            from xhs_kit.po.cookies import get_cookies_file_path
            cookies_file = get_cookies_file_path()
            if cookies_file.exists():
                cookies_file.unlink()
                print(f"已删除 cookies 文件: {cookies_file}")
    
    async def publish(
        self,
        title: str,
        content: str,
        images: list[str],
        tags: Optional[list[str]] = None,
        schedule_at: Optional[datetime] = None
    ) -> PublishResponse:
        """发布图文内容

        Args:
            title: 文字标题（最多20个字）
            content: 文字正文内容
            images: 图片路径列表（至少1张）
            tags: 标签列表（可选，最多10个）
            schedule_at: 定时发布时间（可选，1小时至14天内）
        """
        self._ensure_browser()
        publish_content = PublishImageContent(
            title=title,
            content=content,
            images=images,
            tags=tags or [],
            schedule_at=schedule_at
        )
        return await self._publish_action.publish_image(publish_content)

    async def publish_video(
        self,
        title: str,
        content: str,
        video: str,
        tags: Optional[list[str]] = None,
        schedule_at: Optional[datetime] = None
    ) -> PublishResponse:
        """发布视频内容

        Args:
            title: 文字标题（最多20个字）
            content: 文字正文内容
            video: 视频文件路径
            tags: 标签列表（可选，最多10个）
            schedule_at: 定时发布时间（可选，1小时至14天内）
        """
        self._ensure_browser()
        publish_content = PublishVideoContent(
            title=title,
            content=content,
            video=video,
            tags=tags or [],
            schedule_at=schedule_at
        )
        return await self._publish_action.publish_video(publish_content)

    async def search(
        self,
        keyword: str,
        filters: Optional[FilterOption] = None
    ) -> FeedsListResponse:
        """搜索小红书内容

        Args:
            keyword: 搜索关键词
            filters: 筛选选项（可选）
        """
        self._ensure_browser()
        return await self._search_action.search(keyword, filters)

    async def get_feeds(self) -> FeedsListResponse:
        """获取首页推荐列表"""
        self._ensure_browser()
        return await self._feeds_action.get_feeds_list()

    async def get_feed_detail(self, feed_id: str, xsec_token: str, load_comments: bool = False) -> dict:
        """获取笔记详情

        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            load_comments: 是否加载评论
        """
        self._ensure_browser()
        return await self._feed_detail_action.get_feed_detail(feed_id, xsec_token, load_comments)

    async def get_feed_detail_with_config(self, feed_id: str, xsec_token: str, config) -> dict:
        """获取笔记详情（带评论加载配置）

        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            config: CommentLoadConfig 评论加载配置
        """
        self._ensure_browser()
        return await self._feed_detail_action.get_feed_detail_with_config(feed_id, xsec_token, config)

    async def get_user_profile(self, user_id: str, xsec_token: str) -> dict:
        """获取用户主页

        Args:
            user_id: 用户 ID
            xsec_token: 访问令牌
        """
        self._ensure_browser()
        return await self._user_profile_action.get_user_profile(user_id, xsec_token)

    async def like(self, feed_id: str, xsec_token: str) -> dict:
        """点赞笔记"""
        self._ensure_browser()
        return await self._like_action.like(feed_id, xsec_token)

    async def unlike(self, feed_id: str, xsec_token: str) -> dict:
        """取消点赞"""
        self._ensure_browser()
        return await self._like_action.unlike(feed_id, xsec_token)

    async def favorite(self, feed_id: str, xsec_token: str) -> dict:
        """收藏笔记"""
        self._ensure_browser()
        return await self._favorite_action.favorite(feed_id, xsec_token)

    async def unfavorite(self, feed_id: str, xsec_token: str) -> dict:
        """取消收藏"""
        self._ensure_browser()
        return await self._favorite_action.unfavorite(feed_id, xsec_token)

    async def comment(self, feed_id: str, xsec_token: str, content: str) -> dict:
        """发表评论

        Args:
            feed_id: 笔记 ID
            xsec_token: 访问令牌
            content: 评论内容
        """
        self._ensure_browser()
        return await self._comment_action.post_comment(feed_id, xsec_token, content)

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
        self._ensure_browser()
        return await self._comment_action.reply_comment(
            feed_id, xsec_token, content, comment_id, user_id
        )

    async def publish_text_card(
        self,
        cover_text: str,
        pages: Optional[list[str]] = None,
        style: str = "基础",
        title: str = "",
        content: str = "",
        tags: Optional[list[str]] = None
    ) -> PublishResponse:
        """发布文字配图笔记

        Args:
            cover_text: 封面文字
            pages: 正文页列表（最多17页）
            style: 卡片样式（基础、边框、备忘、手写、便签、涂写、简约、光影、几何）
            title: 笔记标题
            content: 笔记正文描述
            tags: 话题标签列表
        """
        self._ensure_browser()
        return await self._text_card_action.publish_text_card(
            cover_text=cover_text,
            pages=pages,
            style=style,
            title=title,
            content=content,
            tags=tags
        )

    async def close(self) -> None:
        """关闭客户端，释放资源"""
        if self._browser:
            await self._browser.close()
            self._browser = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
