"""数据模型定义"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginStatus(BaseModel):
    """登录状态"""
    is_logged_in: bool
    username: Optional[str] = None


class LoginQrcodeResponse(BaseModel):
    """登录二维码响应"""
    timeout: str
    is_logged_in: bool
    img: Optional[str] = None


class PublishImageContent(BaseModel):
    """发布图文内容"""
    title: str = Field(..., max_length=20, description="标题，最多20个字")
    content: str = Field(..., description="正文内容")
    images: list[str] = Field(..., min_length=1, description="图片路径列表")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    schedule_at: Optional[datetime] = Field(None, description="定时发布时间")


class PublishVideoContent(BaseModel):
    """发布视频内容"""
    title: str = Field(..., max_length=20, description="标题，最多20个字")
    content: str = Field(..., description="正文内容")
    video: str = Field(..., description="视频文件路径")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    schedule_at: Optional[datetime] = Field(None, description="定时发布时间")


class PublishResponse(BaseModel):
    """发布响应"""
    title: Optional[str] = None
    content: Optional[str] = None
    images: Optional[int] = None
    video: Optional[str] = None
    status: str
    message: Optional[str] = None
    post_id: Optional[str] = None


class Feed(BaseModel):
    """Feed 信息"""
    id: str
    model_type: str
    xsec_token: str
    display_title: str
    note_type: str
    user_id: str
    nickname: str
    liked_count: str
    cover_url: Optional[str] = None


class FeedsListResponse(BaseModel):
    """Feeds 列表响应"""
    feeds: list[Feed]
    count: int


class FilterOption(BaseModel):
    """搜索筛选选项"""
    sort_by: Optional[str] = Field(None, description="排序: 综合|最新|最多点赞|最多评论|最多收藏")
    note_type: Optional[str] = Field(None, description="类型: 不限|视频|图文")
    publish_time: Optional[str] = Field(None, description="时间: 不限|一天内|一周内|半年内")
    search_scope: Optional[str] = Field(None, description="范围: 不限|已看过|未看过|已关注")
    location: Optional[str] = Field(None, description="位置: 不限|同城|附近")


class CommentLoadConfig(BaseModel):
    """评论加载配置"""
    load_all_comments: bool = Field(False, description="是否加载全部评论")
    limit: int = Field(20, description="限制加载的一级评论数量")
    click_more_replies: bool = Field(False, description="是否展开二级回复")
    reply_limit: int = Field(10, description="跳过回复数过多的评论")
    scroll_speed: str = Field("normal", description="滚动速度: slow|normal|fast")
