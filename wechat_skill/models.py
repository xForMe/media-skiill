from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class WeChatArticle:
    title: str
    content: str
    author: Optional[str] = None
    digest: Optional[str] = None
    thumb_media_id: Optional[str] = None
    content_source_url: Optional[str] = None
    need_open_comment: int = 1
    only_fans_can_comment: int = 0
    cover_image_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "digest": self.digest,
            "content": self.content,
            "content_source_url": self.content_source_url,
            "thumb_media_id": self.thumb_media_id,
            "need_open_comment": self.need_open_comment,
            "only_fans_can_comment": self.only_fans_can_comment
        }
