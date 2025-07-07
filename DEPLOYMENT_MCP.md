# MCP Streamable HTTP Deployment Guide

## 🚀 MCP Streamable HTTP Standard (March 2025)

The Slack Chatter Service now implements the **latest MCP Streamable HTTP standard** with modern features:

### ✨ Key Features
- **Single endpoint** (`/mcp`) supporting both GET and POST requests
- **Session management** via `mcp-session-id` headers
- **JSON-RPC 2.0 protocol** compliance
- **Bidirectional communication** support
- **Simplified authentication** (API keys, OAuth tokens)

### 🔄 Deployment Models

1. **Local MCP (stdio)** - Traditional subprocess execution with JSON-RPC over stdin/stdout
2. **MCP Streamable HTTP** - Modern single-endpoint server with session headers

## 🛠️ Available MCP Tools

### 1. search_slack_messages

**Description**: Semantic search through Slack messages with AI-powered query enhancement

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query for finding relevant messages",
      "minLength": 1,
      "maxLength": 1000
    },
    "top_k": {
      "type": "integer",
      "description": "Number of results to return (1-50)",
      "minimum": 1,
      "maximum": 50,
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
      "description": "Filter messages from this date (YYYY-MM-DD)",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "date_to": {
      "type": "string",
      "description": "Filter messages to this date (YYYY-MM-DD)",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    }
  },
  "required": ["query"]
}
```

**Example Usage**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_slack_messages",
    "arguments": {
      "query": "deployment issues last week",
      "top_k": 5,
      "channel_filter": "engineering"
    }
  },
  "id": 1
}
```

### 2. get_slack_channels

**Description**: Get list of available Slack channels

**Input Schema**:
```json
{
  "type": "object",
  "properties": {}
}
```

**Example Usage**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_slack_channels",
    "arguments": {}
  },
  "id": 2
}
```

### 3. get_search_stats

**Description**: Get statistics about indexed Slack messages

**Input Schema**:
```json
{
  "type": "object",
  "properties": {}
}
```

**Example Usage**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_search_stats",
    "arguments": {}
  },
  "id": 3
}
```

## 🎯 Client Configuration Guide

### MCP Client Structure (March 2025 Standard)

The new Streamable HTTP standard requires specific client configurations:

#### 1. Local MCP Configuration (stdio)

**For Claude Desktop, Cline, or other MCP clients:**

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

#### 2. Remote MCP Configuration (Streamable HTTP)

**For modern MCP clients supporting HTTP transport:**

```json
{
  "mcpServers": {
    "slack-chatter-remote": {
      "transport": "http",
      "endpoint": "https://your-deployment.com/mcp",
      "authentication": {
        "type": "bearer",
        "token": "mcp_key_your_api_key_here"
      },
      "options": {
        "standard": "streamable-http-2025",
        "session_management": true,
        "supports_get": true,
        "supports_post": true
      }
    }
  }
}
```

#### 3. Legacy/Transitional Configuration

**For older MCP clients (if needed):**

```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "python3",
      "args": ["/path/to/slack-chatter-service/main_orchestrator.py", "mcp"],
      "cwd": "/path/to/slack-chatter-service",
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token",
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

### Client Implementation Examples

#### Python Client (Streamable HTTP)

```python
import asyncio
import httpx
import json
from typing import Dict, Optional

class MCPStreamableClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id: Optional[str] = None
        self.client = httpx.AsyncClient()
    
    async def _make_request(self, method: str, data: Dict) -> Dict:
        """Make an MCP request with session management"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Add session ID if we have one
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        
        response = await self.client.post(
            f"{self.base_url}/mcp",
            json=data,
            headers=headers
        )
        
        # Extract session ID from response
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self.session_id = session_id
        
        return response.json()
    
    async def initialize(self) -> Dict:
        """Initialize MCP session"""
        return await self._make_request("initialize", {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        })
    
    async def list_tools(self) -> Dict:
        """List available MCP tools"""
        return await self._make_request("tools/list", {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        })
    
    async def search_messages(self, query: str, top_k: int = 10, **kwargs) -> Dict:
        """Search Slack messages"""
        return await self._make_request("tools/call", {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_slack_messages",
                "arguments": {"query": query, "top_k": top_k, **kwargs}
            },
            "id": 3
        })
    
    async def get_channels(self) -> Dict:
        """Get available Slack channels"""
        return await self._make_request("tools/call", {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_slack_channels",
                "arguments": {}
            },
            "id": 4
        })
    
    async def get_stats(self) -> Dict:
        """Get search statistics"""
        return await self._make_request("tools/call", {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_search_stats",
                "arguments": {}
            },
            "id": 5
        })
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()

# Usage example
async def main():
    client = MCPStreamableClient(
        base_url="https://your-deployment.com",
        api_key="mcp_key_your_api_key_here"
    )
    
    try:
        # Initialize
        await client.initialize()
        
        # List tools
        tools = await client.list_tools()
        print("Available tools:", tools)
        
        # Search messages
        results = await client.search_messages("deployment issues", top_k=5)
        print("Search results:", results)
        
        # Get channels
        channels = await client.get_channels()
        print("Channels:", channels)
        
        # Get stats
        stats = await client.get_stats()
        print("Stats:", stats)
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

#### JavaScript Client (Streamable HTTP)

```javascript
class MCPStreamableClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.sessionId = null;
    }
    
    async _makeRequest(method, data) {
        const headers = {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
        };
        
        // Add session ID if we have one
        if (this.sessionId) {
            headers['mcp-session-id'] = this.sessionId;
        }
        
        const response = await fetch(`${this.baseUrl}/mcp`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        
        // Extract session ID from response
        const sessionId = response.headers.get('mcp-session-id');
        if (sessionId) {
            this.sessionId = sessionId;
        }
        
        return response.json();
    }
    
    async initialize() {
        return this._makeRequest('initialize', {
            jsonrpc: '2.0',
            method: 'initialize',
            params: {},
            id: 1
        });
    }
    
    async listTools() {
        return this._makeRequest('tools/list', {
            jsonrpc: '2.0',
            method: 'tools/list',
            params: {},
            id: 2
        });
    }
    
    async searchMessages(query, topK = 10, options = {}) {
        return this._makeRequest('tools/call', {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'search_slack_messages',
                arguments: { query, top_k: topK, ...options }
            },
            id: 3
        });
    }
    
    async getChannels() {
        return this._makeRequest('tools/call', {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'get_slack_channels',
                arguments: {}
            },
            id: 4
        });
    }
    
    async getStats() {
        return this._makeRequest('tools/call', {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'get_search_stats',
                arguments: {}
            },
            id: 5
        });
    }
    
    // Alternative: GET request (simplified)
    async simpleSearch(query) {
        const headers = { 'Authorization': `Bearer ${this.apiKey}` };
        if (this.sessionId) {
            headers['mcp-session-id'] = this.sessionId;
        }
        
        const params = new URLSearchParams({
            method: 'tools/call',
            name: 'search_slack_messages',
            query: query,
            top_k: 5
        });
        
        const response = await fetch(`${this.baseUrl}/mcp?${params}`, {
            headers
        });
        
        return response.json();
    }
}

// Usage
const client = new MCPStreamableClient(
    'https://your-deployment.com',
    'mcp_key_your_api_key_here'
);

// Initialize and search
await client.initialize();
const results = await client.searchMessages('deployment issues', 5);
console.log(results);
```

## 🔧 Authentication & Session Management

### Authentication Methods

#### 1. API Key Authentication (Recommended)

```bash
# Header format
Authorization: Bearer mcp_key_generated_key_here

# Example request
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer mcp_key_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

#### 2. OAuth Token Authentication

```bash
# Header format
Authorization: Bearer oauth_token_here

# Example request
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer oauth_token_xyz789..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Session Management

After initial authentication, use the `mcp-session-id` header:

```bash
# Session-based request
curl -X GET "https://your-deployment.com/mcp?method=tools/list" \
  -H "mcp-session-id: mcp_session_generated_id"
```

### Getting Your API Key

**Development Environment:**
```bash
# Visit the dev endpoint
curl https://your-deployment.com/dev/api-key

# Response:
{
  "api_key": "mcp_key_abc123...",
  "note": "This is for development only.",
  "usage": "Authorization: Bearer mcp_key_abc123..."
}
```

**Production Environment:**
API keys should be managed through secure configuration or environment variables.

## 🌐 Deployment Methods

### 1. Local Development

```bash
# Run stdio MCP server
python main_orchestrator.py mcp

# Run Streamable HTTP server
python main_orchestrator.py remote

# Combined mode (ingestion + stdio)
python main_orchestrator.py combined
```

### 2. Docker Deployment

#### Single Container
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

ENV SLACK_BOT_TOKEN=""
ENV OPENAI_API_KEY=""
ENV PINECONE_API_KEY=""
ENV PINECONE_ENVIRONMENT=""
ENV NOTION_INTEGRATION_SECRET=""
ENV NOTION_DATABASE_ID=""
ENV SLACK_CHANNELS=""

EXPOSE 8080
CMD ["python", "main_orchestrator.py", "remote"]
```

#### Multi-Container Setup
```yaml
version: '3.8'
services:
  mcp-streamable:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
      - NOTION_INTEGRATION_SECRET=${NOTION_INTEGRATION_SECRET}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - SLACK_CHANNELS=${SLACK_CHANNELS}
    command: ["python", "main_orchestrator.py", "remote"]
    restart: unless-stopped
```

### 3. Cloud Deployment

#### Replit
```bash
# Visit: https://replit.com
# Import from GitHub
# Add environment variables in Secrets
# Run: python main_orchestrator.py remote
# Enable Always On
```

#### Railway
```bash
# Visit: https://railway.app
# Deploy from GitHub
# Set start command: python main_orchestrator.py remote
# Configure port: 8080
# Add environment variables
```

#### Render
```bash
# Visit: https://render.com
# Create Web Service
# Set start command: python main_orchestrator.py remote
# Configure port: 8080
# Add environment variables
```

## 📡 API Endpoints

### Core MCP Endpoint

**`/mcp` (GET & POST)**
- **Purpose**: Single endpoint for all MCP communication
- **Methods**: GET, POST
- **Authentication**: Bearer token or session ID
- **Content-Type**: application/json (for POST)

**Example POST:**
```bash
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer mcp_key_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_slack_messages",
      "arguments": {
        "query": "deployment issues",
        "top_k": 5
      }
    },
    "id": 1
  }'
```

**Example GET:**
```bash
curl "https://your-deployment.com/mcp?method=tools/list&id=1" \
  -H "Authorization: Bearer mcp_key_abc123..."
```

### Utility Endpoints

**`/health`** - Health check
```bash
curl https://your-deployment.com/health
```

**`/info`** - Server information
```bash
curl https://your-deployment.com/info
```

**`/session/{session_id}`** - Session information
```bash
curl https://your-deployment.com/session/mcp_session_abc123
```

**`/dev/api-key`** - Development API key (remove in production)
```bash
curl https://your-deployment.com/dev/api-key
```

## 🔍 Testing and Validation

### Local Testing

```bash
# Test stdio MCP server
python main_orchestrator.py mcp --validate-config

# Test with echo
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | python main_orchestrator.py mcp
```

### Remote Testing

```bash
# Test server health
curl https://your-deployment.com/health

# Test authentication (should fail)
curl -X POST https://your-deployment.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test with authentication
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer mcp_key_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## 🚨 Error Handling

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| -32001 | Authentication failed | Check API key validity |
| -32002 | Server not initialized | Ensure server is running |
| -32003 | Invalid request | Check JSON-RPC format |
| -32004 | Service unavailable | Ensure ingestion has run |
| -32005 | Rate limit exceeded | Implement backoff strategy |

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Authentication failed",
    "data": {
      "details": "Invalid API key"
    }
  }
}
```

### Robust Error Handling

```python
async def robust_mcp_call(client, method, params, max_retries=3):
    """Make MCP call with robust error handling"""
    for attempt in range(max_retries):
        try:
            return await client._make_request(method, {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": attempt + 1
            })
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## 📊 Performance Optimization

### Connection Pooling

```python
# Reuse HTTP connections
async with httpx.AsyncClient() as client:
    # Make multiple requests with the same client
    results = await asyncio.gather(
        *[make_request(client, query) for query in queries]
    )
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search_results(query: str, top_k: int):
    # Cache frequent searches
    return search_results
```

### Rate Limiting

```python
import asyncio
from asyncio import Semaphore

# Limit concurrent requests
semaphore = Semaphore(5)

async def rate_limited_request(client, data):
    async with semaphore:
        return await client._make_request("search", data)
```

## 🔒 Security Best Practices

### Production Security

1. **API Key Management**
   - Store securely (environment variables, key management systems)
   - Rotate regularly
   - Use different keys for different environments

2. **Session Security**
   - Sessions expire after 24 hours
   - Use HTTPS in production
   - Validate session IDs

3. **Input Validation**
   - All query parameters are validated
   - JSON-RPC format is enforced
   - Request size limits are implemented

4. **Network Security**
   - Enable CORS for specific origins only
   - Use firewall rules to restrict access
   - Implement rate limiting

### Development Security

1. **Environment Variables**
   - Never commit secrets to version control
   - Use `.env` files for local development
   - Use different keys for development/production

2. **API Key Exposure**
   - Remove `/dev/api-key` endpoint in production
   - Log API key usage for monitoring
   - Implement key rotation strategies

## 🎯 Deployment Mode Comparison

| Feature | Local MCP (stdio) | MCP Streamable HTTP |
|---------|-------------------|---------------------|
| **Transport** | stdin/stdout | HTTP/HTTPS |
| **Authentication** | None | API keys/OAuth |
| **Session Management** | None | Header-based |
| **Deployment** | No server needed | Web server required |
| **Scalability** | Single process | Multi-client |
| **Network** | Local only | Remote access |
| **Protocol** | JSON-RPC over stdio | JSON-RPC over HTTP |
| **Best For** | Development, MCP clients | Production, web apps |

## 📋 Production Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] API keys generated and secured
- [ ] HTTPS enabled
- [ ] CORS configured for production domains
- [ ] Rate limiting implemented
- [ ] Session management configured

### Post-Deployment
- [ ] Health checks passing
- [ ] API key accessible via secure method
- [ ] Session creation working
- [ ] All MCP tools responding
- [ ] Error handling working correctly
- [ ] Performance metrics acceptable

### Monitoring
- [ ] Request/response logging enabled
- [ ] Error rate monitoring
- [ ] API key usage tracking
- [ ] Session lifecycle monitoring
- [ ] Performance metrics collection

The MCP Streamable HTTP deployment guide provides comprehensive coverage of the new March 2025 standard with clear client implementation examples and security best practices. 