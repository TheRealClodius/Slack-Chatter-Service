from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class SlackUser:
    id: str
    name: str
    display_name: str
    real_name: str
    email: Optional[str] = None

@dataclass
class SlackReaction:
    name: str
    count: int
    users: List[str]

@dataclass
class SlackMessage:
    id: str  # message timestamp serves as ID
    text: str
    user_id: str
    user_name: str
    channel_id: str
    channel_name: str
    timestamp: datetime
    thread_ts: Optional[str] = None  # If this is a thread reply
    reply_count: int = 0
    reactions: List[SlackReaction] = field(default_factory=list)
    is_thread_parent: bool = False
    thread_replies: List['SlackMessage'] = field(default_factory=list)
    is_canvas: bool = False  # True if this is canvas content
    canvas_title: Optional[str] = None  # Canvas title if applicable
    
    def to_text_for_embedding(self) -> str:
        """Convert message to text suitable for embedding generation"""
        text_parts = []
        
        # Add channel context
        text_parts.append(f"Channel: {self.channel_name}")
        
        # Add user context
        text_parts.append(f"User: {self.user_name}")
        
        # Add timestamp context
        text_parts.append(f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add content type context
        if self.is_canvas:
            text_parts.append("Canvas")
            if self.canvas_title:
                text_parts.append(f"Canvas Title: {self.canvas_title}")
        elif self.thread_ts and not self.is_thread_parent:
            text_parts.append("Thread Reply")
        elif self.is_thread_parent and self.reply_count > 0:
            text_parts.append(f"Thread Parent ({self.reply_count} replies)")
        
        # Add main message text
        content_label = "Canvas Content" if self.is_canvas else "Message"
        text_parts.append(f"{content_label}: {self.text}")
        
        # Add reactions if any
        if self.reactions:
            reactions_text = ", ".join([f"{r.name}({r.count})" for r in self.reactions])
            text_parts.append(f"Reactions: {reactions_text}")
        
        return "\n".join(text_parts)
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert message to metadata for Pinecone storage"""
        return {
            "message_id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "timestamp": self.timestamp.isoformat(),
            "thread_ts": self.thread_ts if self.thread_ts else "",
            "is_thread_parent": self.is_thread_parent,
            "reply_count": self.reply_count,
            "reaction_count": len(self.reactions),
            "text_length": len(self.text),
            "is_canvas": self.is_canvas,
            "canvas_title": self.canvas_title if self.canvas_title else ""
        }

@dataclass
class SlackChannel:
    id: str
    name: str
    description: str
    member_count: int
    is_private: bool
    created: datetime

@dataclass
class IngestionLog:
    timestamp: datetime
    operation: str  # "initial_ingestion" or "hourly_refresh"
    channels_processed: int
    messages_processed: int
    embeddings_generated: int
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    success: bool = True
