from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class XiaohongshuNote:
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    cover_image_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "tags": self.tags,
            "cover_image_path": self.cover_image_path
        }
