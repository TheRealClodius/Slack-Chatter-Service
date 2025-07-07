from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from lib.rate_limiter import rate_limiter

def chunk_text(text: str, max_chunk_size: int, chunk_overlap: int = 0) -> List[str]:
    """Split text into chunks with optional overlap"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # If this isn't the last chunk, try to break at a word boundary
        if end < len(text):
            # Look for the last space within the chunk
            last_space = text.rfind(' ', start, end)
            if last_space > start:
                end = last_space
        
        chunks.append(text[start:end])
        
        # Move start position, accounting for overlap
        start = end - chunk_overlap
        if start <= 0:
            start = end
    
    return chunks

def save_state(state: Dict[str, Any], filename: str) -> None:
    """Save state to a JSON file"""
    try:
        state_file = Path(filename)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving state to {filename}: {e}")

def load_state(filename: str) -> Dict[str, Any]:
    """Load state from a JSON file"""
    try:
        state_file = Path(filename)
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading state from {filename}: {e}")
    return {}

def get_current_utc_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def sanitize_log_data(data: str, max_length: int = 100) -> str:
    """
    Sanitize data for logging to prevent log injection
    
    Args:
        data: Data to sanitize
        max_length: Maximum length of sanitized data
        
    Returns:
        Sanitized data safe for logging
    """
    if not data:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = ''.join(c for c in data if c.isprintable() and c not in ['\n', '\r', '\t'])
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized

class SlackTextCleaner:
    """
    Utility class to clean and process Slack message text
    Based on the danswer implementation with enhancements
    """
    
    def __init__(self, client: WebClient):
        self.client = client
        self._id_to_name_map: Dict[str, str] = {}
    
    async def _get_slack_name(self, user_id: str) -> str:
        """Get Slack user name with caching"""
        if user_id not in self._id_to_name_map:
            try:
                # Use the enhanced rate limiter
                rate_limited_call = rate_limiter.make_slack_api_call_rate_limited(
                    self.client.users_info
                )
                response = await rate_limited_call(user=user_id)
                
                user_data = response["user"]
                profile = user_data.get("profile", {})
                
                # Prefer display name if set, since that's what's shown in Slack
                name = (
                    profile.get("display_name") or 
                    profile.get("real_name") or 
                    user_data.get("name") or 
                    user_id
                )
                
                self._id_to_name_map[user_id] = name
                
            except SlackApiError as e:
                print(f"Error fetching data for user {user_id}: {e}")
                self._id_to_name_map[user_id] = user_id  # Fallback to user ID
        
        return self._id_to_name_map[user_id]
    
    async def _replace_user_ids_with_names(self, message: str) -> str:
        """Replace user IDs with actual usernames"""
        # Find user IDs in the message
        user_ids = re.findall(r"<@(.*?)>", message)
        
        # Replace each user ID with username
        for user_id in user_ids:
            try:
                user_name = await self._get_slack_name(user_id)
                message = message.replace(f"<@{user_id}>", f"@{user_name}")
            except Exception as e:
                print(f"Unable to replace user ID {user_id} with username: {e}")
        
        return message
    
    async def index_clean(self, message: str) -> str:
        """
        Clean message text for indexing/embedding
        Replaces patterns that may cause confusion while preserving information
        """
        message = await self._replace_user_ids_with_names(message)
        message = self.replace_tags_basic(message)
        message = self.replace_channels_basic(message)
        message = self.replace_special_mentions(message)
        message = self.replace_special_catchall(message)
        return message
    
    async def display_clean(self, message: str) -> str:
        """
        Clean message text for display purposes
        More aggressive cleaning to prevent Slack interactions
        """
        message = await self._replace_user_ids_with_names(message)
        message = self.replace_tags_basic(message)
        message = self.replace_channels_basic(message)
        message = self.replace_special_mentions(message)
        message = self.replace_links(message)
        message = self.replace_special_catchall(message)
        message = self.add_zero_width_whitespace_after_tag(message)
        message = self.handle_bold_syntax_for_slack(message)
        return message
    
    @staticmethod
    def replace_tags_basic(message: str) -> str:
        """Replace user tags with basic format to prevent tagging"""
        user_ids = re.findall(r"<@(.*?)>", message)
        for user_id in user_ids:
            message = message.replace(f"<@{user_id}>", f"@{user_id}")
        return message
    
    @staticmethod
    def replace_channels_basic(message: str) -> str:
        """Replace channel mentions with basic format"""
        channel_matches = re.findall(r"<#(.*?)\|(.*?)>", message)
        for channel_id, channel_name in channel_matches:
            message = message.replace(
                f"<#{channel_id}|{channel_name}>", f"#{channel_name}"
            )
        return message
    
    @staticmethod
    def replace_special_mentions(message: str) -> str:
        """Replace special mentions (@channel, @here, @everyone)"""
        message = message.replace("<!channel>", "@channel")
        message = message.replace("<!here>", "@here")
        message = message.replace("<!everyone>", "@everyone")
        return message
    
    @staticmethod
    def replace_links(message: str) -> str:
        """Replace Slack links with display text"""
        possible_link_matches = re.findall(r"<(.*?)>", message)
        for possible_link in possible_link_matches:
            if not possible_link:
                continue
            # Skip special Slack patterns that aren't links
            if possible_link[0] not in ["#", "@", "!"]:
                link_display = (
                    possible_link
                    if "|" not in possible_link
                    else possible_link.split("|")[1]
                )
                message = message.replace(f"<{possible_link}>", link_display)
        return message
    
    @staticmethod
    def replace_special_catchall(message: str) -> str:
        """Replace special pattern <!something|another-thing> with another-thing"""
        pattern = r"<!([^|]+)\|([^>]+)>"
        return re.sub(pattern, r"\2", message)
    
    @staticmethod
    def add_zero_width_whitespace_after_tag(message: str) -> str:
        """Add zero-width whitespace after @ to prevent tagging"""
        return message.replace("@", "@\u200B")
    
    @staticmethod
    def handle_bold_syntax_for_slack(message: str) -> str:
        """Replace double asterisks with single asterisks for Slack formatting"""
        return message.replace("**", "*")

def get_message_link(
    event: Dict[str, Any], workspace: str, channel_id: Optional[str] = None
) -> str:
    """
    Generate a Slack message link
    Based on danswer's implementation
    """
    channel_id = channel_id or event["channel"]
    message_ts = event["ts"]
    message_ts_without_dot = message_ts.replace(".", "")
    thread_ts = event.get("thread_ts")
    
    link = f"https://{workspace}.slack.com/archives/{channel_id}/p{message_ts_without_dot}"
    if thread_ts:
        link += f"?thread_ts={thread_ts}"
    
    return link

async def get_slack_message_permalink(
    channel: str, message_ts: str, client: WebClient
) -> str:
    """
    Get a direct permalink to a Slack message
    """
    try:
        rate_limited_call = rate_limiter.make_slack_api_call_rate_limited(
            client.chat_getPermalink
        )
        response = await rate_limited_call(channel=channel, message_ts=message_ts)
        
        if response["ok"]:
            return response["permalink"]
        else:
            print(f"Failed to get permalink: {response.get('error')}")
            return ""
    except Exception as e:
        print(f"Failed to get Slack message permalink: {str(e)}")
        return ""

def replace_whitespaces_w_space(text: str) -> str:
    """Replace multiple whitespaces with single space"""
    return re.sub(r'\s+', ' ', text).strip()

def translate_vespa_highlight_to_slack(match_strs: List[str], used_chars: int) -> str:
    """
    Translate search result highlights for Slack display
    Based on danswer's implementation
    """
    def _replace_highlight(s: str) -> str:
        # Handle highlights that don't have leading space
        s = re.sub(r"(?<=[^\s])<hi>(.*?)</hi>", r"\1", s)
        # Replace highlight tags with Slack bold formatting
        s = s.replace("</hi>", "*").replace("<hi>", "*")
        return s
    
    final_matches = [
        replace_whitespaces_w_space(_replace_highlight(match_str)).strip()
        for match_str in match_strs
        if match_str
    ]
    combined = "... ".join(final_matches)
    
    # Slack shows "Show More" after 300 chars on desktop
    # Don't trim if there's still a highlight after 300 chars
    remaining = 300 - used_chars
    if len(combined) > remaining and "*" not in combined[remaining:]:
        combined = combined[:remaining - 3] + "..."
    
    return combined
