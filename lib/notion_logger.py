from datetime import datetime
from typing import List, Optional
from notion_client import Client

from lib.config import config
from lib.data_models import IngestionLog

class NotionLogger:
    def __init__(self):
        self.client = Client(auth=config.notion_integration_secret)
        self.database_id = config.notion_database_id
    
    async def log_ingestion(self, log: IngestionLog):
        """Log ingestion results to Notion database"""
        try:
            # Map to your exact Notion schema
            properties = {
                "Embeddings": {
                    "title": [
                        {
                            "text": {
                                "content": f"{log.operation} - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                },
                "Run ID": {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"{log.operation}_{log.timestamp.strftime('%Y%m%d_%H%M%S')}"
                            }
                        }
                    ]
                },
                "Run Status": {
                    "status": {
                        "name": "Success" if log.success else "Failed"
                    }
                },
                "Start Time": {
                    "date": {
                        "start": log.timestamp.isoformat()
                    }
                },
                "Channels Checked": {
                    "number": log.channels_processed
                },
                "Messages Embedded": {
                    "number": log.embeddings_generated
                },
                "Duration": {
                    "number": round(log.duration_seconds, 2)
                }
            }
            
            # Add errors if any
            if log.errors:
                properties["Errors"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": "; ".join(log.errors)
                            }
                        }
                    ]
                }
            
            # Create the page
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
        except Exception as e:
            print(f"Error logging to Notion: {e}")
    
    async def get_last_successful_ingestion(self) -> Optional[datetime]:
        """Get timestamp of last successful ingestion"""
        try:
            # Query for last successful ingestion
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Run Status",
                    "status": {
                        "equals": "Success"
                    }
                },
                sorts=[
                    {
                        "property": "Start Time",
                        "direction": "descending"
                    }
                ],
                page_size=1
            )
            
            if response['results']:
                timestamp_str = response['results'][0]['properties']['Start Time']['date']['start']
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
        except Exception as e:
            print(f"Error getting last ingestion from Notion: {e}")
        
        return None
    
    async def create_database_schema(self):
        """Create or verify the database schema"""
        try:
            # Get database to verify it exists
            database = self.client.databases.retrieve(database_id=self.database_id)
            print(f"Using Notion database: {database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
            
        except Exception as e:
            print(f"Error accessing Notion database: {e}")
            print("Please ensure the database exists and the integration has access")
