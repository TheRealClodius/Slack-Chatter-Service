# Slack Message Ingestion Worker

## Overview

This application is a Slack message vector search API that provides semantic search capabilities for Slack messages. It automatically fetches messages from specified Slack channels, generates embeddings using OpenAI, stores them in vector storage, and logs operations to Notion. The system runs as a web service with background processing for continuous message ingestion and provides REST API endpoints for other repositories to search indexed messages.

## System Architecture

The application follows a modular, service-oriented architecture with clear separation of concerns:

### Core Components
- **Configuration Management**: Centralized config using environment variables and dataclasses
- **Data Models**: Type-safe data structures for Slack entities and logging
- **Web API**: FastAPI-based REST API with endpoints for semantic search and status monitoring
- **Service Layer**: Separate services for Slack ingestion, embedding generation, vector storage, and logging
- **Background Processing**: Automated message ingestion with initial bulk processing and hourly updates
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **State Management**: Persistent state tracking for resumable operations

### Technology Stack
- **Language**: Python with async/await for concurrent operations
- **Web Framework**: FastAPI for REST API endpoints with automatic documentation
- **Server**: Uvicorn ASGI server for production deployment
- **Slack Integration**: slack-sdk for API interactions
- **AI/ML**: OpenAI API for text embeddings (text-embedding-3-small model)
- **Vector Storage**: File-based vector storage for deployment compatibility
- **Documentation**: Notion API for operation logging
- **Scheduling**: APScheduler for background job management
- **Data Processing**: Custom text chunking and rate limiting

## API Endpoints

The application exposes REST API endpoints for external repositories to search indexed Slack messages:

### Search Endpoints
- **POST /search**: Semantic search with full filtering options
- **GET /search**: Simplified search using query parameters (e.g., `?q=hello&top_k=5`)
- **GET /channels**: List all indexed Slack channels

### Monitoring Endpoints  
- **GET /health**: Health check with background worker and storage status
- **GET /stats**: Index statistics including total vectors and last refresh time
- **POST /refresh**: Manually trigger message refresh (async background task)

### Usage Examples
```bash
# Simple search
curl "http://localhost:5000/search?q=deployment&top_k=3"

# Advanced search with filters
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "error handling", "top_k": 5, "channel_filter": "general"}'

# Health check
curl http://localhost:5000/health
```

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

### Deployment Configuration
- **Type**: Cloud Run web service (serves REST API on port 5000)
- **Run Command**: `python main.py`
- **Build Command**: Leave empty for Python web applications
- **Dependencies**: Managed via pyproject.toml with FastAPI and uvicorn
- **Port**: 5000 (web server with background worker integration)

### Deployment Requirements
1. Use Cloud Run deployment type for web service
2. Set run command to `python main.py`
3. Ensure all required environment variables are configured
4. Application serves HTTP requests on port 5000 with background processing

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

- July 06, 2025: Worker successfully deployed and operational
- Processing 3 Slack channels with proper rate limiting
- Pinecone index created with 28 message embeddings stored
- Notion logging database schema matched and verified
- Hourly refresh system active and running
- July 06, 2025: Deployment configuration updated for background worker mode

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
- July 06, 2025: Resolved Pinecone import compatibility issue with version detection
- July 06, 2025: Fixed deployment failure by removing old Pinecone v2 API fallback code and using only v3+ API
- July 06, 2025: Resolved deployment configuration issues - updated for background worker mode instead of Cloud Run
- July 06, 2025: Applied deployment fixes - simplified Pinecone API to v7+ only, confirmed background worker configuration
- July 06, 2025: Applied all suggested deployment fixes: updated Pinecone imports to v7+ API, simplified client initialization, fixed index operations, confirmed background worker ready
- July 06, 2025: Fixed deployment compatibility issues - updated Pinecone service to use modern v7.3.0 API with Pinecone class and ServerlessSpec, removed deprecated init function usage, confirmed all tests passing
- July 06, 2025: Resolved all deployment failures - fixed Notion database schema mismatches, added robust error handling for invalid Slack channels, corrected all property names and types, worker now running successfully with 28+ vectors stored
- July 06, 2025: Final deployment compatibility fixes - removed problematic Pinecone packages entirely, implemented file-based vector storage for deployment reliability, fixed Cloud Run vs Background Worker configuration issues, all tests passing with worker running successfully
- July 06, 2025: **Major Architecture Update** - Transformed application from background worker to web API service with FastAPI, added REST endpoints for semantic search (/search, /health, /stats, /channels), integrated background processing into web server lifecycle, successfully deployed as Cloud Run web service on port 5000

## User Preferences

Preferred communication style: Simple, everyday language.