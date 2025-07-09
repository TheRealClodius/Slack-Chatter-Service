import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    # Slack Configuration
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_channels: List[str] = None  # Will be populated from SLACK_CHANNELS env var
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536  # Standard dimension for text-embedding-3-small
    
    # Pinecone Configuration
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_environment: str = os.getenv("PINECONE_ENVIRONMENT", "")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "slack-messages")
    
    # Notion Configuration
    notion_integration_secret: str = os.getenv("NOTION_INTEGRATION_SECRET", "")
    notion_database_id: str = os.getenv("NOTION_DATABASE_ID", "")
    
    # OpenAI Rate Limiting Configuration
    openai_rate_limit_per_minute: int = 3000  # Tier 1 rate limit
    
    # Scheduling Configuration
    refresh_interval_hours: int = 1
    
    # Chunking Configuration
    max_chunk_size: int = 8000  # Characters per chunk for embeddings
    chunk_overlap: int = 200
    
    # Caching Configuration
    cache_users_hours: int = 24  # How long to cache user info
    cache_channels_hours: int = 24  # How long to cache channel info
    
    # MCP Configuration
    mcp_server_name: str = "slack-chatter-search"
    mcp_server_version: str = "2.0.0"
    
    def __post_init__(self):
        # Parse comma-separated channels from environment
        channels_str = os.getenv("SLACK_CHANNELS", "")
        if channels_str:
            self.slack_channels = [ch.strip() for ch in channels_str.split(",")]
        else:
            self.slack_channels = []
        
        # Validate required configurations
        self._validate_config()
    
    def _validate_config(self):
        required_vars = [
            ("SLACK_BOT_TOKEN", self.slack_bot_token),
            ("OPENAI_API_KEY", self.openai_api_key),
            ("PINECONE_API_KEY", self.pinecone_api_key),
            ("PINECONE_ENVIRONMENT", self.pinecone_environment),
            ("NOTION_INTEGRATION_SECRET", self.notion_integration_secret),
            ("NOTION_DATABASE_ID", self.notion_database_id),
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        if not self.slack_channels:
            raise ValueError("No Slack channels specified. Set SLACK_CHANNELS environment variable.")

# Create global config instance
config = Config()
