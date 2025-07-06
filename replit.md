# Slack Message Ingestion Worker

## Overview

This application is a Slack message ingestion worker that automatically fetches messages from specified Slack channels, generates embeddings using OpenAI, stores them in Pinecone vector database, and logs operations to Notion. The system runs as a background service with scheduled intervals to continuously process new messages.

## System Architecture

The application follows a modular, service-oriented architecture with clear separation of concerns:

### Core Components
- **Configuration Management**: Centralized config using environment variables and dataclasses
- **Data Models**: Type-safe data structures for Slack entities and logging
- **Service Layer**: Separate services for Slack ingestion, embedding generation, vector storage, and logging
- **Scheduling**: Background task management with initial ingestion and periodic updates
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **State Management**: Persistent state tracking for resumable operations

### Technology Stack
- **Language**: Python with async/await for concurrent operations
- **Slack Integration**: slack-sdk for API interactions
- **AI/ML**: OpenAI API for text embeddings (text-embedding-3-small model)
- **Vector Database**: Pinecone for similarity search and storage
- **Documentation**: Notion API for operation logging
- **Scheduling**: APScheduler for background job management
- **Data Processing**: Custom text chunking and rate limiting

## Key Components

### Configuration Service (`config.py`)
- Manages all environment variables and application settings
- Validates required configurations on startup
- Supports configurable rate limits and chunking parameters
- Parses comma-separated channel lists from environment

### Data Models (`data_models.py`)
- Defines structured data types for Slack entities (messages, users, channels, reactions)
- Provides text conversion methods for embedding generation
- Includes metadata extraction for vector storage
- Supports thread hierarchies and message relationships

### Slack Ingester (`slack_ingester.py`)
- Handles Slack API interactions with rate limiting
- Caches user and channel information for efficiency
- Fetches messages with full context (threads, reactions, users)
- Implements incremental updates based on timestamps

### Embedding Service (`embedding_service.py`)
- Generates vector embeddings using OpenAI's text-embedding-3-small model
- Handles text chunking for large messages (8000 char limit with 200 char overlap)
- Includes rate limiting for OpenAI API compliance
- Creates metadata-rich embeddings for enhanced search

### Pinecone Service (`pinecone_service.py`)
- Manages vector database operations (upsert, search, index management)
- Automatically creates indexes with appropriate dimensions (1536D)
- Implements batch processing for efficient uploads
- Uses cosine similarity for vector comparisons

### Notion Logger (`notion_logger.py`)
- Logs all ingestion operations to a structured Notion database
- Tracks success/failure rates, processing metrics, and errors
- Provides audit trail for troubleshooting and monitoring
- Creates database schema automatically if needed

### Scheduler (`scheduler.py`)
- Orchestrates the entire ingestion pipeline
- Handles initial bulk ingestion followed by hourly incremental updates
- Manages state persistence for resumable operations
- Coordinates between all services with error handling

### Rate Limiter (`rate_limiter.py`)
- Implements sliding window rate limiting for multiple APIs
- Prevents API quota exhaustion with configurable limits
- Uses async locks for thread-safe operation
- Automatically delays requests when limits are approached

## Data Flow

1. **Initialization**: Load configuration and validate required environment variables
2. **Channel Discovery**: Fetch metadata for configured Slack channels
3. **Message Ingestion**: Retrieve messages with full context (users, threads, reactions)
4. **Text Processing**: Convert messages to embedding-ready text with chunking
5. **Embedding Generation**: Create vector embeddings using OpenAI API
6. **Vector Storage**: Upsert embeddings to Pinecone with rich metadata
7. **Operation Logging**: Record results and metrics to Notion database
8. **Scheduling**: Continue with hourly incremental updates

## External Dependencies

### Required APIs
- **Slack Bot Token**: For accessing Slack workspace and channels
- **OpenAI API**: For generating text embeddings
- **Pinecone**: For vector storage and similarity search
- **Notion Integration**: For operation logging and monitoring

### Python Packages
- `slack-sdk`: Official Slack API client
- `openai`: OpenAI API client for embeddings
- `pinecone-client`: Vector database operations
- `notion-client`: Notion API integration
- `apscheduler`: Background job scheduling

## Deployment Strategy

The application is designed as a long-running background service:

### Environment Setup
- Requires 7 environment variables for API access
- Supports configurable rate limits and processing parameters
- Includes validation and helpful error messages for missing config

### Operational Modes
- **Initial Ingestion**: Bulk processing of historical messages
- **Incremental Updates**: Hourly processing of new messages only
- **State Persistence**: Resumable operations with saved checkpoints

### Monitoring and Logging
- Comprehensive logging to Notion database
- Error tracking and success metrics
- Duration monitoring for performance optimization
- Automatic retry logic for transient failures

## Deployment Status

- July 06, 2025: Worker successfully deployed and running initial ingestion
- Currently processing 1 Slack channel with rate limiting active
- Pinecone index created and operational
- Notion logging database configured and verified

## Current Operations

The worker is performing its first complete ingestion of all historical messages from the configured Slack channel. This process:
- Respects Slack API rate limits (waiting between requests)
- Generates embeddings for all messages using OpenAI
- Stores searchable vectors in Pinecone
- Logs progress to Notion database

After initial ingestion completes, the system automatically switches to hourly incremental updates.

## Planned Enhancements

- Additional Slack channels will be added once initial setup is verified
- Multi-channel support is already built into the architecture

## Changelog

- July 06, 2025: Initial setup and successful deployment
- July 06, 2025: Fixed Pinecone API compatibility for new library version
- July 06, 2025: Worker operational with rate limiting and proper API integration

## User Preferences

Preferred communication style: Simple, everyday language.