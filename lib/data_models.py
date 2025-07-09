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
    users: List[str]  # User IDs who reacted
    user_names: List[str] = field(default_factory=list)  # Resolved usernames

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
    content_type: str = "message"  # Type: message, canvas, list, workflow, post, file
    file_info: Optional[Dict[str, Any]] = None  # File metadata if applicable
    
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
        if self.content_type == "canvas":
            text_parts.append("Canvas")
            if self.canvas_title:
                text_parts.append(f"Canvas Title: {self.canvas_title}")
        elif self.content_type == "list":
            text_parts.append("List")
        elif self.content_type == "workflow":
            text_parts.append("Workflow")
        elif self.content_type == "post":
            text_parts.append("Post")
        elif self.content_type == "file":
            text_parts.append("File")
            if self.file_info:
                text_parts.append(f"File Type: {self.file_info.get('filetype', 'unknown')}")
        elif self.thread_ts and not self.is_thread_parent:
            text_parts.append("Thread Reply")
        elif self.is_thread_parent and self.reply_count > 0:
            text_parts.append(f"Thread Parent ({self.reply_count} replies)")
        
        # Add main message text
        content_labels = {
            "canvas": "Canvas Content",
            "list": "List Content", 
            "workflow": "Workflow Content",
            "post": "Post Content",
            "file": "File Content",
            "message": "Message"
        }
        content_label = content_labels.get(self.content_type, "Message")
        text_parts.append(f"{content_label}: {self.text}")
        
        # Add reactions if any
        if self.reactions:
            reactions_list = []
            for r in self.reactions:
                if r.user_names:
                    users_text = ", ".join(r.user_names[:3])  # Show first 3 users
                    if len(r.user_names) > 3:
                        users_text += f" and {len(r.user_names) - 3} others"
                    reactions_list.append(f":{r.name}: ({r.count}) by {users_text}")
                else:
                    reactions_list.append(f":{r.name}: ({r.count})")
            text_parts.append(f"Reactions: {', '.join(reactions_list)}")
        
        # Add thread replies if this is a thread parent
        if self.thread_replies:
            text_parts.append(f"\nThread Replies ({len(self.thread_replies)}):")
            for i, reply in enumerate(self.thread_replies, 1):
                text_parts.append(f"Reply {i} by {reply.user_name} at {reply.timestamp.strftime('%H:%M')}: {reply.text}")
                if reply.reactions:
                    reply_reactions_list = []
                    for r in reply.reactions:
                        if r.user_names:
                            users_text = ", ".join(r.user_names[:2])  # Show first 2 users for replies
                            if len(r.user_names) > 2:
                                users_text += f" +{len(r.user_names) - 2}"
                            reply_reactions_list.append(f":{r.name}: ({r.count}) by {users_text}")
                        else:
                            reply_reactions_list.append(f":{r.name}: ({r.count})")
                    text_parts.append(f"    Reactions: {', '.join(reply_reactions_list)}")
        
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
            "canvas_title": self.canvas_title if self.canvas_title else "",
            "content_type": self.content_type,
            "file_type": self.file_info.get('filetype', '') if self.file_info else ""
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
