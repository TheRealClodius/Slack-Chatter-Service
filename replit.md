# Slack Chatter Service 2.0

## Overview

The Slack Chatter Service is an MCP (Model Context Protocol) tool that provides intelligent semantic search capabilities for Slack messages. The service consists of multiple components: a background ingestion worker that continuously processes Slack messages, a local MCP server for stdio communication, and a remote MCP server with OAuth 2.1 authentication. The system uses OpenAI embeddings for semantic understanding and Pinecone for vector storage.

## System Architecture

The application follows a clean, modular architecture with separation of concerns:

### Component Architecture
- **Local MCP Server**: Implements stdio MCP protocol for local client integration
- **Remote MCP Server**: Implements OAuth 2.1 + SSE for remote authenticated access
- **Background Worker**: Handles continuous ingestion of Slack messages
- **Search Service**: Dedicated semantic search functionality
- **Shared Libraries**: Core components used across all services

### Technology Stack
- **Backend**: Python with asyncio for concurrent operations
- **AI/ML**: OpenAI GPT-4o-mini for query enhancement and text-embedding-3-small for embeddings
- **Vector Database**: Pinecone for semantic search (with local JSON fallback for development)
- **Communication**: Slack Web API for message ingestion
- **Authentication**: OAuth 2.1 with PKCE for remote access
- **Real-time Communication**: Server-Sent Events (SSE) for remote protocol
- **Logging**: Notion integration for operational logs
- **Protocols**: MCP (stdio) and MCP Remote Protocol (OAuth 2.1 + SSE)

## Key Components

### Core Services

#### MCP Server (`mcp/server.py`)
- **Dual Implementation**: Pure JSON-RPC 2.0 protocol over stdio + Remote Protocol server
- **Local MCP**: Traditional subprocess execution for MCP clients
- **Remote MCP**: OAuth 2.1 authentication with SSE communication
- Provides direct search capabilities via both protocols
- Handles client requests for message search, channel information, and statistics
- **Clean Architecture**: No server-side agents - agents belong on client side

#### Remote MCP Application (`mcp/fastapi_app.py`)
- **OAuth 2.1 Implementation**: Complete authorization server with PKCE
- **Server-Sent Events**: Real-time bidirectional communication
- **Scoped Permissions**: `mcp:search`, `mcp:channels`, `mcp:stats`
- **Session Management**: Token generation, validation, and expiration
- **FastAPI Integration**: RESTful endpoints with automatic OpenAPI documentation
- **Security Features**: CORS, rate limiting, input validation

#### LLM Search Agent (`mcp/llm_search_agent.py`)
- **Client-side only**: Agent code preserved for client-side integration
- AI-powered query enhancement using OpenAI GPT-4o-mini
- YAML-based configuration for system prompts and model settings
- Transforms natural language queries into structured search parameters
- **Note**: Removed from server - proper MCP architecture uses client-side agents

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
- **Canvas content extraction**: Automatically extracts and indexes Slack canvas content
- **Rich content support**: Canvas titles, text blocks, and metadata are embedded for search

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
3. **Canvas Extraction**: Extract canvas content from channels with canvas files
4. **Text Processing**: Clean and preprocess message text and canvas content
5. **Embedding Generation**: Create semantic embeddings using OpenAI
6. **Vector Storage**: Store embeddings in Pinecone with metadata
7. **Logging**: Record ingestion metrics in Notion

### Local MCP Search Flow
1. **Client Connection**: MCP client connects via subprocess (stdio)
2. **Tool Discovery**: Client discovers available search tools
3. **Query Reception**: MCP server receives search request
4. **Query Enhancement**: LLM agent enhances natural language query
5. **Embedding Generation**: Convert query to embedding vector
6. **Vector Search**: Perform similarity search in Pinecone
7. **Result Processing**: Format and rank search results
8. **Response**: Return structured results via MCP protocol

### Remote MCP Search Flow
1. **OAuth Authentication**: Client performs OAuth 2.1 flow with PKCE
2. **Token Validation**: Server validates access token and scopes
3. **SSE Connection**: Client establishes Server-Sent Events connection
4. **MCP Communication**: JSON-RPC 2.0 over SSE for real-time interaction
5. **Search Processing**: Same as local MCP but with authentication
6. **Response Delivery**: Results delivered via SSE or HTTP response

### Client Integration Flow
1. **Protocol Selection**: Choose between local stdio or remote OAuth 2.1
2. **Authentication**: Skip for local, OAuth 2.1 for remote
3. **Connection Establishment**: Subprocess for local, HTTP/SSE for remote
4. **Tool Discovery**: Client discovers available search tools
5. **Search Request**: Client sends search query with parameters
6. **Result Processing**: Client receives and formats search results

## Deployment Modes

### Local MCP Mode
```bash
# Traditional MCP tool execution
python main_orchestrator.py mcp
```
- **Use Case**: Development, MCP client integration
- **Communication**: stdin/stdout JSON-RPC
- **Authentication**: None (process isolation)
- **Deployment**: Subprocess execution

### Remote MCP Mode
```bash
# OAuth 2.1 + SSE server
python main_orchestrator.py remote
```
- **Use Case**: Production, web applications, remote access
- **Communication**: HTTP + Server-Sent Events
- **Authentication**: OAuth 2.1 with PKCE
- **Deployment**: Web server on port 8080

### Ingestion Worker Mode
```bash
# Background message processing
python main_orchestrator.py ingestion
```
- **Use Case**: Continuous data processing
- **Communication**: Slack API
- **Authentication**: Slack bot token
- **Deployment**: Background service

### Combined Mode
```bash
# Ingestion + Local MCP
python main_orchestrator.py combined
```
- **Use Case**: All-in-one deployment
- **Communication**: Slack API + stdin/stdout
- **Authentication**: Slack bot token
- **Deployment**: Background service + MCP server

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
- `fastapi`: Web framework for remote MCP server
- `authlib`: OAuth 2.1 implementation
- `sse-starlette`: Server-Sent Events support

## Deployment Strategy

### Development Deployment
- Local execution with JSON file storage
- Environment variables via `.env` file
- Direct Python execution for testing
- Local MCP mode for client integration

### Production Deployment Options

#### Replit Deployment (Recommended for beginners)
- Import repository from GitHub
- Configure environment variables in Secrets tab
- Choose deployment mode:
  - **Ingestion Only**: `python main_orchestrator.py ingestion`
  - **Remote MCP**: `python main_orchestrator.py remote`
  - **Combined**: `python main_orchestrator.py combined`
- Automatic dependency installation and service startup

#### MCP Tool Deployment (Local)
- Install as Python package: `pip install -e .`
- Configure MCP client to execute as subprocess
- Environment variables passed through MCP configuration
- No web server required - pure MCP protocol

#### MCP Remote Protocol Deployment (Production)
- Deploy to cloud platforms (Railway, Render, etc.)
- Configure OAuth 2.1 redirect URIs
- Enable HTTPS for production OAuth flows
- Set up monitoring and logging

#### Traditional Server Deployment
- Background worker deployment for continuous ingestion
- Remote MCP server for authenticated access
- Separate deployment of ingestion and search components

### Configuration Requirements
- Slack bot token with `channels:history`, `channels:read`, `users:read` scopes
- OpenAI API key with sufficient quota for embeddings and chat completions
- Pinecone API key and index configuration
- Notion integration secret and database ID for logging

## MCP Remote Protocol Features

### OAuth 2.1 Authentication
- **PKCE (Proof Key for Code Exchange)**: Prevents authorization code interception
- **Scoped Permissions**: Fine-grained access control
- **Token Expiration**: 24-hour token lifetime
- **Session Management**: Automatic cleanup and validation

### Server-Sent Events (SSE)
- **Real-time Communication**: Bidirectional JSON-RPC over SSE
- **Persistent Connections**: Long-lived connections with heartbeat
- **Error Handling**: Graceful degradation and reconnection
- **Alternative to WebSockets**: Simpler implementation for MCP protocol

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/oauth-authorization-server` | GET | OAuth 2.1 discovery |
| `/oauth/authorize` | GET | Authorization endpoint |
| `/oauth/token` | POST | Token exchange |
| `/mcp/sse` | GET | SSE communication |
| `/mcp/request` | POST | Direct MCP requests |
| `/mcp/session` | GET | Session information |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |

### Client Integration Examples

#### Python Client
```python
from mcp_remote_client import MCPRemoteClient

client = MCPRemoteClient(
    base_url="https://your-replit-app.replit.app",
    client_id="mcp-slack-chatter-client",
    client_secret="your_client_secret"
)

await client.authenticate()
results = await client.search_messages("deployment issues")
```

#### JavaScript Client
```javascript
const client = new MCPRemoteClient({
  baseUrl: 'https://your-replit-app.replit.app',
  clientId: 'mcp-slack-chatter-client',
  clientSecret: process.env.MCP_CLIENT_SECRET
});

await client.authenticate();
const results = await client.searchMessages('authentication errors');
```

## Changelog
```
Changelog:
- July 09, 2025. **OAUTH 2.1 COMPLETE**: Full OAuth 2.1 authentication flow implemented and tested successfully
- July 09, 2025. **PRODUCTION READY**: Complete MCP Remote Protocol with PKCE authentication and 374 searchable messages
- July 09, 2025. **SECURITY UPGRADE**: Moved from API keys to OAuth 2.1 with scoped permissions (mcp:search, mcp:channels, mcp:stats)
- July 09, 2025. **CLIENT INTEGRATION**: Created comprehensive OAuth client guides and working demo scripts
- July 09, 2025. **ARCHITECTURE CLEANUP**: Removed server-side agent code - proper MCP architecture achieved
- July 09, 2025. **AUTHENTICATION SUCCESS**: Server-generated API key system working perfectly - authentication breakthrough achieved
- July 09, 2025. **Production Deployment**: Full MCP server operational with 6/7 tools on port 5000 
- July 09, 2025. **Auto-Generated Keys**: Server creates deployment keys automatically with 192-bit entropy
- July 09, 2025. **Secure Authentication DEPLOYED**: Implemented secure API key whitelisting system with 192-bit entropy
- July 09, 2025. **MCP 2.0 Specification Compliance**: Upgraded to pure MCP 2.0 (2025-03-26) compliance
- July 09, 2025. **JSON-RPC 2.0 Only**: Removed legacy query_params format, POST-only endpoint
- July 09, 2025. **Header Compliance**: Updated to Mcp-Session-Id header format
- July 09, 2025. **Ingestion Progress**: 374 messages processed with complete OAuth authentication working
- July 09, 2025. Recreated Pinecone index with 1536 dimensions for text-embedding-3-small
- July 09, 2025. Enhanced thread nesting to embed complete conversation context
- July 09, 2025. Improved reaction handling with user attribution and proper nesting
- July 09, 2025. Added comprehensive rich content extraction (lists, workflows, posts, code files)
- July 09, 2025. Fixed Pinecone package dependency (pinecone-client → pinecone)
- July 09, 2025. Added Slack canvas content extraction and embedding support
- July 09, 2025. Enhanced data models with canvas metadata (title, content type)
- July 09, 2025. Fixed OpenAI API key integration for successful embedding generation
- July 07, 2025. Added MCP Remote Protocol with OAuth 2.1 and SSE
- July 07, 2025. Dual MCP implementation (stdio + remote)
- July 07, 2025. Enhanced security with authentication and scoped permissions
- July 07, 2025. Real-time communication via Server-Sent Events
- July 07, 2025. FastAPI integration for remote protocol
- July 07, 2025. Initial setup
- July 07, 2025. Added remote MCP protocol support with OAuth 2.1 and SSE
- July 07, 2025. Fixed deployment issues: asyncio conflicts, port configuration, dependencies
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```