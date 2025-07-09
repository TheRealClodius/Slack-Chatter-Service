#!/usr/bin/env python3
"""
Discover all Slack channels available to the bot
This script helps you find channel IDs for adding to SLACK_CHANNELS
"""

import os
import asyncio
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def discover_channels():
    """Discover all channels the bot can access"""
    
    # Get bot token from environment
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN not found in environment")
        return
    
    client = WebClient(token=bot_token)
    
    print("🔍 Discovering Slack channels...")
    print("=" * 50)
    
    try:
        # Get all channels (public and private)
        response = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=1000
        )
        
        channels = response["channels"]
        print(f"Found {len(channels)} channels accessible to the bot:\n")
        
        # Current configured channels
        current_channels = os.getenv("SLACK_CHANNELS", "").split(",")
        current_channels = [ch.strip() for ch in current_channels if ch.strip()]
        
        print("📋 Channel List:")
        print("-" * 60)
        
        for channel in channels:
            channel_id = channel["id"]
            channel_name = channel["name"]
            is_private = channel.get("is_private", False)
            member_count = channel.get("num_members", 0)
            
            # Check if currently configured
            status = "✅ CONFIGURED" if channel_id in current_channels else "⚪ AVAILABLE"
            privacy = "🔒 Private" if is_private else "🌐 Public"
            
            print(f"{status} | {privacy} | {channel_name} ({channel_id}) - {member_count} members")
        
        print("\n" + "=" * 60)
        print("📝 To add channels, update your SLACK_CHANNELS environment variable:")
        print("SLACK_CHANNELS=" + ",".join([ch["id"] for ch in channels]))
        
        # Show suggested additions
        available_channels = [ch["id"] for ch in channels if ch["id"] not in current_channels]
        if available_channels:
            print(f"\n🆕 Available channels to add: {len(available_channels)}")
            print("Suggested additions:")
            for channel in channels:
                if channel["id"] in available_channels:
                    print(f"  - {channel['name']} ({channel['id']})")
        
    except SlackApiError as e:
        print(f"❌ Error discovering channels: {e}")
        print("Make sure your bot has the following scopes:")
        print("  - channels:read")
        print("  - groups:read")
        print("  - im:read")
        print("  - mpim:read")

if __name__ == "__main__":
    discover_channels()