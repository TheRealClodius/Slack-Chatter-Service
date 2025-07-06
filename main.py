import asyncio
import signal
import sys
from datetime import datetime

from scheduler import SlackWorkerScheduler
from config import config

class SlackWorker:
    def __init__(self):
        self.scheduler = SlackWorkerScheduler()
        self.running = False
    
    async def start(self):
        """Start the background worker"""
        print("=" * 60)
        print("🚀 Slack Message Ingestion Worker Starting")
        print("=" * 60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📺 Monitoring {len(config.slack_channels)} Slack channel(s)")
        print(f"🔄 Refresh interval: {config.refresh_interval_hours} hour(s)")
        print("=" * 60)
        
        # Validate configuration
        try:
            config._validate_config()
            print("✅ Configuration validated")
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            print("\nRequired environment variables:")
            print("- SLACK_BOT_TOKEN: Your Slack Bot Token")
            print("- SLACK_CHANNELS: Comma-separated list of channel IDs")
            print("- OPENAI_API_KEY: Your OpenAI API key")
            print("- PINECONE_API_KEY: Your Pinecone API key")
            print("- PINECONE_ENVIRONMENT: Your Pinecone environment")
            print("- PINECONE_INDEX_NAME: Name for your Pinecone index")
            print("- NOTION_INTEGRATION_SECRET: Your Notion integration secret")
            print("- NOTION_DATABASE_ID: Your Notion database ID")
            print("\nFor Notion setup instructions:")
            print("1. Go to https://www.notion.so/my-integrations")
            print("2. Create a new integration")
            print("3. Copy the integration secret")
            print("4. Create a database in Notion with these columns:")
            print("   - Timestamp (Date)")
            print("   - Operation (Select)")
            print("   - Channels Processed (Number)")
            print("   - Messages Processed (Number)")
            print("   - Embeddings Generated (Number)")
            print("   - Duration (seconds) (Number)")
            print("   - Success (Checkbox)")
            print("   - Errors (Text)")
            print("5. Share the database with your integration")
            print("6. Copy the database ID from the URL")
            sys.exit(1)
        
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
        
        try:
            # Start the scheduler
            await self.scheduler.start()
            
            # Keep the worker running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        except Exception as e:
            print(f"❌ Worker error: {e}")
        finally:
            await self.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}")
        self.running = False
    
    async def stop(self):
        """Stop the worker gracefully"""
        print("🔄 Shutting down worker...")
        await self.scheduler.stop()
        print("✅ Worker stopped successfully")

async def main():
    """Main entry point"""
    worker = SlackWorker()
    await worker.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
