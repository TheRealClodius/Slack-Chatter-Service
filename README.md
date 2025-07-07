# Slack Chatter Service 2.0

🚀 **MCP tool for semantic search of Slack messages with intelligent query enhancement**

## Overview

Slack Chatter Service has been completely restructured with a clean, modular architecture that separates concerns between message ingestion and search functionality. The service now provides intelligent search capabilities through the Model Context Protocol (MCP) with both **local stdio** and **remote OAuth 2.1/SSE** access modes, plus an AI agent that enhances and formats queries for better results.

## 🏗️ New Architecture

### Core Components

```
slack-chatter-service/
├── mcp/                    # MCP Server & Remote Protocol
│   ├── server.py          # Pure MCP + Remote Protocol implementation
│   ├── fastapi_app.py     # OAuth 2.1 + SSE FastAPI application
│   └── llm_search_agent.py # Intelligent query enhancement
├── search/                 # Search Service
│   └── service.py         # Dedicated search functionality
├── ingestion/             # Background Workers
│   ├── slack_ingester.py  # Slack API integration
│   └── worker.py          # Background ingestion process
├── lib/                    # Core Shared Components
│   ├── config.py          # Configuration management
│   ├── data_models.py     # Data structures
│   ├── embedding_service.py # OpenAI embeddings
│   ├── pinecone_service.py  # Vector storage
│   ├── notion_logger.py   # Logging service
│   ├── rate_limiter.py    # API rate limiting
│   └── utils.py           # Utilities
├── scripts/               # Utility Scripts
│   └── verify_ingestion.py # Verification tool
├── tests/                 # Test Files (ready for new tests)
└── main_orchestrator.py   # Unified entry point
```

### Key Improvements

- **🔗 Decoupled Architecture**: Ingestion and search are completely separated
- **🤖 Intelligent Agent**: AI-powered query enhancement and formatting
- **📡 Dual MCP Modes**: Local stdio + Remote OAuth 2.1/SSE protocol
- **🔒 Secure Remote Access**: OAuth 2.1 authentication with scoped permissions
- **🎯 Focused Components**: Each service has a single responsibility
- **🔧 Flexible Deployment**: Run different modes independently

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -e .

# Or with uv (recommended)
uv install -e .
```

### Configuration

#### 1. Set up your Slack Bot

**⚠️ IMPORTANT:** Your Slack bot must be added to the channels you want to index!

1. Create a Slack app and get your bot token
2. **Add your bot to each channel** you want to search (bot needs to be a member)
3. Get channel IDs: Right-click channel → View channel details → Copy channel ID
4. Your bot needs these permissions:
   - `channels:history` - Read messages in public channels
   - `channels:read` - View basic information about channels
   - `users:read` - View basic information about users

#### 2. Set Environment Variables

```bash
# Slack Configuration
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_CHANNELS="C1234567890,C0987654321"  # Channel IDs where your bot is a member

# OpenAI Configuration
export OPENAI_API_KEY="sk-your-openai-key"

# Notion Configuration (optional)
export NOTION_INTEGRATION_SECRET="your-notion-secret"
export NOTION_DATABASE_ID="your-database-id"

# Optional Configuration
export REFRESH_INTERVAL_HOURS="1"
export SLACK_RATE_LIMIT_PER_MINUTE="50"
```

### Running the Service

The new architecture supports multiple modes:

#### 1. MCP Server Mode (Local - stdio)
```bash
# Run as local MCP tool via stdio
python main_orchestrator.py mcp

# Or using the installed script
slack-chatter mcp
```

#### 2. MCP Remote Protocol Mode (OAuth 2.1 + SSE)
```bash
# Run MCP Remote Protocol server with OAuth 2.1 and SSE
python main_orchestrator.py remote

# Server runs on http://localhost:8080 with:
# - OAuth 2.1 authentication with PKCE
# - Server-Sent Events (SSE) communication
# - Scoped permissions (mcp:search, mcp:channels, mcp:stats)
# - Session management with token expiration
```

#### 3. Ingestion Worker Mode
```bash
# Run background ingestion only
python main_orchestrator.py ingestion
```

#### 4. Combined Mode
```bash
# Run both ingestion and MCP server
python main_orchestrator.py combined
```

#### 5. Test Mode
```bash
# Test search functionality
python main_orchestrator.py search
```

### Validate Configuration
```bash
python main_orchestrator.py mcp --validate-config
```

## 🔒 MCP Remote Protocol

### OAuth 2.1 Authentication

The remote mode implements the official MCP Remote Protocol with:

- **OAuth 2.1** with PKCE for secure authentication
- **Scoped permissions**: `mcp:search`, `mcp:channels`, `mcp:stats`
- **Session management** with 24-hour token expiration
- **Server-Sent Events (SSE)** for real-time communication

### Available Endpoints

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

### Quick OAuth Flow

```bash
# 1. Get OAuth discovery
curl http://localhost:8080/.well-known/oauth-authorization-server

# 2. Generate PKCE and visit authorization URL
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)
CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | cut -c1-43)

# 3. Visit authorization URL (get auth code)
curl "http://localhost:8080/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=random_state&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"

# 4. Exchange code for token
curl -X POST http://localhost:8080/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=YOUR_AUTH_CODE&redirect_uri=http://localhost:3000/callback&client_id=mcp-slack-chatter-client&client_secret=YOUR_CLIENT_SECRET&code_verifier=$CODE_VERIFIER"

# 5. Use access token for MCP requests
curl -X POST http://localhost:8080/mcp/request \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## 🤖 MCP Client Configuration

### Local MCP Server (stdio)

Add this exact configuration to your custom MCP agent:

```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "slack-chatter",
      "args": ["mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-actual-token",
        "OPENAI_API_KEY": "sk-your-actual-key",
        "PINECONE_API_KEY": "your-pinecone-key",
        "PINECONE_ENVIRONMENT": "us-west1-gcp",
        "NOTION_INTEGRATION_SECRET": "your-notion-secret",
        "NOTION_DATABASE_ID": "your-database-id",
        "SLACK_CHANNELS": "C1234567890,C0987654321"
      }
    }
  }
}
```

### Remote MCP Server (OAuth 2.1)

For remote access, use the MCP Remote Protocol client libraries or implement OAuth 2.1 flow:

```python
# Python example
from mcp_remote_client import MCPRemoteClient

client = MCPRemoteClient(
    base_url="http://localhost:8080",
    client_id="mcp-slack-chatter-client",
    client_secret="your_client_secret"  # Get from server logs
)

await client.authenticate()
results = await client.search_messages("deployment issues")
```

**⚠️ Remember:** Your Slack bot must be added to all channels in `SLACK_CHANNELS`!

**💰 Cost Structure:**
- **Embeddings**: ~$0.0001 per 1,000 tokens (one-time indexing cost)
- **AI Search Agent**: ~$0.001-$0.004 per search query (4000 token limit)
- **Total**: Very cost-effective - typical search costs ~$0.002/query + minimal embedding costs

## 🤖 AI Search Agent

Pure LLM-powered search agent with full autonomy through YAML configuration:

### Features

- **🧠 Vector Search Mastery**: Deep understanding of semantic similarity and embedding optimization
- **🎯 Full Agent Control**: Complete query enhancement handled by the LLM agent
- **📊 YAML Configuration**: Easy customization through agent_prompt.yaml
- **🔍 Intelligent Processing**: Agent determines all search parameters and strategies
- **⚡ High Token Limit**: 4000 tokens for comprehensive analysis and responses
- **🚨 Adaptive Reasoning**: Agent provides detailed explanations for all decisions

### Example Enhancements

| Original Query | LLM-Enhanced Behavior |
|---------------|-------------------|
| "urgent auth issues" | 🔍 **Vector Optimization**: Expands to "urgent critical authentication auth login signin session authorization security access denied token expired OAuth SAML SSO issues problems errors failures bugs troubleshooting fix resolve" + increases top_k to 25 |
| "what did @john say about deployment yesterday" | 🎯 **Targeted Retrieval**: Extracts user filter, adds "deployment deploy release publish launch ship pipeline CI/CD build staging production rollout rollback version update" + applies date filter |
| "database performance slow" | 📊 **Semantic Expansion**: Includes "database db performance slow query optimization index bottleneck latency throughput connection pool monitoring metrics" |
| "how to fix cors error" | 🧠 **Solution-Focused**: Expands with "cors cross-origin error fix solve troubleshoot headers preflight browser policy CORS configuration setup" + emphasizes solution patterns |

## 🎯 Prompt Engineering

The LLM search agent uses a YAML-based configuration system for easy customization:

### Configuration File: `agent_prompt.yaml`

```yaml
system_prompt: |
  You are an expert vector search specialist...
  
model:
  name: "gpt-4o-mini"
  temperature: 0.1
  max_tokens: 4000

agent:
  name: "Vector Search Specialist"
  version: "1.0.0"
  
cost:
  per_query_usd: 0.001
```

### Customization Benefits

- **No Code Changes**: Edit prompts without touching Python code
- **Runtime Loading**: Changes take effect immediately on restart
- **Version Control**: Track prompt evolution in git
- **A/B Testing**: Easy to swap different prompt strategies
- **Model Flexibility**: Change model parameters without code deployment

### Getting Agent Info

```bash
# Show current agent configuration
python main_orchestrator.py mcp --agent-info
```

### Sample Output

```
🤖 AI Search Agent Information
========================================
Agent Type: LLM-Powered
Agent: Vector Search Specialist
Version: 1.0.0
Model: gpt-4o-mini
Temperature: 0.1
Max Tokens: 4000
Cost: ~$0.001 per query

📋 Configuration Source: agent_prompt.yaml
🎯 Capabilities:
  🔍 Vector Search Mastery
  🎯 Full Agent Control
  📊 YAML Configuration
  🔍 Intelligent Processing
  ⚡ High Token Limit
  🚨 Adaptive Reasoning

💡 Prompt Engineering:
  • Edit agent_prompt.yaml to customize behavior
  • No code changes needed for prompt modifications
  • Runtime loading of updated prompts
```

## 🔧 MCP Integration

### Using with MCP Clients

The service implements both MCP protocols and provides these tools:

- **`search_slack_messages`**: Semantic search with intelligent enhancement
- **`get_slack_channels`**: List available channels
- **`get_search_stats`**: Index statistics and health info

### Protocol Options

#### 1. Local MCP (stdio) - For development and direct integration
- Simple subprocess execution
- JSON-RPC 2.0 over stdin/stdout
- No authentication required
- Best for: Local development, MCP client integration

#### 2. Remote MCP (OAuth 2.1 + SSE) - For production and web clients
- OAuth 2.1 authentication with PKCE
- Server-Sent Events for real-time communication
- Scoped permissions and session management
- Best for: Production deployments, web applications, shared access

### 📋 Client Templates

Ready-to-use templates for integrating Slack search into your applications:

- **`templates/slack_search_tool.py`**: Complete MCP client implementation
- **`templates/client_prompt.yaml`**: Client-side system prompt for LLM integration
- **`templates/README.md`**: Comprehensive integration guide

```python
# Quick example - see templates/ for full implementation
from templates.slack_search_tool import SlackSearchTool

search_tool = SlackSearchTool([
    "python", "main_orchestrator.py", "mcp"
])

await search_tool.connect()
results = await search_tool.search_slack_messages("deployment issues")
```

### Tool Schema

```json
{
  "name": "search_slack_messages",
  "description": "Search through Slack messages using semantic search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query for finding relevant messages"
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results to return (1-50)",
        "default": 10
      },
      "channel_filter": {
        "type": "string",
        "description": "Filter results by channel name"
      },
      "user_filter": {
        "type": "string",
        "description": "Filter results by user name"
      },
      "date_from": {
        "type": "string",
        "description": "Filter messages from this date (YYYY-MM-DD)"
      },
      "date_to": {
        "type": "string",
        "description": "Filter messages to this date (YYYY-MM-DD)"
      }
    },
    "required": ["query"]
  }
}
```

## 📁 Component Details

### MCP Server (`mcp/server.py`)

- Implements MCP protocol specification
- Handles tool registration and execution
- Provides fallback manual server implementation
- Formats results for MCP clients

### AI Search Agent (`mcp/llm_search_agent.py`)

- **Pure LLM Approach**: Complete query enhancement handled by the agent
- **YAML Configuration**: All behavior controlled through `agent_prompt.yaml`
- **High Token Limit**: 4000 tokens for comprehensive analysis
- **Simplified Code**: Minimal logic, maximum agent autonomy
- **Vector Search Expertise**: Deep understanding built into the prompt
- **Runtime Configuration**: Edit YAML, restart service - no code changes needed

### Search Service (`search/service.py`)

- Dedicated search functionality
- Vector similarity search
- Result caching and optimization
- Health checks and statistics
- Independent of ingestion processes

### Ingestion Worker (`ingestion/worker.py`)

- Standalone background process
- Schedules automatic message ingestion
- Handles initial bulk ingestion
- Incremental updates on schedule
- State persistence and recovery

## 🔄 Migration from v1.x

The new architecture maintains compatibility with existing data while providing a cleaner structure:

### What's Changed

- **Entry Point**: Use `main_orchestrator.py` instead of `main.py`
- **No More REST API**: Replaced with MCP protocol
- **Separated Concerns**: Ingestion and search are independent
- **Enhanced Queries**: AI agent improves search quality

### Migration Steps

1. **Update Dependencies**: Run `pip install -e .` to get new dependencies
2. **Test Configuration**: Run `slack-chatter mcp --validate-config`
3. **Start Ingestion**: Run `slack-chatter ingestion` to populate index
4. **Use MCP Mode**: Run `slack-chatter mcp` for search functionality

### Backward Compatibility

- Existing vector data is preserved
- Configuration variables remain the same
- Notion logging continues to work
- Message processing logic unchanged

## 🛠️ Development

### Project Structure

```
slack-chatter-service/
├── mcp/                    # MCP protocol implementation
├── search/                 # Search service components  
├── ingestion/             # Background worker components
├── lib/                    # Core shared components
│   ├── config.py          # Configuration management
│   ├── data_models.py     # Data structures
│   ├── embedding_service.py # OpenAI embeddings
│   ├── pinecone_service.py  # Vector storage
│   ├── notion_logger.py   # Logging service
│   ├── rate_limiter.py    # API rate limiting
│   └── utils.py           # Utilities
├── scripts/               # Utility scripts
├── tests/                 # Test files
└── main_orchestrator.py   # Main entry point
```

### Adding New Features

1. **Search Enhancements**: Modify `search/service.py`
2. **Agent Intelligence**: Update `mcp/search_agent.py`
3. **MCP Tools**: Add to `mcp/server.py`
4. **Ingestion Logic**: Modify `ingestion/worker.py`
5. **Core Components**: Update files in `lib/` directory
6. **Utility Scripts**: Add new scripts to `scripts/` directory
7. **Tests**: Add test files to `tests/` directory

### Testing

```bash
# Test search functionality
python main_orchestrator.py search

# Test with debug logging
python main_orchestrator.py search --log-level DEBUG

# Validate configuration
python main_orchestrator.py mcp --validate-config
```

## 📊 Monitoring

### Health Checks

```bash
# Check service health
python -c "
import asyncio
from search.service import create_search_service

async def check():
    service = create_search_service()
    health = await service.health_check()
    print(health)

asyncio.run(check())
"

# Verify ingestion data
python scripts/verify_ingestion.py
```

### Statistics

The service provides comprehensive stats about indexed messages:

- Total vectors indexed
- Channels covered
- Last refresh time
- Service health status

## 🔒 Security

The new architecture maintains the security features of v1.x:

- Environment variable configuration
- Rate limiting on Slack API calls
- Input validation and sanitization
- Secure embedding generation

## 📈 Performance

### Optimizations

- **Caching**: Search results and metadata cached for 5 minutes
- **Lazy Loading**: Services initialized only when needed
- **Efficient Queries**: Optimized vector search parameters
- **Background Processing**: Ingestion doesn't block search

### Scaling

- **Horizontal**: Run multiple ingestion workers
- **Vertical**: Independent search service scaling
- **Caching**: Built-in result caching
- **Monitoring**: Health checks and statistics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes in the appropriate component directory
4. Test with `python main_orchestrator.py search`
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Slack Chatter Service 2.0** - Intelligent Slack search powered by AI 🚀 