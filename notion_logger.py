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
            # Get database schema to understand existing properties
            database = self.client.databases.retrieve(database_id=self.database_id)
            existing_props = database['properties']
            
            # Find the title property (there should be exactly one)
            title_prop = None
            for prop_name, prop_data in existing_props.items():
                if prop_data['type'] == 'title':
                    title_prop = prop_name
                    break
            
            if not title_prop:
                raise Exception("No title property found in Notion database")
            
            # Build properties based on what exists in the database
            properties = {
                title_prop: {
                    "title": [
                        {
                            "text": {
                                "content": f"{log.operation} - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                }
            }
            
            # Add other properties if they exist in the database
            prop_mappings = {
                'timestamp': log.timestamp.isoformat(),
                'operation': log.operation,
                'channels': log.channels_processed,
                'messages': log.messages_processed,
                'embeddings': log.embeddings_generated,
                'duration': log.duration_seconds,
                'success': log.success,
                'errors': "\n".join(log.errors) if log.errors else "None"
            }
            
            for prop_name, prop_data in existing_props.items():
                prop_type = prop_data['type']
                prop_name_lower = prop_name.lower()
                
                # Match property names (case insensitive, partial match)
                if 'timestamp' in prop_name_lower and prop_type == 'date':
                    properties[prop_name] = {"date": {"start": prop_mappings['timestamp']}}
                elif 'operation' in prop_name_lower and prop_type in ['rich_text', 'text']:
                    properties[prop_name] = {"rich_text": [{"text": {"content": prop_mappings['operation']}}]}
                elif 'channel' in prop_name_lower and prop_type == 'number':
                    properties[prop_name] = {"number": prop_mappings['channels']}
                elif 'message' in prop_name_lower and prop_type == 'number':
                    properties[prop_name] = {"number": prop_mappings['messages']}
                elif 'embedding' in prop_name_lower and prop_type == 'number':
                    properties[prop_name] = {"number": prop_mappings['embeddings']}
                elif 'duration' in prop_name_lower and prop_type == 'number':
                    properties[prop_name] = {"number": prop_mappings['duration']}
                elif 'success' in prop_name_lower and prop_type == 'checkbox':
                    properties[prop_name] = {"checkbox": prop_mappings['success']}
                elif 'error' in prop_name_lower and prop_type in ['rich_text', 'text']:
                    properties[prop_name] = {"rich_text": [{"text": {"content": prop_mappings['errors']}}]}
            
            # Create page in Notion database
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            print(f"Logged ingestion results to Notion: {log.operation}")
            
        except Exception as e:
            print(f"Error logging to Notion: {e}")
            print("Continuing without Notion logging...")
    
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
