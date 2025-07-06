import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import config
from slack_ingester import SlackIngester
from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from notion_logger import NotionLogger
from data_models import IngestionLog
from utils import get_current_utc_time, save_state, load_state, format_duration
import time

class SlackWorkerScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.slack_ingester = SlackIngester()
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()
        self.notion_logger = NotionLogger()
        
        self.is_initial_ingestion_complete = False
        self.initial_ingestion_task = None
    
    async def start(self):
        """Start the scheduler and initial ingestion"""
        print("Starting Slack Worker Scheduler...")
        
        # Load previous state
        state = load_state()
        self.is_initial_ingestion_complete = state.get('initial_ingestion_complete', False)
        
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
                
                # Store in Pinecone
                print("Storing embeddings in Pinecone...")
                await self.pinecone_service.upsert_embeddings(embeddings_data)
                
                print("Initial ingestion complete!")
            
            # Mark initial ingestion as complete
            self.is_initial_ingestion_complete = True
            save_state({'initial_ingestion_complete': True})
            
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
                
                # Store in Pinecone
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
    
    async def stop(self):
        """Stop the scheduler"""
        print("Stopping scheduler...")
        self.scheduler.shutdown()
        
        if self.initial_ingestion_task and not self.initial_ingestion_task.done():
            print("Cancelling initial ingestion...")
            self.initial_ingestion_task.cancel()
            try:
                await self.initial_ingestion_task
            except asyncio.CancelledError:
                pass
