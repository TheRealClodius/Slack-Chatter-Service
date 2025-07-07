# MCP Tool Deployment Guide

## 🚀 How to Deploy Slack Chatter Service as an MCP Tool

The Slack Chatter Service supports two MCP deployment modes:
1. **Local MCP (stdio)** - Traditional subprocess execution with JSON-RPC over stdin/stdout
2. **MCP Remote Protocol** - OAuth 2.1 + SSE server for remote authenticated access

## 🎯 MCP Deployment Models

### 1. **Local MCP Package Installation** (Recommended for Development)

The most common way to deploy MCP tools is as installable Python packages:

```bash
# Install the package
pip install slack-chatter-service

# Or for development
pip install -e .
```

**MCP Client Configuration:**
```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "slack-chatter",
      "args": ["mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token",
        "OPENAI_API_KEY": "sk-your-key",
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

### 2. **MCP Remote Protocol Server** (Recommended for Production)

Deploy as a persistent server with OAuth 2.1 authentication and SSE communication:

```bash
# Start the MCP Remote Protocol server
python main_orchestrator.py remote

# Server runs on http://localhost:8080 with:
# - OAuth 2.1 authentication with PKCE
# - Server-Sent Events for real-time communication
# - Scoped permissions: mcp:search, mcp:channels, mcp:stats
# - Session management with token expiration
```

**Available Endpoints:**
- `/.well-known/oauth-authorization-server` - OAuth 2.1 discovery
- `/oauth/authorize` - Authorization endpoint
- `/oauth/token` - Token exchange
- `/mcp/sse` - Server-Sent Events communication
- `/mcp/request` - Direct MCP JSON-RPC requests
- `/mcp/session` - Session information
- `/health` - Health check
- `/docs` - API documentation

**Client Integration:**
```python
from mcp_remote_client import MCPRemoteClient

client = MCPRemoteClient(
    base_url="https://your-deployment.com",
    client_id="mcp-slack-chatter-client",
    client_secret="your_client_secret"  # Get from server logs
)

await client.authenticate()
results = await client.search_messages("deployment issues")
```

### 3. **Direct Python Execution** (Local Development)

For development or custom installations:

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

### 4. **Docker Container Deployment** (Recommended for Production)

#### Local MCP Container
```dockerfile
# Dockerfile.mcp
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# Set environment variables
ENV SLACK_BOT_TOKEN=""
ENV OPENAI_API_KEY=""
ENV PINECONE_API_KEY=""
ENV PINECONE_ENVIRONMENT=""
ENV NOTION_INTEGRATION_SECRET=""
ENV NOTION_DATABASE_ID=""
ENV SLACK_CHANNELS=""

ENTRYPOINT ["slack-chatter", "mcp"]
```

**MCP Client Configuration:**
```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "slack-chatter-service:latest"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token",
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### MCP Remote Protocol Container
```dockerfile
# Dockerfile.remote
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# Set environment variables
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

### 5. **Cloud Deployment Options**

#### Railway (Recommended)
```bash
# Deploy MCP Remote Protocol server
railway deploy
# Set start command: python main_orchestrator.py remote
# Configure environment variables
# Enable domain for OAuth redirects
```

#### Render
```bash
# Create Web Service
# Set start command: python main_orchestrator.py remote
# Configure port: 8080
# Add environment variables
```

#### Replit
```bash
# Import from GitHub
# Add environment variables in Secrets
# Run: python main_orchestrator.py remote
# Enable Always On
```

### 6. **Hybrid Deployment** (Background Worker + MCP Server)

For complete functionality, deploy both ingestion worker and MCP server:

```yaml
# docker-compose.yml
version: '3.8'

services:
  ingestion-worker:
    build: .
    command: ["python", "main_orchestrator.py", "ingestion"]
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... other env vars
    restart: unless-stopped

  mcp-remote-server:
    build: .
    command: ["python", "main_orchestrator.py", "remote"]
    ports:
      - "8080:8080"
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... other env vars
    restart: unless-stopped
```

### 7. **Standalone Server Mode**

For shared team usage, run as a persistent background service:

```bash
# Combined mode: runs both ingestion and MCP stdio server
slack-chatter combined

# Or separate processes:
slack-chatter ingestion &  # Background ingestion
slack-chatter remote       # MCP Remote Protocol server
```

## 🔧 MCP Client Examples

### Claude Desktop Configuration

#### Local MCP (stdio)
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "slack-chatter",
      "args": ["mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token",
        "OPENAI_API_KEY": "sk-your-key",
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

#### Remote MCP (OAuth 2.1)
For remote access, use the MCP Remote Protocol client:

```python
from mcp_remote_client import MCPRemoteClient

client = MCPRemoteClient(
    base_url="https://your-deployment.replit.app",
    client_id="mcp-slack-chatter-client",
    client_secret="your_client_secret"
)

await client.authenticate()
results = await client.search_messages("deployment issues")
```

### Custom Agent Configuration

#### Local MCP
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

#### Remote MCP (Production)
```javascript
// JavaScript/Node.js example
const { MCPRemoteClient } = require('mcp-remote-client');

const client = new MCPRemoteClient({
  baseUrl: 'https://your-deployment.railway.app',
  clientId: 'mcp-slack-chatter-client',
  clientSecret: process.env.MCP_CLIENT_SECRET
});

await client.authenticate();
const results = await client.searchMessages('deployment issues');
```

**Required Environment Variables:**
- `SLACK_BOT_TOKEN` - Your Slack bot token (starts with `xoxb-`)
- `OPENAI_API_KEY` - Your OpenAI API key (starts with `sk-`)
- `SLACK_CHANNELS` - Comma-separated channel IDs where your bot is a member
- `PINECONE_API_KEY` - Your Pinecone API key
- `PINECONE_ENVIRONMENT` - Your Pinecone environment (e.g., `us-west1-gcp`)
- `NOTION_INTEGRATION_SECRET` - Your Notion integration secret
- `NOTION_DATABASE_ID` - Your Notion database ID

### Cline/Continue Configuration

#### Local MCP
```json
{
  "mcp": {
    "servers": {
      "slack-chatter": {
        "command": "slack-chatter",
        "args": ["mcp"],
        "env": {
          "SLACK_BOT_TOKEN": "xoxb-your-token",
          "OPENAI_API_KEY": "sk-your-key"
        }
      }
    }
  }
}
```

#### Remote MCP (Advanced)
```typescript
// TypeScript example for custom integrations
import { MCPRemoteClient } from 'mcp-remote-client';

const client = new MCPRemoteClient({
  baseUrl: 'https://your-deployment.render.com',
  clientId: 'mcp-slack-chatter-client',
  clientSecret: process.env.MCP_CLIENT_SECRET,
  scopes: ['mcp:search', 'mcp:channels', 'mcp:stats']
});

// Initialize OAuth 2.1 flow
await client.authenticate();

// Use MCP tools
const channels = await client.getSlackChannels();
const results = await client.searchSlackMessages('authentication errors');
const stats = await client.getSearchStats();
```

## 🔐 OAuth 2.1 Authentication Flow

### Client Registration

The MCP Remote Protocol server automatically registers a default OAuth client on startup:

```
Client ID: mcp-slack-chatter-client
Client Secret: <generated-on-startup>
Scopes: mcp:search, mcp:channels, mcp:stats
Redirect URIs: 
  - http://localhost:3000/callback
  - https://*.replit.app/callback
  - https://*.railway.app/callback
  - https://*.render.com/callback
```

### Authorization Flow

1. **Authorization URL**: `GET /oauth/authorize`
   ```
   https://your-deployment.com/oauth/authorize?
     response_type=code&
     client_id=mcp-slack-chatter-client&
     redirect_uri=http://localhost:3000/callback&
     scope=mcp:search+mcp:channels+mcp:stats&
     state=random_state&
     code_challenge=CODE_CHALLENGE&
     code_challenge_method=S256
   ```

2. **Token Exchange**: `POST /oauth/token`
   ```bash
   curl -X POST https://your-deployment.com/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code" \
     -d "code=AUTHORIZATION_CODE" \
     -d "redirect_uri=http://localhost:3000/callback" \
     -d "client_id=mcp-slack-chatter-client" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "code_verifier=CODE_VERIFIER"
   ```

3. **Access Token Response**:
   ```json
   {
     "access_token": "mcp_access_token_...",
     "token_type": "Bearer",
     "expires_in": 86400,
     "scope": "mcp:search mcp:channels mcp:stats"
   }
   ```

### Using Access Tokens

#### Direct MCP Requests
```bash
curl -X POST https://your-deployment.com/mcp/request \
  -H "Authorization: Bearer mcp_access_token_..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_slack_messages",
      "arguments": {
        "query": "deployment issues",
        "top_k": 10
      }
    },
    "id": 1
  }'
```

#### Server-Sent Events (SSE)
```javascript
const eventSource = new EventSource(
  'https://your-deployment.com/mcp/sse?access_token=mcp_access_token_...'
);

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('MCP Response:', data);
};

// Send MCP request via SSE
const request = {
  jsonrpc: "2.0",
  method: "tools/call",
  params: {
    name: "search_slack_messages",
    arguments: { query: "authentication errors" }
  },
  id: 1
};

eventSource.addEventListener('open', function() {
  // Send request (implementation depends on SSE library)
  sendSSERequest(request);
});
```

## 🎯 Deployment Mode Comparison

| Feature | Local MCP (stdio) | MCP Remote Protocol |
|---------|-------------------|---------------------|
| **Authentication** | None | OAuth 2.1 + PKCE |
| **Communication** | stdin/stdout | HTTP + SSE |
| **Deployment** | Subprocess | Web server |
| **Scalability** | Single process | Multi-client |
| **Security** | Process isolation | Token-based |
| **Best For** | Development, MCP clients | Production, web apps |
| **Port** | None | 8080 |
| **Setup Complexity** | Low | Medium |

## 🚀 Production Deployment Recommendations

### Small Teams (< 10 users)
- **Local MCP**: Use stdio mode with shared package installation
- **Remote MCP**: Deploy to Replit or Railway for simple web access

### Medium Teams (10-100 users)
- **Hybrid**: Deploy both ingestion worker and MCP Remote Protocol server
- **Platforms**: Railway, Render, or Docker containers
- **Authentication**: OAuth 2.1 with proper redirect URIs

### Large Teams (100+ users)
- **Dedicated Infrastructure**: VPS or cloud deployment
- **Load Balancing**: Multiple MCP Remote Protocol server instances
- **Authentication**: Integrate with corporate SSO (future feature)
- **Monitoring**: Comprehensive logging and metrics

## 🔍 Testing and Validation

### Local MCP Testing
```bash
# Test local MCP server
python main_orchestrator.py mcp --validate-config

# Test with MCP client
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | python main_orchestrator.py mcp
```

### Remote MCP Testing
```bash
# Test OAuth discovery
curl https://your-deployment.com/.well-known/oauth-authorization-server

# Test health endpoint
curl https://your-deployment.com/health

# Test unauthorized access (should fail)
curl -X POST https://your-deployment.com/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test with proper OAuth flow
# (Use client libraries for full OAuth implementation)
```

## 📊 Performance and Monitoring

### Metrics to Monitor
- **Token usage**: Track OAuth token generation and validation
- **Request latency**: Monitor MCP request/response times
- **Error rates**: Track authentication failures and MCP errors
- **Resource usage**: Monitor CPU, memory, and network usage

### Logging Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for development
logging.getLogger('mcp.server').setLevel(logging.DEBUG)
logging.getLogger('mcp.fastapi_app').setLevel(logging.DEBUG)
```

## 🔒 Security Considerations

### Production Security Checklist
- [ ] **HTTPS only** for OAuth 2.1 flows
- [ ] **Client secret rotation** on regular basis
- [ ] **Token expiration** properly configured (24 hours)
- [ ] **CORS restrictions** properly configured
- [ ] **Rate limiting** implemented for OAuth endpoints
- [ ] **Input validation** for all MCP parameters
- [ ] **Audit logging** for authentication events
- [ ] **Network security** (firewalls, VPN access)

### Development Security
- [ ] **Environment variables** for all secrets
- [ ] **No hardcoded credentials** in source code
- [ ] **Secure local development** environment
- [ ] **Regular dependency updates** via `uv sync`

The MCP deployment guide now covers both local stdio and remote OAuth 2.1 deployment options, providing flexibility for different use cases and team sizes.

## 💻 Complete Client Integration Examples

### Python Client Example (httpx + SSE)

```python
import asyncio
import json
import httpx
from sse_starlette import EventSourceResponse

class MCPRemoteClient:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    async def search_messages(self, query: str, top_k: int = 10):
        """Search Slack messages"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_slack_messages",
                "arguments": {"query": query, "top_k": top_k}
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/request",
                json=request_data,
                headers=self.headers
            )
            return response.json()
    
    async def connect_sse(self):
        """Connect to SSE endpoint"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{self.base_url}/mcp/sse",
                headers=self.headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        yield data

# Usage
async def main():
    client = MCPRemoteClient("http://localhost:8080", "your_access_token")
    
    # Search messages
    results = await client.search_messages("deployment issues")
    print(json.dumps(results, indent=2))
    
    # Connect to SSE
    async for event in client.connect_sse():
        print(f"Received: {event}")

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript Client Example (Complete OAuth 2.1 Flow)

```javascript
// PKCE helper functions
function generateCodeVerifier() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return base64URLEncode(array);
}

async function generateCodeChallenge(codeVerifier) {
    const data = new TextEncoder().encode(codeVerifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return base64URLEncode(new Uint8Array(digest));
}

function base64URLEncode(array) {
    return btoa(String.fromCharCode(...array))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

// OAuth 2.1 flow
async function getAccessToken() {
    const clientId = 'mcp-slack-chatter-client';
    const clientSecret = 'your_client_secret';
    const redirectUri = 'http://localhost:3000/callback';
    
    // Generate PKCE
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    
    // Start authorization
    const authUrl = `http://localhost:8080/oauth/authorize?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=mcp:search+mcp:channels+mcp:stats&state=random_state&code_challenge=${codeChallenge}&code_challenge_method=S256`;
    
    // User visits authUrl and gets authorization code
    const authCode = 'received_from_redirect';
    
    // Exchange code for token
    const tokenResponse = await fetch('http://localhost:8080/oauth/token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: authCode,
            redirect_uri: redirectUri,
            client_id: clientId,
            client_secret: clientSecret,
            code_verifier: codeVerifier
        })
    });
    
    const tokenData = await tokenResponse.json();
    return tokenData.access_token;
}

// MCP client
class MCPRemoteClient {
    constructor(baseUrl, accessToken) {
        this.baseUrl = baseUrl;
        this.accessToken = accessToken;
    }
    
    async searchMessages(query, topK = 10) {
        const response = await fetch(`${this.baseUrl}/mcp/request`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tools/call',
                params: {
                    name: 'search_slack_messages',
                    arguments: { query, top_k: topK }
                },
                id: 1
            })
        });
        
        return response.json();
    }
    
    connectSSE() {
        return new EventSource(`${this.baseUrl}/mcp/sse`, {
            headers: {
                'Authorization': `Bearer ${this.accessToken}`
            }
        });
    }
}

// Usage
async function main() {
    const accessToken = await getAccessToken();
    const client = new MCPRemoteClient('http://localhost:8080', accessToken);
    
    // Search messages
    const results = await client.searchMessages('deployment issues');
    console.log(results);
    
    // Connect to SSE
    const eventSource = client.connectSSE();
    eventSource.onmessage = (event) => {
        console.log('Received:', JSON.parse(event.data));
    };
}
```

## 🔍 Advanced Troubleshooting

### OAuth 2.1 Debug Commands

```bash
# Test OAuth discovery
curl http://localhost:8080/.well-known/oauth-authorization-server

# Test health endpoint
curl http://localhost:8080/health

# View OAuth clients (debug endpoint)
curl http://localhost:8080/debug/oauth-clients

# Test MCP request without auth (should fail)
curl -X POST http://localhost:8080/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test with invalid token (should fail)
curl -X POST http://localhost:8080/mcp/request \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Common OAuth Issues

1. **OAuth client not found**: Check the client ID and ensure server is running
2. **Token expired**: Generate a new access token (24-hour expiration)
3. **Invalid PKCE**: Ensure code_verifier and code_challenge are correctly generated
4. **Search service not available**: Ensure ingestion has run and vector database is populated
5. **CORS issues**: Update allowed origins for your client domain
6. **Invalid redirect URI**: Ensure redirect URI matches registered URIs

### Debug Mode

```bash
# Enable debug logging
python main_orchestrator.py remote --log-level DEBUG

# View server logs for OAuth client secret
# Check startup logs for: "Generated OAuth client secret: ..."
```

## ⚡ Performance Optimization

### SSE Connection Management

- **Lightweight connections**: SSE uses less resources than WebSockets
- **Automatic reconnection**: Implement reconnection logic in clients
- **Connection pooling**: Reuse connections when possible
- **Heartbeat mechanism**: Built-in keep-alive for SSE connections

### Token Management

- **Token caching**: Cache tokens locally to avoid repeated OAuth flows
- **Token refresh**: Implement token refresh before expiration
- **Session persistence**: Store session info for reconnection
- **Rate limiting**: Respect OAuth endpoint rate limits

The MCP deployment guide now provides comprehensive coverage of both local stdio and remote OAuth 2.1 deployment options, with complete working examples for production use. 