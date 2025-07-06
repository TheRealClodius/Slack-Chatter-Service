#!/usr/bin/env python3
"""
Verification script to check what messages were ingested into Pinecone.
This helps verify that the ingestion process captured messages correctly,
including checking date ranges and channel coverage.
"""

import asyncio
from datetime import datetime
from collections import defaultdict
from pinecone_service import PineconeService

async def verify_ingestion():
    """Verify what messages were actually ingested"""
    
    print("🔍 Checking ingested messages in Pinecone...")
    print("=" * 60)
    
    # Initialize Pinecone service
    pinecone_service = PineconeService()
    
    # Get index statistics
    stats = pinecone_service.get_index_stats()
    print(f"📊 Index Statistics:")
    print(f"   Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"   Dimension: {stats.get('dimension', 0)}")
    print(f"   Index fullness: {stats.get('index_fullness', 0.0):.2%}")
    print()
    
    if stats.get('total_vector_count', 0) == 0:
        print("❌ No vectors found in index")
        return
    
    # Query all vectors to see what we have
    print("🔍 Sampling stored messages...")
    
    # Create a dummy query vector to fetch some results
    dummy_vector = [0.0] * 1536  # text-embedding-3-small dimension
    
    # Query for messages
    results = await pinecone_service.query_similar(
        query_embedding=dummy_vector, 
        top_k=100  # Get more results to see the full scope
    )
    
    if not results:
        print("❌ No results returned from query")
        return
    
    print(f"📝 Found {len(results)} message chunks")
    print()
    
    # Analyze the results
    channels = defaultdict(int)
    users = defaultdict(int)
    dates = []
    autopilot_messages = []
    
    for result in results:
        metadata = result.get('metadata', {})
        
        # Extract info
        channel_name = metadata.get('channel_name', 'Unknown')
        user_name = metadata.get('user_name', 'Unknown')
        timestamp = metadata.get('timestamp', '')
        text = metadata.get('text', '')
        
        channels[channel_name] += 1
        users[user_name] += 1
        
        if timestamp:
            try:
                date_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                dates.append(date_obj)
                
                # Check for autopilot-design-process channel and January 2025
                if 'autopilot' in channel_name.lower() and date_obj.year == 2025 and date_obj.month == 1:
                    autopilot_messages.append({
                        'date': date_obj,
                        'user': user_name,
                        'text': text[:100] + '...' if len(text) > 100 else text
                    })
                    
            except Exception as e:
                print(f"⚠️  Error parsing timestamp {timestamp}: {e}")
    
    # Display channel breakdown
    print("📺 Messages by Channel:")
    for channel, count in sorted(channels.items()):
        print(f"   {channel}: {count} chunks")
    print()
    
    # Display date range
    if dates:
        dates.sort()
        earliest = dates[0]
        latest = dates[-1]
        print("📅 Date Range:")
        print(f"   Earliest: {earliest.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Latest: {latest.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check for January 2025 messages specifically
        jan_2025_messages = [d for d in dates if d.year == 2025 and d.month == 1]
        if jan_2025_messages:
            print(f"✅ Found {len(jan_2025_messages)} messages from January 2025")
        else:
            print("ℹ️  No messages found from January 2025")
        print()
    
    # Display autopilot-design-process messages from January 2025
    if autopilot_messages:
        print("🎯 January 2025 messages from autopilot channels:")
        for msg in sorted(autopilot_messages, key=lambda x: x['date'])[:5]:  # Show first 5
            print(f"   {msg['date'].strftime('%Y-%m-%d %H:%M')} - {msg['user']}: {msg['text']}")
        if len(autopilot_messages) > 5:
            print(f"   ... and {len(autopilot_messages) - 5} more")
        print()
    else:
        print("ℹ️  No January 2025 messages found from autopilot channels")
        print()
    
    # Display top users
    print("👥 Top Users:")
    top_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:5]
    for user, count in top_users:
        print(f"   {user}: {count} chunks")
    
    print()
    print("✅ Verification complete!")

if __name__ == "__main__":
    asyncio.run(verify_ingestion())