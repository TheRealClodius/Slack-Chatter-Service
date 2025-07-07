# Slack Chatter Service 2.0

## Overview

The Slack Chatter Service is an MCP (Model Context Protocol) tool that provides intelligent semantic search capabilities for Slack messages. The service consists of two main components: a background ingestion worker that continuously processes Slack messages and an MCP server that provides search functionality. The system uses OpenAI embeddings for semantic understanding and Pinecone for vector storage.

## System Architecture

The application follows a clean, modular architecture with separation of concerns:

### Component Architecture
- **MCP Server**: Implements the Model Context Protocol for search operations
- **Background Worker**: Handles continuous ingestion of Slack messages
- **Search Service**: Dedicated semantic search functionality
- **Shared Libraries**: Core components used across all services

### Technology Stack
- **Backend**: Python with asyncio for concurrent operations
- **AI/ML**: OpenAI GPT-4o-mini for query enhancement and text-embedding-3-small for embeddings
- **Vector Database**: Pinecone for semantic search (with local JSON fallback for development)
- **Communication**: Slack Web API for message ingestion
- **Logging**: Notion integration for operational logs
- **Protocol**: MCP (Model Context Protocol) for client communication

## Key Components

### Core Services

#### MCP Server (`mcp/server.py`)
- Implements pure JSON-RPC 2.0 protocol over stdio
- Provides search capabilities via MCP protocol
- Handles client requests for message search, channel information, and statistics
- Integrates with LLM search agent for intelligent query enhancement

#### LLM Search Agent (`mcp/llm_search_agent.py`)
- AI-powered query enhancement using OpenAI GPT-4o-mini
- YAML-based configuration for system prompts and model settings
- Transforms natural language queries into structured search parameters
- Provides reasoning for search strategy decisions

#### Search Service (`search/service.py`)
- Dedicated semantic search functionality
- Vector similarity search using OpenAI embeddings
- Support for filtering by channel, user, and date ranges
- Result ranking and relevance scoring

#### Ingestion Worker (`ingestion/worker.py`)
- Background process for continuous message ingestion
- Scheduled jobs using AsyncIOScheduler
- Initial ingestion and incremental updates
- State persistence for resumable operations

#### Slack Ingester (`ingestion/slack_ingester.py`)
- Slack API integration with rate limiting
- TTL-based caching for users and channels
- Text cleaning and preprocessing
- Endpoint-specific rate limiting for Slack API

### Shared Libraries (`lib/`)

#### Configuration Management (`lib/config.py`)
- Environment variable handling
- Service configuration with sensible defaults
- Validation of required settings

#### Data Models (`lib/data_models.py`)
- Structured data classes for Slack entities
- Message, channel, user, and reaction models
- Metadata generation for search indexing

#### Embedding Service (`lib/embedding_service.py`)
- OpenAI text-embedding-3-small integration
- Text chunking for large messages
- Rate-limited embedding generation

#### Vector Storage (`lib/pinecone_service.py`)
- Pinecone integration for production
- Local JSON fallback for development
- Vector upsert and similarity search operations

#### Rate Limiting (`lib/rate_limiter.py`)
- Endpoint-specific rate limiting for Slack API
- Retry-after header handling
- OpenAI API rate limiting

#### Utilities (`lib/utils.py`)
- Text processing and cleaning
- State persistence utilities
- Slack text formatting helpers

## Data Flow

### Ingestion Flow
1. **Worker Initialization**: Load previous state and configure scheduler
2. **Message Fetching**: Retrieve messages from configured Slack channels
3. **Text Processing**: Clean and preprocess message text
4. **Embedding Generation**: Create semantic embeddings using OpenAI
5. **Vector Storage**: Store embeddings in Pinecone with metadata
6. **Logging**: Record ingestion metrics in Notion

### Search Flow
1. **Query Reception**: MCP server receives search request
2. **Query Enhancement**: LLM agent enhances natural language query
3. **Embedding Generation**: Convert query to embedding vector
4. **Vector Search**: Perform similarity search in Pinecone
5. **Result Processing**: Format and rank search results
6. **Response**: Return structured results via MCP protocol

### Client Integration Flow
1. **MCP Connection**: Client connects to MCP server via subprocess
2. **Tool Discovery**: Client discovers available search tools
3. **Search Request**: Client sends search query with parameters
4. **Result Processing**: Client receives and formats search results

## External Dependencies

### Required Services
- **Slack API**: Bot token with appropriate scopes for message reading
- **OpenAI API**: For embeddings (text-embedding-3-small) and query enhancement (GPT-4o-mini)
- **Pinecone**: Vector database for semantic search (optional, local fallback available)
- **Notion API**: For operational logging and monitoring

### Key Dependencies
- `slack-sdk`: Slack API client
- `openai`: OpenAI API client
- `pinecone-client`: Vector database client
- `notion-client`: Notion integration
- `apscheduler`: Background job scheduling
- `pyyaml`: Configuration management

## Deployment Strategy

### Development Deployment
- Local execution with JSON file storage
- Environment variables via `.env` file
- Direct Python execution for testing

### Production Deployment Options

#### Replit Deployment (Recommended for beginners)
- Import repository from GitHub
- Configure environment variables in Secrets tab
- One-command deployment with `python replit_deploy.py`
- Automatic dependency installation and service startup

#### MCP Tool Deployment
- Install as Python package: `pip install -e .`
- Configure MCP client to execute as subprocess
- Environment variables passed through MCP configuration
- No web server required - pure MCP protocol

#### Traditional Server Deployment
- Background worker deployment for continuous ingestion
- MCP server for on-demand search queries
- Separate deployment of ingestion and search components

### Configuration Requirements
- Slack bot token with `channels:history`, `channels:read`, `users:read` scopes
- OpenAI API key with sufficient quota for embeddings and chat completions
- Pinecone API key and index configuration
- Notion integration secret and database ID for logging

## Changelog
```
Changelog:
- July 07, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```