"""
Slack Message Ingestion Service
Handles fetching messages from Slack API with endpoint-specific rate limiting and retry handling
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from lib.config import config
from lib.data_models import SlackMessage, SlackChannel, SlackUser, SlackReaction
from lib.rate_limiter import rate_limiter
from lib.utils import SlackTextCleaner

class SlackIngester:
    def __init__(self):
        self.client = WebClient(token=config.slack_bot_token)
        # TTL-based caching: (data, timestamp)
        self.users_cache: Dict[str, Tuple[SlackUser, datetime]] = {}
        self.channels_cache: Dict[str, Tuple[SlackChannel, datetime]] = {}
        # Text cleaner for processing messages
        self.text_cleaner = SlackTextCleaner(self.client)
    
    def _is_cache_valid(self, cached_time: datetime, ttl_hours: int) -> bool:
        """Check if cached data is still valid"""
        return datetime.now(timezone.utc) - cached_time < timedelta(hours=ttl_hours)
    
    def _cleanup_expired_cache(self):
        """Remove expired entries from caches"""
        now = datetime.now(timezone.utc)
        
        # Clean users cache
        expired_users = [
            user_id for user_id, (_, timestamp) in self.users_cache.items()
            if not self._is_cache_valid(timestamp, config.cache_users_hours)
        ]
        for user_id in expired_users:
            del self.users_cache[user_id]
        
        # Clean channels cache
        expired_channels = [
            channel_id for channel_id, (_, timestamp) in self.channels_cache.items()
            if not self._is_cache_valid(timestamp, config.cache_channels_hours)
        ]
        for channel_id in expired_channels:
            del self.channels_cache[channel_id]
        
        if expired_users or expired_channels:
            print(f"Cleaned up {len(expired_users)} expired users and {len(expired_channels)} expired channels from cache")
    
    async def _make_slack_api_call(self, method_name: str, **kwargs):
        """Make a Slack API call with enhanced rate limiting and error handling"""
        # Get the method from the client
        method = getattr(self.client, method_name)
        
        # Apply the enhanced rate limiting decorator
        rate_limited_method = rate_limiter.make_slack_api_call_rate_limited(method)
        
        # Make the call with comprehensive error handling
        return await rate_limited_method(**kwargs)
    
    async def get_channels_info(self) -> List[SlackChannel]:
        """Get information about configured channels"""
        channels = []
        
        for channel_id in config.slack_channels:
            try:
                response = await self._make_slack_api_call("conversations_info", channel=channel_id)
                channel_data = response['channel']
                
                channel = SlackChannel(
                    id=channel_data['id'],
                    name=channel_data['name'],
                    description=channel_data.get('purpose', {}).get('value', ''),
                    member_count=channel_data.get('num_members', 0),
                    is_private=channel_data.get('is_private', False),
                    created=datetime.fromtimestamp(channel_data['created'], tz=timezone.utc)
                )
                
                channels.append(channel)
                self.channels_cache[channel.id] = (channel, datetime.now(timezone.utc))
                
            except SlackApiError as e:
                print(f"Error getting channel info for {channel_id}: {e}")
                continue
        
        return channels
    
    async def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get user information, with caching"""
        if user_id in self.users_cache:
            cached_user, cached_time = self.users_cache[user_id]
            if self._is_cache_valid(cached_time, config.cache_users_hours):
                return cached_user
        
        try:
            response = await self._make_slack_api_call("users_info", user=user_id)
            user_data = response['user']
            
            user = SlackUser(
                id=user_data['id'],
                name=user_data['name'],
                display_name=user_data.get('profile', {}).get('display_name', ''),
                real_name=user_data.get('profile', {}).get('real_name', ''),
                email=user_data.get('profile', {}).get('email')
            )
            
            self.users_cache[user_id] = (user, datetime.now(timezone.utc))
            return user
            
        except SlackApiError as e:
            print(f"Error getting user info for {user_id}: {e}")
            return None
    
    async def get_channel_messages(self, channel_id: str, oldest: Optional[str] = None, 
                                 latest: Optional[str] = None, limit: int = 10000) -> List[SlackMessage]:
        """Get messages from a channel with pagination - optimized for maximum efficiency"""
        all_messages = []
        cursor = None
        target_limit = limit
        
        while True:
            try:
                # Always use max 1000 per request for efficiency unless we need fewer
                batch_size = min(1000, target_limit - len(all_messages))
                if batch_size <= 0:
                    break
                
                kwargs = {
                    'channel': channel_id,
                    'limit': batch_size,
                }
                
                if oldest:
                    kwargs['oldest'] = oldest
                if latest:
                    kwargs['latest'] = latest
                if cursor:
                    kwargs['cursor'] = cursor
                
                response = await self._make_slack_api_call("conversations_history", **kwargs)
                messages = response['messages']
                
                # Process messages
                for msg_data in messages:
                    message = await self._convert_message_data(msg_data, channel_id)
                    if message:
                        all_messages.append(message)
                
                # Check for pagination
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor or len(all_messages) >= target_limit:
                    break
                    
            except SlackApiError as e:
                print(f"Error getting messages for channel {channel_id}: {e}")
                break
        
        return all_messages
    
    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[SlackMessage]:
        """Get replies in a thread"""
        replies = []
        
        try:
            response = await self._make_slack_api_call("conversations_replies", 
                                                     channel=channel_id, 
                                                     ts=thread_ts)
            
            # Skip the first message (thread parent) and process replies
            for msg_data in response['messages'][1:]:
                reply = await self._convert_message_data(msg_data, channel_id)
                if reply:
                    replies.append(reply)
                    
        except SlackApiError as e:
            print(f"Error getting thread replies for {thread_ts}: {e}")
        
        return replies
    
    async def _convert_message_data(self, msg_data: Dict, channel_id: str) -> Optional[SlackMessage]:
        """Convert Slack API message data to SlackMessage object"""
        # Check for rich content types first
        rich_content = await self._extract_rich_content(msg_data, channel_id)
        if rich_content:
            return rich_content
            
        # Skip messages without text or from bots
        if not msg_data.get('text') or msg_data.get('subtype') == 'bot_message':
            return None
        
        user_id = msg_data.get('user')
        if not user_id:
            return None
        
        # Get user info
        user = await self.get_user_info(user_id)
        if not user:
            return None
        
        # Get channel info
        channel = self.channels_cache.get(channel_id)
        channel_name = channel[0].name if channel else channel_id
        
        # Convert timestamp
        timestamp = datetime.fromtimestamp(float(msg_data['ts']), tz=timezone.utc)
        
        # Clean and process the message text
        raw_text = msg_data['text']
        cleaned_text = await self.text_cleaner.index_clean(raw_text)
        
        # Process reactions
        reactions = []
        for reaction_data in msg_data.get('reactions', []):
            # Resolve user IDs to usernames for reactions
            user_names = []
            for user_id in reaction_data.get('users', []):
                user_info = await self.get_user_info(user_id)
                user_names.append(user_info.name if user_info else user_id)
            
            reaction = SlackReaction(
                name=reaction_data['name'],
                count=reaction_data['count'],
                users=reaction_data['users'],
                user_names=user_names
            )
            reactions.append(reaction)
        
        # Create message
        message = SlackMessage(
            id=msg_data['ts'],
            text=cleaned_text,
            user_id=user_id,
            user_name=user.name,
            channel_id=channel_id,
            channel_name=channel_name,
            timestamp=timestamp,
            thread_ts=msg_data.get('thread_ts'),
            reply_count=msg_data.get('reply_count', 0),
            reactions=reactions,
            is_thread_parent=bool(msg_data.get('reply_count', 0) > 0 and not msg_data.get('thread_ts')),
            content_type="message"
        )
        
        return message
    
    async def get_all_messages_since(self, since_timestamp: Optional[datetime] = None) -> List[SlackMessage]:
        """Get all messages from all configured channels since a given timestamp"""
        all_messages = []
        oldest = str(since_timestamp.timestamp()) if since_timestamp else None
        
        # Clean up expired cache entries first
        self._cleanup_expired_cache()
        
        # First get channel info
        await self.get_channels_info()
        
        for channel_id in config.slack_channels:
            print(f"Ingesting messages from channel {channel_id}")
            
            try:
                # Get channel messages
                messages = await self.get_channel_messages(channel_id, oldest=oldest)
                
                # Create a set to track which messages are thread replies
                thread_reply_ids = set()
                
                # For each message that has replies, get the thread
                for message in messages:
                    if message.is_thread_parent and message.reply_count > 0:
                        try:
                            thread_replies = await self.get_thread_replies(channel_id, message.id)
                            message.thread_replies = thread_replies
                            # Track thread reply IDs to avoid duplicates
                            for reply in thread_replies:
                                thread_reply_ids.add(reply.id)
                        except Exception as e:
                            print(f"Error getting thread replies for {message.id}: {e}")
                
                # Filter out thread replies from main message list (they're nested under parents)
                top_level_messages = [msg for msg in messages if msg.id not in thread_reply_ids]
                
                # Get canvas content for the channel
                canvas_messages = await self.get_channel_canvas_content(channel_id)
                all_messages.extend(canvas_messages)
                
                all_messages.extend(top_level_messages)
                
                total_thread_replies = sum(len(msg.thread_replies) for msg in top_level_messages)
                print(f"Successfully processed {len(top_level_messages)} top-level messages, {total_thread_replies} thread replies, and {len(canvas_messages)} canvas items from {channel_id}")
                
            except Exception as e:
                print(f"Error processing channel {channel_id}: {e}")
                print(f"Skipping channel {channel_id} and continuing...")
                continue
            
            # Add a small delay between channels to be respectful
            await asyncio.sleep(1)
        
        # Sort messages chronologically
        all_messages.sort(key=lambda m: m.timestamp)
        
        return all_messages
    
    async def get_latest_message_timestamp(self, channel_id: str) -> Optional[datetime]:
        """Get the timestamp of the latest message in a channel"""
        try:
            response = await self._make_slack_api_call("conversations_history", 
                                                     channel=channel_id, 
                                                     limit=1)
            
            if response['messages']:
                latest_ts = response['messages'][0]['ts']
                return datetime.fromtimestamp(float(latest_ts), tz=timezone.utc)
                
        except SlackApiError as e:
            print(f"Error getting latest message timestamp for {channel_id}: {e}")
        
        return None
    
    async def get_channel_canvas_content(self, channel_id: str) -> List[SlackMessage]:
        """Extract canvas content from a channel"""
        canvas_messages = []
        
        try:
            # Get channel info to find canvas files
            response = await self._make_slack_api_call("conversations_info", channel=channel_id)
            channel_data = response.get('channel', {})
            
            # Check if channel has canvas in properties
            properties = channel_data.get('properties', {})
            canvas_info = properties.get('canvas', {})
            
            if canvas_info and canvas_info.get('file_id'):
                canvas_file_id = canvas_info['file_id']
                
                # Get canvas file info
                try:
                    file_response = await self._make_slack_api_call("files_info", file=canvas_file_id)
                    file_data = file_response.get('file', {})
                    
                    # Extract canvas content
                    canvas_content = await self._extract_canvas_content(file_data)
                    
                    if canvas_content:
                        # Get creator user info
                        creator_user_id = file_data.get('user', '')
                        creator_user = await self.get_user_info(creator_user_id) if creator_user_id else None
                        creator_name = creator_user.name if creator_user else 'Canvas'
                        
                        # Create a message object for the canvas content
                        canvas_message = SlackMessage(
                            id=f"canvas_{canvas_file_id}",
                            text=canvas_content,
                            user_id=creator_user_id,
                            user_name=creator_name,
                            channel_id=channel_id,
                            channel_name=channel_data.get('name', channel_id),
                            timestamp=datetime.fromtimestamp(file_data.get('created', 0), tz=timezone.utc),
                            is_canvas=True,
                            canvas_title=file_data.get('title', 'Canvas'),
                            content_type="canvas",
                            file_info=file_data
                        )
                        
                        canvas_messages.append(canvas_message)
                        print(f"Successfully extracted canvas content: {file_data.get('title', 'Untitled')}")
                    
                except Exception as e:
                    print(f"Error extracting canvas {canvas_file_id}: {e}")
                    
        except Exception as e:
            print(f"Error getting canvas content for channel {channel_id}: {e}")
            
        return canvas_messages
    
    async def _extract_canvas_content(self, file_data: Dict) -> str:
        """Extract text content from canvas file data"""
        content_parts = []
        
        # Add canvas title
        title = file_data.get('title', '')
        if title:
            content_parts.append(f"Canvas Title: {title}")
        
        # Extract text from title_blocks (rich text content)
        title_blocks = file_data.get('title_blocks', [])
        for block in title_blocks:
            if block.get('type') == 'rich_text':
                for element in block.get('elements', []):
                    if element.get('type') == 'rich_text_section':
                        for text_element in element.get('elements', []):
                            if text_element.get('type') == 'text':
                                content_parts.append(text_element.get('text', ''))
        
        # Add basic file info
        if file_data.get('size'):
            content_parts.append(f"Canvas size: {file_data['size']} bytes")
        
        if file_data.get('canvas_readtime'):
            read_time = file_data['canvas_readtime']
            content_parts.append(f"Estimated read time: {read_time:.1f} minutes")
        
        # Add editor information (resolve user IDs to names)
        editors = file_data.get('editors', [])
        if editors:
            editor_names = []
            for editor_id in editors:
                editor_user = await self.get_user_info(editor_id)
                editor_name = f"@{editor_user.name}" if editor_user else editor_id
                editor_names.append(editor_name)
            content_parts.append(f"Editors: {', '.join(editor_names)}")
        
        return "\n".join(content_parts)
    
    async def _extract_rich_content(self, msg_data: Dict, channel_id: str) -> Optional[SlackMessage]:
        """Extract rich content types like lists, workflows, posts, and files"""
        # Check for file attachments
        files = msg_data.get('files', [])
        
        for file_data in files:
            file_type = file_data.get('filetype', '')
            subtype = file_data.get('subtype', '')
            mimetype = file_data.get('mimetype', '')
            
            # Handle different rich content types
            content_type = "file"
            content_text = ""
            
            # Slack Lists
            if subtype == "slack_list" or file_type == "slack_list":
                content_type = "list"
                content_text = await self._extract_list_content(file_data)
            
            # Slack Workflows  
            elif subtype == "workflow" or file_type == "workflow":
                content_type = "workflow"
                content_text = await self._extract_workflow_content(file_data)
            
            # Slack Posts
            elif subtype == "post" or file_type == "post":
                content_type = "post"
                content_text = await self._extract_post_content(file_data)
            
            # Text files and documents
            elif file_type in ["text", "plain", "markdown", "txt", "md"]:
                content_type = "file"
                content_text = await self._extract_text_file_content(file_data)
            
            # Code files
            elif file_type in ["python", "javascript", "java", "cpp", "go", "rust", "php", "ruby"]:
                content_type = "file"
                content_text = await self._extract_code_file_content(file_data)
                
            # Skip if no meaningful content
            if not content_text or len(content_text.strip()) < 10:
                continue
            
            # Get user info
            user_id = msg_data.get('user', file_data.get('user', ''))
            user = await self.get_user_info(user_id) if user_id else None
            user_name = user.name if user else 'Unknown'
            
            # Get channel info
            channel = self.channels_cache.get(channel_id)
            channel_name = channel[0].name if channel else channel_id
            
            # Create rich content message
            timestamp = datetime.fromtimestamp(float(msg_data.get('ts', file_data.get('created', 0))), tz=timezone.utc)
            
            rich_message = SlackMessage(
                id=f"{content_type}_{file_data.get('id', msg_data.get('ts', ''))}",
                text=content_text,
                user_id=user_id,
                user_name=user_name,
                channel_id=channel_id,
                channel_name=channel_name,
                timestamp=timestamp,
                thread_ts=msg_data.get('thread_ts'),
                content_type=content_type,
                file_info=file_data
            )
            
            return rich_message
        
        return None
    
    async def _extract_list_content(self, file_data: Dict) -> str:
        """Extract content from Slack lists"""
        content_parts = []
        
        # Add list title
        title = file_data.get('title', file_data.get('name', ''))
        if title:
            content_parts.append(f"List Title: {title}")
        
        # Extract list items from preview or content
        preview = file_data.get('preview', '')
        if preview:
            content_parts.append(f"List Items:\n{preview}")
        
        # Add list metadata
        if file_data.get('size'):
            content_parts.append(f"List size: {file_data['size']} bytes")
            
        return "\n".join(content_parts)
    
    async def _extract_workflow_content(self, file_data: Dict) -> str:
        """Extract content from Slack workflows"""
        content_parts = []
        
        # Add workflow title
        title = file_data.get('title', file_data.get('name', ''))
        if title:
            content_parts.append(f"Workflow Title: {title}")
        
        # Extract workflow description from preview
        preview = file_data.get('preview', '')
        if preview:
            content_parts.append(f"Workflow Description:\n{preview}")
        
        # Add workflow metadata
        if file_data.get('app_name'):
            content_parts.append(f"App: {file_data['app_name']}")
            
        return "\n".join(content_parts)
    
    async def _extract_post_content(self, file_data: Dict) -> str:
        """Extract content from Slack posts"""
        content_parts = []
        
        # Add post title
        title = file_data.get('title', file_data.get('name', ''))
        if title:
            content_parts.append(f"Post Title: {title}")
        
        # Extract post content from preview
        preview = file_data.get('preview', '')
        if preview:
            content_parts.append(f"Post Content:\n{preview}")
        
        # Add post metadata
        if file_data.get('size'):
            content_parts.append(f"Post size: {file_data['size']} bytes")
            
        return "\n".join(content_parts)
    
    async def _extract_text_file_content(self, file_data: Dict) -> str:
        """Extract content from text files"""
        content_parts = []
        
        # Add file title
        title = file_data.get('title', file_data.get('name', ''))
        if title:
            content_parts.append(f"File: {title}")
        
        # Extract file content from preview
        preview = file_data.get('preview', '')
        if preview:
            content_parts.append(f"Content:\n{preview}")
        
        # Add file metadata
        if file_data.get('filetype'):
            content_parts.append(f"File type: {file_data['filetype']}")
        if file_data.get('size'):
            content_parts.append(f"Size: {file_data['size']} bytes")
            
        return "\n".join(content_parts)
    
    async def _extract_code_file_content(self, file_data: Dict) -> str:
        """Extract content from code files"""
        content_parts = []
        
        # Add file title
        title = file_data.get('title', file_data.get('name', ''))
        if title:
            content_parts.append(f"Code File: {title}")
        
        # Extract code content from preview
        preview = file_data.get('preview', '')
        if preview:
            content_parts.append(f"Code:\n{preview}")
        
        # Add code metadata
        if file_data.get('filetype'):
            content_parts.append(f"Language: {file_data['filetype']}")
        if file_data.get('lines'):
            content_parts.append(f"Lines: {file_data['lines']}")
        if file_data.get('size'):
            content_parts.append(f"Size: {file_data['size']} bytes")
            
        return "\n".join(content_parts) 