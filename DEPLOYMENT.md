# Deployment Guide

## Overview

The Slack Chatter Service provides two main deployment modes:
1. **MCP Server (stdio)** - For local client connections via JSON-RPC over stdin/stdout
2. **MCP Remote Protocol** - For remote client connections via OAuth 2.1 and Server-Sent Events

## Prerequisites

- Python 3.11+
- All required API keys configured in environment variables
- Vector database (Pinecone) set up and configured
- Slack app configured with necessary permissions

## MCP Server Mode (Local)

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run MCP server for stdio communication
python3 main_orchestrator.py mcp
```

### Integration with MCP Clients

The MCP server supports the standard MCP protocol over stdio:

```bash
# Connect via stdio
python3 main_orchestrator.py mcp

# Or use with MCP client libraries
mcp-client-connect python3 main_orchestrator.py mcp
```

## MCP Remote Protocol Mode

### Overview

The MCP Remote Protocol implementation provides secure remote access using:
- **OAuth 2.1** for authentication with PKCE
- **Server-Sent Events (SSE)** for real-time bidirectional communication
- **Scoped permissions** for fine-grained access control
- **Session management** with token expiration

### Quick Start

```bash
# Install dependencies with OAuth 2.1 and SSE support
pip install -r requirements.txt

# Run MCP Remote Protocol server
python3 main_orchestrator.py remote
```

### OAuth 2.1 Flow

#### 1. Client Registration

A default OAuth client is automatically registered:
- **Client ID**: `mcp-slack-chatter-client`
- **Client Secret**: Generated on startup (check logs)
- **Scopes**: `mcp:search`, `mcp:channels`, `mcp:stats`
- **Redirect URIs**: `http://localhost:3000/callback`, `https://*.replit.app/callback`

#### 2. Authorization Flow

1. **Get OAuth discovery information**:
   ```bash
   curl http://localhost:8080/.well-known/oauth-authorization-server
   ```

2. **Start authorization** (replace parameters):
   ```bash
   # Generate PKCE verifier and challenge
   CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)
   CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | cut -c1-43)
   
   # Visit authorization URL
   curl "http://localhost:8080/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=random_state&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"
   ```

3. **Exchange code for token**:
   ```bash
   curl -X POST http://localhost:8080/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code&code=YOUR_AUTH_CODE&redirect_uri=http://localhost:3000/callback&client_id=mcp-slack-chatter-client&client_secret=YOUR_CLIENT_SECRET&code_verifier=$CODE_VERIFIER"
   ```

#### 3. Using the Access Token

Once you have an access token, you can use it to access MCP endpoints:

```bash
# Get session info
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" http://localhost:8080/mcp/session

# Make MCP requests
curl -X POST http://localhost:8080/mcp/request \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Connect to SSE endpoint
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" http://localhost:8080/mcp/sse
```

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

### Scoped Permissions

- **mcp:search** - Access to search_slack_messages tool
- **mcp:channels** - Access to get_slack_channels tool
- **mcp:stats** - Access to get_search_stats tool

### Session Management

- **Token lifetime**: 24 hours
- **Session cleanup**: Automatic cleanup of expired sessions
- **Token refresh**: Not implemented (request new token when expired)

## Replit Deployment

### Environment Setup

1. **Fork the repository** on Replit
2. **Set environment variables**:
   ```bash
   # Required API keys
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_APP_TOKEN=xapp-your-slack-app-token
   OPENAI_API_KEY=your-openai-api-key
   PINECONE_API_KEY=your-pinecone-api-key
   
   # Optional configuration
   PINECONE_ENVIRONMENT=us-east-1-aws
   PINECONE_INDEX_NAME=slack-chatter-index
   ```

3. **Deploy using the deployment script**:
   ```bash
   python3 replit_deploy.py
   ```

### Replit Configuration

The `.replit` file is configured for:
- **Python 3.11** runtime
- **Automatic dependency installation**
- **Environment variable validation**
- **Graceful shutdown handling**

### Production Considerations

- Update `allow_origins` in CORS middleware for security
- Implement proper OAuth client registration
- Add rate limiting for OAuth endpoints
- Configure HTTPS for production use
- Set up monitoring and logging

## Development Mode

### Running All Services

```bash
# Combined mode (ingestion + MCP server)
python3 main_orchestrator.py combined

# Individual services
python3 main_orchestrator.py ingestion  # Ingestion worker only
python3 main_orchestrator.py search     # Search service test
```

### Debug OAuth Clients

```bash
# View registered OAuth clients
curl http://localhost:8080/debug/oauth-clients
```

### Logging

```bash
# Enable debug logging
python3 main_orchestrator.py remote --log-level DEBUG
```

## Integration Examples

### Python Client Example

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

### JavaScript Client Example

```javascript
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

## Troubleshooting

### Common Issues

1. **OAuth client not found**: Check the client ID and ensure server is running
2. **Token expired**: Generate a new access token
3. **Invalid PKCE**: Ensure code_verifier and code_challenge are correctly generated
4. **Search service not available**: Ensure ingestion has run and vector database is populated

### Debug Commands

```bash
# Test OAuth discovery
curl http://localhost:8080/.well-known/oauth-authorization-server

# Test health endpoint
curl http://localhost:8080/health

# View OAuth clients
curl http://localhost:8080/debug/oauth-clients

# Test MCP request without auth (should fail)
curl -X POST http://localhost:8080/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Security Considerations

- **PKCE**: Prevents authorization code interception
- **Token expiration**: Limits exposure of compromised tokens
- **Scoped permissions**: Principle of least privilege
- **HTTPS**: Required for production deployment
- **CORS**: Configure origins appropriately
- **Rate limiting**: Implement for OAuth endpoints

## Performance

- **SSE connections**: Lightweight persistent connections
- **Token validation**: In-memory lookup (fast)
- **Session cleanup**: Automatic cleanup of expired sessions
- **Search caching**: Implemented at search service level 