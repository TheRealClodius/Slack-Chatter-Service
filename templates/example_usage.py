#!/usr/bin/env python3
"""
Simple Example: Using Slack Search Tool Client

This example shows how to use the SlackSearchTool client template
to integrate Slack message search into your application.

Prerequisites:
1. Slack Chatter MCP server must be running
2. Environment variables must be configured
3. Data must be ingested into the search index
"""

import asyncio
import logging
from slack_search_tool import SlackSearchTool, YourApplicationService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_search_example():
    """Basic example: Direct search functionality"""
    print("🔍 Basic Search Example")
    print("=" * 50)
    
    # Initialize the search tool
    search_tool = SlackSearchTool([
        "python", "../main_orchestrator.py", "mcp"  # Adjust path as needed
    ])
    
    try:
        # Connect to the MCP server
        await search_tool.connect()
        print("✅ Connected to Slack search service")
        
        # Get basic information
        channels = await search_tool.get_available_channels()
        print(f"📁 Available channels: {', '.join(channels)}")
        
        stats = await search_tool.get_search_stats()
        print(f"📊 Index contains {stats['total_messages']} messages")
        
        # Perform some searches
        search_queries = [
            "authentication issues",
            "database migration",
            "deployment problems",
            "API design decisions"
        ]
        
        for query in search_queries:
            print(f"\n🔎 Searching for: '{query}'")
            results = await search_tool.search_slack_messages(query, top_k=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"  {i}. @{result.user} in #{result.channel}")
                    print(f"     {result.text[:100]}...")
                    print(f"     Score: {result.relevance_score:.2f}")
            else:
                print("  No results found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await search_tool.disconnect()
        print("👋 Disconnected from search service")


async def smart_search_example():
    """Smart search example: Using the intelligent search wrapper"""
    print("\n🤖 Smart Search Example")
    print("=" * 50)
    
    search_tool = SlackSearchTool([
        "python", "../main_orchestrator.py", "mcp"
    ])
    
    try:
        await search_tool.connect()
        
        # Test questions that would benefit from Slack search
        questions = [
            "What did the team decide about the new API?",
            "How did we solve the authentication problem?",
            "Who was working on the database migration?",
            "What are the current deployment issues?",
            "What's our stance on using GraphQL?"
        ]
        
        for question in questions:
            print(f"\n❓ Question: {question}")
            response = await search_tool.smart_search(question)
            print(f"💬 Response: {response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await search_tool.disconnect()


async def filtered_search_example():
    """Example showing how to use search filters"""
    print("\n🎯 Filtered Search Example")
    print("=" * 50)
    
    search_tool = SlackSearchTool([
        "python", "../main_orchestrator.py", "mcp"
    ])
    
    try:
        await search_tool.connect()
        
        # Search with user filter
        print("🔍 Searching for messages from specific user...")
        results = await search_tool.search_slack_messages(
            "deployment",
            top_k=5,
            user_filter="john_doe"  # Adjust to actual username
        )
        print(f"Found {len(results)} messages from john_doe about deployment")
        
        # Search with channel filter
        print("\n🔍 Searching in specific channel...")
        results = await search_tool.search_slack_messages(
            "bug",
            top_k=5,
            channel_filter="dev-team"  # Adjust to actual channel
        )
        print(f"Found {len(results)} messages about bugs in #dev-team")
        
        # Search with date filter
        print("\n🔍 Searching recent messages...")
        results = await search_tool.search_slack_messages(
            "production issue",
            top_k=5,
            date_from="2024-01-01"  # Adjust date as needed
        )
        print(f"Found {len(results)} recent messages about production issues")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await search_tool.disconnect()


async def application_integration_example():
    """Example of integrating into a larger application"""
    print("\n🏗️ Application Integration Example")
    print("=" * 50)
    
    # This would be your main application service
    app_service = YourApplicationService()
    
    try:
        await app_service.initialize()
        print("✅ Application service initialized")
        
        # Simulate user queries to your application
        user_queries = [
            "Tell me about recent deployment issues",
            "What's the weather like?",  # Non-Slack query
            "Who discussed the API redesign?",
            "How do I reset my password?",  # Non-Slack query
            "What problems did we have with the database migration?"
        ]
        
        for query in user_queries:
            print(f"\n👤 User: {query}")
            response = await app_service.handle_user_query(query)
            print(f"🤖 Assistant: {response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await app_service.cleanup()


async def performance_test_example():
    """Example showing performance testing"""
    print("\n⚡ Performance Test Example")
    print("=" * 50)
    
    search_tool = SlackSearchTool([
        "python", "../main_orchestrator.py", "mcp"
    ])
    
    try:
        await search_tool.connect()
        
        import time
        
        # Test multiple searches for performance
        test_queries = [
            "error", "deployment", "authentication", "database", "API",
            "bug", "feature", "production", "staging", "configuration"
        ]
        
        total_time = 0
        for query in test_queries:
            start_time = time.time()
            results = await search_tool.search_slack_messages(query, top_k=5)
            duration = time.time() - start_time
            total_time += duration
            
            print(f"Query '{query}': {len(results)} results in {duration:.2f}s")
        
        avg_time = total_time / len(test_queries)
        print(f"\n📊 Average search time: {avg_time:.2f}s")
        print(f"📊 Total time for {len(test_queries)} searches: {total_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await search_tool.disconnect()


async def main():
    """Run all examples"""
    print("🚀 Slack Search Tool Client Examples")
    print("=" * 60)
    
    # Check if MCP server is accessible
    try:
        search_tool = SlackSearchTool([
            "python", "../main_orchestrator.py", "mcp"
        ])
        await search_tool.connect()
        await search_tool.disconnect()
        print("✅ MCP server is accessible")
    except Exception as e:
        print(f"❌ Cannot connect to MCP server: {e}")
        print("   Make sure the Slack Chatter service is running:")
        print("   python main_orchestrator.py mcp")
        return
    
    # Run examples
    try:
        await basic_search_example()
        await smart_search_example()
        await filtered_search_example()
        await application_integration_example()
        await performance_test_example()
        
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Examples completed!")


if __name__ == "__main__":
    asyncio.run(main()) 