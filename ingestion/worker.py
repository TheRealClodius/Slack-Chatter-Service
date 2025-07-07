"""
Dedicated Ingestion Worker for Slack Messages
Runs as a standalone background process to ingest Slack messages
"""

import asyncio
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from lib.config import config
from lib.data_models import IngestionLog
from lib.embedding_service import EmbeddingService
from lib.pinecone_service import PineconeService
from lib.notion_logger import NotionLogger
from lib.utils import get_current_utc_time, save_state, load_state, format_duration

from .slack_ingester import SlackIngester


class SlackIngestionWorker:
    """Dedicated worker for ingesting Slack messages"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.slack_ingester = SlackIngester()
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()
        self.notion_logger = NotionLogger()
        
        self.is_initial_ingestion_complete = False
        self.initial_ingestion_task = None
        self.running = False
        
        # Load previous state
        self._load_state()
    
    def _load_state(self):
        """Load worker state from file"""
        state = load_state("ingestion_state.json")
        self.is_initial_ingestion_complete = state.get('initial_ingestion_complete', False)
    
    def _save_state(self):
        """Save worker state to file"""
        state = {
            'initial_ingestion_complete': self.is_initial_ingestion_complete,
            'last_run': datetime.now().isoformat()
        }
        save_state(state, "ingestion_state.json")
    
    async def start(self):
        """Start the ingestion worker"""
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
            sys.exit(1)
        
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
        
        try:
            # Verify Notion database schema
            await self.notion_logger.create_database_schema()
            
            # Start scheduler
            self.scheduler.start()
            
            # Check if we need to do initial ingestion
            if not self.is_initial_ingestion_complete or self.pinecone_service.is_index_empty():
                print("Starting initial ingestion...")
                self.initial_ingestion_task = asyncio.create_task(self.initial_ingestion())
            else:
                print("Initial ingestion already complete, scheduling hourly refreshes")
                self._schedule_hourly_refresh()
            
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
    
    def _schedule_hourly_refresh(self):
        """Schedule hourly refresh job"""
        self.scheduler.add_job(
            self.hourly_refresh,
            trigger=IntervalTrigger(hours=config.refresh_interval_hours),
            id='hourly_refresh',
            replace_existing=True
        )
        print(f"Scheduled hourly refresh every {config.refresh_interval_hours} hour(s)")
    
    async def initial_ingestion(self):
        """Perform initial full ingestion of all messages"""
        start_time = time.time()
        log = IngestionLog(
            timestamp=get_current_utc_time(),
            operation="initial_ingestion",
            channels_processed=0,
            messages_processed=0,
            embeddings_generated=0
        )
        
        try:
            print("Starting initial ingestion of all Slack messages...")
            
            # Get all messages (no time filter for initial ingestion)
            all_messages = await self.slack_ingester.get_all_messages_since(None)
            log.messages_processed = len(all_messages)
            log.channels_processed = len(config.slack_channels)
            
            print(f"Retrieved {len(all_messages)} messages from {len(config.slack_channels)} channels")
            
            if all_messages:
                # Generate embeddings
                print("Generating embeddings...")
                embeddings_data = await self.embedding_service.generate_embeddings(all_messages)
                log.embeddings_generated = len(embeddings_data)
                
                print(f"Generated {len(embeddings_data)} embeddings")
                
                # Store in vector database
                print("Storing embeddings in vector database...")
                await self.pinecone_service.upsert_embeddings(embeddings_data)
                
                print("Initial ingestion complete!")
            
            # Mark initial ingestion as complete
            self.is_initial_ingestion_complete = True
            self._save_state()
            
            # Schedule hourly refreshes
            self._schedule_hourly_refresh()
            
            log.success = True
            
        except Exception as e:
            error_msg = f"Initial ingestion failed: {str(e)}"
            print(error_msg)
            log.errors.append(error_msg)
            log.success = False
        
        finally:
            log.duration_seconds = time.time() - start_time
            await self.notion_logger.log_ingestion(log)
            print(f"Initial ingestion completed in {format_duration(log.duration_seconds)}")
    
    async def hourly_refresh(self):
        """Perform hourly refresh of new messages"""
        start_time = time.time()
        log = IngestionLog(
            timestamp=get_current_utc_time(),
            operation="hourly_refresh",
            channels_processed=0,
            messages_processed=0,
            embeddings_generated=0
        )
        
        try:
            print("Starting hourly refresh...")
            
            # Get timestamp of last successful ingestion
            last_ingestion = await self.notion_logger.get_last_successful_ingestion()
            if not last_ingestion:
                # Fallback to 1 hour ago if no previous ingestion found
                last_ingestion = get_current_utc_time() - timedelta(hours=1)
            
            print(f"Getting messages since {last_ingestion}")
            
            # Get new messages since last ingestion
            new_messages = await self.slack_ingester.get_all_messages_since(last_ingestion)
            log.messages_processed = len(new_messages)
            log.channels_processed = len(config.slack_channels)
            
            print(f"Retrieved {len(new_messages)} new messages")
            
            if new_messages:
                # Generate embeddings
                embeddings_data = await self.embedding_service.generate_embeddings(new_messages)
                log.embeddings_generated = len(embeddings_data)
                
                # Store in vector database
                await self.pinecone_service.upsert_embeddings(embeddings_data)
                
                print(f"Processed {len(new_messages)} new messages")
            else:
                print("No new messages to process")
            
            log.success = True
            
        except Exception as e:
            error_msg = f"Hourly refresh failed: {str(e)}"
            print(error_msg)
            log.errors.append(error_msg)
            log.success = False
        
        finally:
            log.duration_seconds = time.time() - start_time
            await self.notion_logger.log_ingestion(log)
            print(f"Hourly refresh completed in {format_duration(log.duration_seconds)}")
    
    async def manual_refresh(self):
        """Manually trigger a refresh"""
        print("Manual refresh triggered")
        await self.hourly_refresh()
    
    async def stop(self):
        """Stop the ingestion worker"""
        print("Stopping ingestion worker...")
        self.running = False
        
        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        # Cancel initial ingestion if still running
        if self.initial_ingestion_task and not self.initial_ingestion_task.done():
            print("Cancelling initial ingestion...")
            self.initial_ingestion_task.cancel()
            try:
                await self.initial_ingestion_task
            except asyncio.CancelledError:
                pass
        
        # Save final state
        self._save_state()
        
        print("✅ Ingestion worker stopped gracefully")


async def main():
    """Main entry point for the ingestion worker"""
    worker = SlackIngestionWorker()
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 