import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import config
from data_models import SlackMessage, SlackChannel, SlackUser, SlackReaction
from rate_limiter import rate_limiter

class SlackIngester:
    def __init__(self):
        self.client = WebClient(token=config.slack_bot_token)
        self.users_cache: Dict[str, SlackUser] = {}
        self.channels_cache: Dict[str, SlackChannel] = {}
    
    async def get_channels_info(self) -> List[SlackChannel]:
        """Get information about configured channels"""
        channels = []
        
        for channel_id in config.slack_channels:
            try:
                await rate_limiter.wait_if_needed("slack", config.slack_rate_limit_per_minute)
                
                response = self.client.conversations_info(channel=channel_id)
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
                self.channels_cache[channel.id] = channel
                
            except SlackApiError as e:
                print(f"Error getting channel info for {channel_id}: {e}")
                continue
        
        return channels
    
    async def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get user information, with caching"""
        if user_id in self.users_cache:
            return self.users_cache[user_id]
        
        try:
            await rate_limiter.wait_if_needed("slack", config.slack_rate_limit_per_minute)
            
            response = self.client.users_info(user=user_id)
            user_data = response['user']
            
            user = SlackUser(
                id=user_data['id'],
                name=user_data['name'],
                display_name=user_data.get('profile', {}).get('display_name', ''),
                real_name=user_data.get('profile', {}).get('real_name', ''),
                email=user_data.get('profile', {}).get('email')
            )
            
            self.users_cache[user_id] = user
            return user
            
        except SlackApiError as e:
            print(f"Error getting user info for {user_id}: {e}")
            return None
    
    async def get_channel_messages(self, channel_id: str, oldest: Optional[str] = None, 
                                 latest: Optional[str] = None, limit: int = 1000) -> List[SlackMessage]:
        """Get messages from a channel with pagination"""
        all_messages = []
        cursor = None
        
        while True:
            try:
                await rate_limiter.wait_if_needed("slack", config.slack_rate_limit_per_minute)
                
                kwargs = {
                    'channel': channel_id,
                    'limit': min(limit, 1000),  # Slack API max is 1000
                }
                
                if oldest:
                    kwargs['oldest'] = oldest
                if latest:
                    kwargs['latest'] = latest
                if cursor:
                    kwargs['cursor'] = cursor
                
                response = self.client.conversations_history(**kwargs)
                messages = response['messages']
                
                # Process messages
                for msg_data in messages:
                    message = await self._convert_message_data(msg_data, channel_id)
                    if message:
                        all_messages.append(message)
                
                # Check for pagination
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor or len(all_messages) >= limit:
                    break
                    
            except SlackApiError as e:
                print(f"Error getting messages for channel {channel_id}: {e}")
                break
        
        return all_messages
    
    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[SlackMessage]:
        """Get replies in a thread"""
        replies = []
        
        try:
            await rate_limiter.wait_if_needed("slack", config.slack_rate_limit_per_minute)
            
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            
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
        channel_name = channel.name if channel else channel_id
        
        # Convert timestamp
        timestamp = datetime.fromtimestamp(float(msg_data['ts']), tz=timezone.utc)
        
        # Process reactions
        reactions = []
        for reaction_data in msg_data.get('reactions', []):
            reaction = SlackReaction(
                name=reaction_data['name'],
                count=reaction_data['count'],
                users=reaction_data['users']
            )
            reactions.append(reaction)
        
        # Create message
        message = SlackMessage(
            id=msg_data['ts'],
            text=msg_data['text'],
            user_id=user_id,
            user_name=user.name,
            channel_id=channel_id,
            channel_name=channel_name,
            timestamp=timestamp,
            thread_ts=msg_data.get('thread_ts'),
            reply_count=msg_data.get('reply_count', 0),
            reactions=reactions,
            is_thread_parent=bool(msg_data.get('reply_count', 0) > 0 and not msg_data.get('thread_ts'))
        )
        
        return message
    
    async def get_all_messages_since(self, since_timestamp: Optional[datetime] = None) -> List[SlackMessage]:
        """Get all messages from all configured channels since a given timestamp"""
        all_messages = []
        oldest = str(since_timestamp.timestamp()) if since_timestamp else None
        
        # First get channel info
        await self.get_channels_info()
        
        for channel_id in config.slack_channels:
            print(f"Ingesting messages from channel {channel_id}")
            
            try:
                # Get channel messages
                messages = await self.get_channel_messages(channel_id, oldest=oldest)
                
                # For each message that has replies, get the thread
                for message in messages:
                    if message.is_thread_parent and message.reply_count > 0:
                        try:
                            thread_replies = await self.get_thread_replies(channel_id, message.id)
                            message.thread_replies = thread_replies
                        except Exception as e:
                            print(f"Error getting thread replies for {message.id}: {e}")
                
                all_messages.extend(messages)
                print(f"Successfully processed {len(messages)} messages from {channel_id}")
                
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
            await rate_limiter.wait_if_needed("slack", config.slack_rate_limit_per_minute)
            
            response = self.client.conversations_history(
                channel=channel_id,
                limit=1
            )
            
            if response['messages']:
                latest_ts = response['messages'][0]['ts']
                return datetime.fromtimestamp(float(latest_ts), tz=timezone.utc)
                
        except SlackApiError as e:
            print(f"Error getting latest message timestamp for {channel_id}: {e}")
        
        return None
