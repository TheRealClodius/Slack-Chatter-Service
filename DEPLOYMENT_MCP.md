# MCP Tool Deployment Guide

## 🚀 How to Deploy Slack Chatter Service as an MCP Tool

The Slack Chatter Service supports two MCP deployment modes:
1. **Local MCP (stdio)** - Traditional subprocess execution with JSON-RPC over stdin/stdout
2. **MCP Remote Protocol** - OAuth 2.1 + SSE server for remote authenticated access

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

The MCP deployment guide now provides comprehensive coverage of both local stdio and remote OAuth 2.1 deployment options, with complete working examples for production use.

## 🔧 Enhanced Authentication Flow

### PKCE Implementation Details

PKCE (Proof Key for Code Exchange) prevents authorization code interception attacks:

```python
import secrets
import base64
import hashlib

def generate_pkce_pair():
    """Generate PKCE verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge
```

### Complete Authentication Flow

```python
import asyncio
import json
import httpx
import secrets
import base64
import hashlib
from urllib.parse import urlencode

class MCPAuthenticatedClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = None
    
    def generate_pkce_pair(self):
        """Generate PKCE verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    async def authenticate(self, redirect_uri: str = "http://localhost:3000/callback"):
        """Perform complete OAuth 2.1 authentication"""
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        # Start authorization
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "mcp:search mcp:channels mcp:stats",
            "state": secrets.token_urlsafe(32),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{self.base_url}/oauth/authorize?" + urlencode(auth_params)
        print(f"Visit: {auth_url}")
        
        # Get authorization code (in practice, this comes from redirect)
        auth_code = input("Enter authorization code: ")
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code_verifier": code_verifier
            }
            
            response = await client.post(f"{self.base_url}/oauth/token", data=token_data)
            
            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")
            
            token_result = response.json()
            self.access_token = token_result["access_token"]
            
            # Calculate expiration time
            import time
            self.token_expires_at = time.time() + token_result.get("expires_in", 3600)
            
            return token_result
    
    def is_token_valid(self):
        """Check if current token is still valid"""
        if not self.access_token:
            return False
        
        import time
        return time.time() < (self.token_expires_at or 0)
    
    async def make_mcp_request(self, method: str, params: dict = None):
        """Make authenticated MCP request with automatic token validation"""
        if not self.is_token_valid():
            raise Exception("Token expired or invalid. Re-authenticate required.")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": secrets.randbelow(10000)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/request",
                json=request_data,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            result = response.json()
            
            # Check for errors
            if "error" in result:
                raise MCPError(result["error"])
            
            return result
    
    async def search_messages(self, query: str, **kwargs):
        """Search Slack messages with error handling"""
        return await self.make_mcp_request(
            "tools/call",
            {
                "name": "search_slack_messages",
                "arguments": {"query": query, **kwargs}
            }
        )
    
    async def get_channels(self):
        """Get available channels"""
        return await self.make_mcp_request(
            "tools/call",
            {
                "name": "get_slack_channels",
                "arguments": {}
            }
        )
    
    async def get_stats(self):
        """Get search statistics"""
        return await self.make_mcp_request(
            "tools/call",
            {
                "name": "get_search_stats",
                "arguments": {}
            }
        )

class MCPError(Exception):
    """Custom exception for MCP errors"""
    def __init__(self, error_data):
        self.code = error_data.get("code")
        self.message = error_data.get("message")
        self.data = error_data.get("data")
        super().__init__(f"MCP Error {self.code}: {self.message}")

## 🚨 Error Handling

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| -32001 | Authentication failed | Check token validity, re-authenticate |
| -32002 | Insufficient scope | Request proper scopes during auth |
| -32003 | Invalid request | Check JSON-RPC format and parameters |
| -32004 | Service unavailable | Ensure ingestion has run, check service health |
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
      "details": "Token expired",
      "expires_at": "2024-01-01T12:00:00Z"
    }
  }
}
```

### Error Handling Example

```python
import asyncio
import time

async def robust_search(client, query, max_retries=3):
    """Search with robust error handling and retries"""
    for attempt in range(max_retries):
        try:
            return await client.search_messages(query)
            
        except MCPError as e:
            if e.code == -32001:  # Authentication failed
                print("Token expired, re-authenticating...")
                await client.authenticate()
                continue
                
            elif e.code == -32005:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
                
            else:
                print(f"Unhandled error: {e}")
                raise
                
        except Exception as e:
            print(f"Network error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
    
    raise Exception(f"Failed after {max_retries} attempts")
```

## 🧪 Testing Framework

### Unit Tests

```python
import pytest
import asyncio
from unittest.mock import Mock, patch

class TestMCPClient:
    @pytest.fixture
    async def client(self):
        return MCPAuthenticatedClient(
            base_url="http://localhost:8080",
            client_id="test-client",
            client_secret="test-secret"
        )
    
    @pytest.mark.asyncio
    async def test_pkce_generation(self, client):
        """Test PKCE generation"""
        verifier, challenge = client.generate_pkce_pair()
        
        assert len(verifier) >= 43
        assert len(challenge) >= 43
        assert verifier != challenge
    
    @pytest.mark.asyncio
    async def test_search_messages(self, client):
        """Test message search"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"messages": []}
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Set valid token
            client.access_token = "test-token"
            client.token_expires_at = time.time() + 3600
            
            result = await client.search_messages("test query")
            assert "result" in result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32001,
                    "message": "Authentication failed"
                }
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client.access_token = "invalid-token"
            client.token_expires_at = time.time() + 3600
            
            with pytest.raises(MCPError) as exc_info:
                await client.search_messages("test")
            
            assert exc_info.value.code == -32001
```

### Integration Tests

```python
@pytest.mark.integration
async def test_full_oauth_flow():
    """Test complete OAuth 2.1 flow"""
    client = MCPAuthenticatedClient(
        base_url="http://localhost:8080",
        client_id="mcp-slack-chatter-client",
        client_secret=os.getenv("CLIENT_SECRET")
    )
    
    # This would require manual intervention in real tests
    # In CI/CD, you'd mock the authorization step
    if not os.getenv("CI"):
        await client.authenticate()
        
        # Test all endpoints
        channels = await client.get_channels()
        assert "result" in channels
        
        stats = await client.get_stats()
        assert "result" in stats
        
        results = await client.search_messages("test", top_k=1)
        assert "result" in results
```

## 📋 Best Practices

### Security Best Practices

1. **Token Storage**: Store tokens securely, never in plain text
   ```python
   import keyring
   
   # Store token securely
   keyring.set_password("mcp-slack-chatter", "access_token", token)
   
   # Retrieve token
   token = keyring.get_password("mcp-slack-chatter", "access_token")
   ```

2. **Token Rotation**: Implement automatic token refresh
   ```python
   async def ensure_valid_token(self):
       if not self.is_token_valid():
           await self.authenticate()
   ```

3. **Scope Limitation**: Request only required scopes
   ```python
   # Good: Specific scopes
   scope = "mcp:search"
   
   # Bad: All scopes
   scope = "mcp:search mcp:channels mcp:stats"
   ```

### Performance Best Practices

1. **Connection Pooling**: Reuse HTTP connections
   ```python
   # Use session for multiple requests
   async with httpx.AsyncClient() as session:
       for query in queries:
           await make_request(session, query)
   ```

2. **Request Batching**: Batch multiple searches when possible
   ```python
   async def batch_search(queries):
       tasks = [client.search_messages(q) for q in queries]
       return await asyncio.gather(*tasks)
   ```

3. **Caching**: Cache frequent requests
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   async def cached_search(query):
       return await client.search_messages(query)
   ```

### Integration Best Practices

1. **Graceful Degradation**: Handle service unavailability
   ```python
   try:
       results = await client.search_messages(query)
   except MCPError:
       # Fallback to alternative search
       results = await fallback_search(query)
   ```

2. **Rate Limiting**: Respect API limits
   ```python
   import asyncio
   from asyncio import Semaphore
   
   # Limit concurrent requests
   semaphore = Semaphore(5)
   
   async def rate_limited_search(query):
       async with semaphore:
           return await client.search_messages(query)
   ```

3. **Monitoring**: Log requests and responses
   ```python
   import logging
   
   logger = logging.getLogger(__name__)
   
   async def logged_search(query):
       logger.info(f"Searching for: {query}")
       try:
           result = await client.search_messages(query)
           logger.info(f"Found {len(result.get('result', {}).get('messages', []))} messages")
           return result
       except Exception as e:
           logger.error(f"Search failed: {e}")
           raise
   ```

## 🔍 Production Deployment Checklist

### Environment Setup
- [ ] All environment variables configured
- [ ] OAuth client registered with proper redirect URIs
- [ ] HTTPS enabled for production
- [ ] CORS configured for client domains
- [ ] Rate limiting implemented

### Security Configuration
- [ ] Client secrets stored securely
- [ ] Token expiration properly configured
- [ ] Scopes limited to minimum required
- [ ] Input validation implemented
- [ ] Audit logging enabled

### Monitoring & Observability
- [ ] Health checks implemented
- [ ] Metrics collection enabled
- [ ] Error tracking configured
- [ ] Performance monitoring set up
- [ ] Log aggregation configured

### Testing & Validation
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Load testing completed
- [ ] Security testing performed
- [ ] Documentation validated

The MCP deployment guide now provides comprehensive coverage of deployment, integration, authentication, error handling, testing, and best practices for both local stdio and remote OAuth 2.1 deployment options. 