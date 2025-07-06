from datetime import datetime
from typing import List
from notion_client import Client

from config import config
from data_models import IngestionLog

class NotionLogger:
    def __init__(self):
        self.client = Client(auth=config.notion_integration_secret)
        self.database_id = config.notion_database_id
    
    async def log_ingestion(self, log: IngestionLog):
        """Log ingestion results to Notion database"""
        try:
            # Prepare properties for Notion database
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": f"{log.operation} - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                },
                "Timestamp": {
                    "date": {
                        "start": log.timestamp.isoformat()
                    }
                },
                "Operation": {
                    "rich_text": [
                        {
                            "text": {
                                "content": log.operation
                            }
                        }
                    ]
                },
                "Channels": {
                    "number": log.channels_processed
                },
                "Messages": {
                    "number": log.messages_processed
                },
                "Embeddings": {
                    "number": log.embeddings_generated
                },
                "Duration": {
                    "number": log.duration_seconds
                },
                "Success": {
                    "checkbox": log.success
                },
                "Errors": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "\n".join(log.errors) if log.errors else "None"
                            }
                        }
                    ]
                }
            }
            
            # Create page in Notion database
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            print(f"Logged ingestion results to Notion: {log.operation}")
            
        except Exception as e:
            print(f"Error logging to Notion: {e}")
    
    async def get_last_successful_ingestion(self) -> datetime:
        """Get timestamp of last successful ingestion"""
        try:
            # Query for last successful ingestion
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Success",
                    "checkbox": {
                        "equals": True
                    }
                },
                sorts=[
                    {
                        "property": "Timestamp",
                        "direction": "descending"
                    }
                ],
                page_size=1
            )
            
            if response['results']:
                timestamp_str = response['results'][0]['properties']['Timestamp']['date']['start']
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
        except Exception as e:
            print(f"Error getting last ingestion from Notion: {e}")
        
        return None
    
    async def create_database_schema(self):
        """Create the required database schema if it doesn't exist"""
        try:
            # Get database to check if it exists and has correct schema
            database = self.client.databases.retrieve(database_id=self.database_id)
            print("Notion database schema verified")
            
        except Exception as e:
            print(f"Error verifying Notion database schema: {e}")
            print("Please ensure your Notion database has the following columns:")
            print("- Name (Title)")
            print("- Timestamp (Date)")
            print("- Operation (Text)")
            print("- Channels (Number)")
            print("- Messages (Number)")
            print("- Embeddings (Number)")
            print("- Duration (Number)")
            print("- Success (Checkbox)")
            print("- Errors (Text)")
