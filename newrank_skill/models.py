from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Article:
    title: str
    author: Optional[str]
    account_id: Optional[str]
    pub_time: Optional[str]
    summary: Optional[str]
    content: Optional[str]
    read_count: Optional[int]
    like_count: Optional[int]
    hot_words: List[str] = field(default_factory=list)
    topics: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Article":
        return cls(
            title=data.get("title", ""),
            author=data.get("userName"),
            account_id=data.get("accountId"),
            pub_time=data.get("pubTime"),
            summary=data.get("summary"),
            content=data.get("content"),
            read_count=data.get("readCount"),
            like_count=data.get("likeCount"),
            hot_words=data.get("hotWords", []),
            topics=data.get("topic")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "account_id": self.account_id,
            "pub_time": self.pub_time,
            "summary": self.summary,
            "content": self.content,
            "read_count": self.read_count,
            "like_count": self.like_count,
            "hot_words": self.hot_words,
            "topics": self.topics
        }
