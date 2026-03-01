"""MCP 服务端"""

import base64
import io
import sys
from typing import Optional
from mcp.server.fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)

from xhs_kit.po.client import XhsClient


def print_qrcode_to_terminal(img_base64: str) -> str:
    """将 base64 图片解析为二维码并打印到终端
    
    Returns:
        str: 二维码内容的 URL，如果解析失败则返回空字符串
    """
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
        
        # 解析 base64 图片
        if img_base64.startswith('data:'):
            # 去掉 data:image/xxx;base64, 前缀
            img_base64 = img_base64.split(',', 1)[1]
        
        img_data = base64.b64decode(img_base64)
        img = Image.open(io.BytesIO(img_data))
        
        # 解码二维码
        decoded = decode(img)
        if not decoded:
            logger.warning("无法解析二维码内容")
            return ""
        
        qr_data = decoded[0].data.decode('utf-8')
        
        # 生成终端可显示的二维码
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # 获取二维码矩阵
        matrix = qr.get_matrix()
        
        # 打印到 stderr（不干扰 MCP 通信）
        print("\n" + "="*60, file=sys.stderr)
        print("请使用小红书 App 扫描以下二维码登录:", file=sys.stderr)
        print("="*60, file=sys.stderr)
        
        # 使用 Unicode 块字符打印二维码（更清晰）
        # 每两行合并为一行，使用 ▀ ▄ █ 字符
        for row_idx in range(0, len(matrix), 2):
            line = ""
            for col_idx in range(len(matrix[0])):
                top = matrix[row_idx][col_idx] if row_idx < len(matrix) else False
                bottom = matrix[row_idx + 1][col_idx] if row_idx + 1 < len(matrix) else False
                
                if top and bottom:
                    line += "█"
                elif top and not bottom:
                    line += "▀"
                elif not top and bottom:
                    line += "▄"
                else:
                    line += " "
            print(line, file=sys.stderr)
        
        print("="*60, file=sys.stderr)
        print(f"二维码链接: {qr_data}", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        sys.stderr.flush()
        
        return qr_data
    except ImportError as e:
        logger.warning(f"缺少依赖库: {e}，无法打印终端二维码")
        return ""
    except Exception as e:
        logger.warning(f"解析二维码失败: {e}")
        return ""


# 创建 MCP Server
mcp = FastMCP(name="xiaohongshu-mcp")

# 全局客户端实例
_client: Optional[XhsClient] = None
_headless: bool = True


def get_client() -> XhsClient:
    """获取客户端实例"""
    global _client
    if _client is None:
        _client = XhsClient(headless=_headless)
    return _client


@mcp.tool()
async def check_login_status() -> dict:
    """检查小红书登录状态（只检查 cookies 文件是否存在）"""
    from xhs_kit.po.cookies import get_cookies_file_path
    has_cookies = get_cookies_file_path().exists()
    return {
        "is_logged_in": has_cookies,
        "username": None
    }


@mcp.tool()
async def login_with_browser() -> dict:
    """浏览器扫码登录（会弹出浏览器窗口）。
    
    注意：在 Claude Code 中，推荐使用命令行登录：xhs-mcp login-qrcode --terminal
    """
    # 先检查是否已有 cookies
    from xhs_kit.po.cookies import get_cookies_file_path
    if get_cookies_file_path().exists():
        return {
            "is_logged_in": True,
            "message": "已登录，无需重复登录"
        }
    
    # 使用非 headless 模式的客户端
    from xhs_kit.po.client import XhsClient
    
    async with XhsClient(headless=False) as client:
        success = await client.login()
        return {
            "is_logged_in": success,
            "message": "登录成功，cookies 已保存" if success else "登录失败或超时，请重试"
        }


@mcp.tool()
async def get_login_qrcode() -> dict:
    """获取登录二维码（返回 Base64 图片）。
    
    返回二维码图片的 Base64 编码，需要配合轮询 check_login_status 使用。
    推荐使用 login_with_browser 工具或命令行 xhs-mcp login-qrcode --terminal 登录。
    """
    client = get_client()
    result = await client.get_login_qrcode()
    return {
        "timeout": result.timeout,
        "is_logged_in": result.is_logged_in,
        "img": result.img
    }


@mcp.tool()
async def delete_cookies() -> dict:
    """删除 cookies 文件，重置登录状态。删除后需要重新登录。"""
    client = get_client()
    client.delete_cookies()
    return {"success": True, "message": "Cookies 已删除"}


@mcp.tool()
async def publish_content(
    title: str,
    content: str,
    images: list[str],
    tags: Optional[list[str]] = None,
    schedule_at: Optional[str] = None
) -> dict:
    """发布小红书图文内容
    
    Args:
        title: 文字标题（小红书限制：最多20个中文字或英文单词）
        content: 文字正文内容，不包含以#开头的标签内容
        images: 图片路径列表（至少需要1张图片），支持本地绝对路径
        tags: 话题标签列表（可选），如 ["美食", "旅行", "生活"]
        schedule_at: 定时发布时间（可选），ISO8601格式如 2024-01-20T10:30:00+08:00
    """
    from datetime import datetime
    
    client = get_client()
    
    schedule_time = None
    if schedule_at:
        schedule_time = datetime.fromisoformat(schedule_at)
    
    result = await client.publish(
        title=title,
        content=content,
        images=images,
        tags=tags,
        schedule_at=schedule_time
    )
    
    return {
        "title": result.title,
        "content": result.content,
        "images": result.images,
        "status": result.status
    }


@mcp.tool()
async def publish_with_video(
    title: str,
    content: str,
    video: str,
    tags: Optional[list[str]] = None,
    schedule_at: Optional[str] = None
) -> dict:
    """发布小红书视频内容（仅支持本地单个视频文件）
    
    Args:
        title: 文字标题（小红书限制：最多20个中文字或英文单词）
        content: 文字正文内容，不包含以#开头的标签内容
        video: 本地视频绝对路径（仅支持单个视频文件）
        tags: 话题标签列表（可选），如 ["美食", "旅行", "生活"]
        schedule_at: 定时发布时间（可选），ISO8601格式如 2024-01-20T10:30:00+08:00
    """
    from datetime import datetime
    
    client = get_client()
    
    schedule_time = None
    if schedule_at:
        schedule_time = datetime.fromisoformat(schedule_at)
    
    result = await client.publish_video(
        title=title,
        content=content,
        video=video,
        tags=tags,
        schedule_at=schedule_time
    )
    
    return {
        "title": result.title,
        "content": result.content,
        "video": result.video,
        "status": result.status
    }


@mcp.tool()
async def search_feeds(
    keyword: str, 
    sort_by: Optional[str] = None, 
    note_type: Optional[str] = None,
    publish_time: Optional[str] = None,
    search_scope: Optional[str] = None,
    location: Optional[str] = None
) -> dict:
    """搜索小红书内容
    
    Args:
        keyword: 搜索关键词
        sort_by: 排序方式（可选）: 综合|最新|最多点赞|最多评论|最多收藏
        note_type: 笔记类型（可选）: 不限|视频|图文
        publish_time: 发布时间（可选）: 不限|一天内|一周内|半年内
        search_scope: 搜索范围（可选）: 不限|已看过|未看过|已关注
        location: 位置距离（可选）: 不限|同城|附近
    """
    from xhs_kit.po.models import FilterOption
    
    client = get_client()
    filters = None
    if any([sort_by, note_type, publish_time, search_scope, location]):
        filters = FilterOption(
            sort_by=sort_by, 
            note_type=note_type,
            publish_time=publish_time,
            search_scope=search_scope,
            location=location
        )
    
    result = await client.search(keyword, filters)
    return {
        "count": result.count,
        "feeds": [f.model_dump() for f in result.feeds]
    }


@mcp.tool()
async def list_feeds() -> dict:
    """获取首页推荐列表"""
    client = get_client()
    result = await client.get_feeds()
    return {
        "count": result.count,
        "feeds": [f.model_dump() for f in result.feeds]
    }


@mcp.tool()
async def get_feed_detail(
    feed_id: str, 
    xsec_token: str, 
    load_comments: bool = False,
    load_all_comments: bool = False,
    limit: int = 20,
    click_more_replies: bool = False,
    reply_limit: int = 10,
    scroll_speed: str = "normal"
) -> dict:
    """获取笔记详情
    
    Args:
        feed_id: 笔记 ID，从搜索或推荐列表获取
        xsec_token: 访问令牌，从搜索或推荐列表获取
        load_comments: 是否加载评论列表（基础模式，仅前10条）
        load_all_comments: 是否加载全部评论（滚动加载更多）
        limit: 限制加载的一级评论数量（默认20，仅当load_all_comments为true时生效）
        click_more_replies: 是否展开二级回复（默认false，仅当load_all_comments为true时生效）
        reply_limit: 跳过回复数过多的评论（默认10，仅当click_more_replies为true时生效）
        scroll_speed: 滚动速度（slow|normal|fast，仅当load_all_comments为true时生效）
    """
    client = get_client()
    
    # 如果启用了 load_all_comments，传递配置参数
    if load_all_comments:
        from xhs_kit.po.models import CommentLoadConfig
        config = CommentLoadConfig(
            load_all_comments=load_all_comments,
            limit=limit,
            click_more_replies=click_more_replies,
            reply_limit=reply_limit,
            scroll_speed=scroll_speed
        )
        return await client.get_feed_detail_with_config(feed_id, xsec_token, config)
    
    # 否则使用基础模式
    return await client.get_feed_detail(feed_id, xsec_token, load_comments)


@mcp.tool()
async def get_user_profile(user_id: str, xsec_token: str) -> dict:
    """获取用户主页信息
    
    Args:
        user_id: 用户 ID
        xsec_token: 访问令牌
    """
    client = get_client()
    return await client.get_user_profile(user_id, xsec_token)


@mcp.tool()
async def like_feed(feed_id: str, xsec_token: str, unlike: bool = False) -> dict:
    """点赞或取消点赞笔记
    
    Args:
        feed_id: 笔记 ID
        xsec_token: 访问令牌
        unlike: 是否取消点赞，默认 False 为点赞
    """
    client = get_client()
    if unlike:
        return await client.unlike(feed_id, xsec_token)
    return await client.like(feed_id, xsec_token)


@mcp.tool()
async def favorite_feed(feed_id: str, xsec_token: str, unfavorite: bool = False) -> dict:
    """收藏或取消收藏笔记
    
    Args:
        feed_id: 笔记 ID
        xsec_token: 访问令牌
        unfavorite: 是否取消收藏，默认 False 为收藏
    """
    client = get_client()
    if unfavorite:
        return await client.unfavorite(feed_id, xsec_token)
    return await client.favorite(feed_id, xsec_token)


@mcp.tool()
async def post_comment(feed_id: str, xsec_token: str, content: str) -> dict:
    """发表评论到笔记
    
    Args:
        feed_id: 笔记 ID
        xsec_token: 访问令牌
        content: 评论内容
    """
    client = get_client()
    return await client.comment(feed_id, xsec_token, content)


@mcp.tool()
async def reply_comment(
    feed_id: str, 
    xsec_token: str, 
    content: str,
    comment_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> dict:
    """回复笔记下的指定评论
    
    Args:
        feed_id: 笔记 ID
        xsec_token: 访问令牌
        content: 回复内容
        comment_id: 目标评论 ID（可选，从评论列表获取）
        user_id: 目标用户 ID（可选，从评论列表获取）
    
    Note:
        comment_id 和 user_id 至少需要提供一个
    """
    client = get_client()
    return await client.reply_comment(feed_id, xsec_token, content, comment_id, user_id)


@mcp.tool()
async def publish_text_card(
    cover_text: str,
    pages: Optional[list[str]] = None,
    style: str = "基础",
    title: str = "",
    content: str = "",
    tags: Optional[list[str]] = None
) -> dict:
    """发布文字配图笔记（将文字生成为卡片图片）
    
    Args:
        cover_text: 封面文字内容
        pages: 正文页列表（最多17页），每页一段文字
        style: 卡片样式，可选：基础|边框|备忘|手写|便签|涂写|简约|光影|几何
        title: 文字标题
        content: 文字正文内容
        tags: 话题标签列表
    """
    client = get_client()
    result = await client.publish_text_card(
        cover_text=cover_text,
        pages=pages,
        style=style,
        title=title,
        content=content,
        tags=tags
    )
    return {
        "status": result.status,
        "message": result.message
    }


def init_server(headless: bool = True):
    """初始化服务器"""
    global _headless
    _headless = headless
    logger.info("MCP Server 已初始化")


def run_server(headless: bool = True):
    """运行 MCP 服务器（stdio 模式）"""
    init_server(headless=headless)
    mcp.run(transport="stdio")
