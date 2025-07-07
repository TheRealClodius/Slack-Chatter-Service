# MCP Tool Integration Guide

## Overview

This Slack Chatter Service provides two integration methods:
1. **Local MCP Server** - JSON-RPC over stdio for local clients
2. **MCP Remote Protocol** - OAuth 2.1 + SSE for remote clients

## Available MCP Tools

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

## Local MCP Integration

### Setup

1. **Clone and setup the Slack Chatter Service**:
   ```bash
   git clone <repository-url>
   cd Slack-Chatter-Service
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   ```bash
   export SLACK_BOT_TOKEN=xoxb-your-token
   export SLACK_APP_TOKEN=xapp-your-token
   export OPENAI_API_KEY=your-openai-key
   export PINECONE_API_KEY=your-pinecone-key
   ```

3. **Run the MCP server**:
   ```bash
   python3 main_orchestrator.py mcp
   ```

### Integration in Your Agent

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "python3",
      "args": ["main_orchestrator.py", "mcp"],
      "cwd": "/path/to/Slack-Chatter-Service"
    }
  }
}
```

## Remote MCP Integration

### Setup

1. **Deploy the MCP Remote Protocol server**:
   ```bash
   python3 main_orchestrator.py remote
   ```

2. **Server will be available at**:
   - Base URL: `http://localhost:8080`
   - OAuth Discovery: `/.well-known/oauth-authorization-server`
   - Authorization: `/oauth/authorize`
   - Token: `/oauth/token`
   - MCP SSE: `/mcp/sse`
   - MCP Request: `/mcp/request`

### OAuth 2.1 Flow

#### 1. Get OAuth Configuration

```bash
curl http://localhost:8080/.well-known/oauth-authorization-server
```

#### 2. Start Authorization

```bash
# Generate PKCE parameters
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)
CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | cut -c1-43)

# Visit authorization URL
curl "http://localhost:8080/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=random_state&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"
```

#### 3. Exchange Code for Token

```bash
curl -X POST http://localhost:8080/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=YOUR_AUTH_CODE&redirect_uri=http://localhost:3000/callback&client_id=mcp-slack-chatter-client&client_secret=YOUR_CLIENT_SECRET&code_verifier=$CODE_VERIFIER"
```

#### 4. Use Access Token

```bash
# Make MCP requests
curl -X POST http://localhost:8080/mcp/request \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Integration Examples

#### Python Client

```python
import asyncio
import json
import httpx
import secrets
import base64
import hashlib
from urllib.parse import urlencode, parse_qs, urlparse

class MCPRemoteClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    def generate_pkce_pair(self):
        """Generate PKCE verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    async def authenticate(self, redirect_uri: str = "http://localhost:3000/callback"):
        """Perform OAuth 2.1 authentication"""
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
        
        # For testing, get the authorization code directly
        async with httpx.AsyncClient() as client:
            response = await client.get(auth_url)
            # In practice, you'd parse the HTML response to get the auth code
            # For now, assume we have the auth code
            auth_code = input("Enter the authorization code: ")
            
            # Exchange code for token
            token_data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code_verifier": code_verifier
            }
            
            token_response = await client.post(
                f"{self.base_url}/oauth/token",
                data=token_data
            )
            
            token_result = token_response.json()
            self.access_token = token_result["access_token"]
            return token_result
    
    async def search_messages(self, query: str, **kwargs):
        """Search Slack messages"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_slack_messages",
                "arguments": {"query": query, **kwargs}
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/request",
                json=request_data,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            return response.json()
    
    async def get_channels(self):
        """Get available channels"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_slack_channels",
                "arguments": {}
            },
            "id": 2
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/request",
                json=request_data,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            return response.json()
    
    async def get_stats(self):
        """Get search statistics"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_search_stats",
                "arguments": {}
            },
            "id": 3
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/request",
                json=request_data,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            return response.json()

# Usage
async def main():
    client = MCPRemoteClient(
        base_url="http://localhost:8080",
        client_id="mcp-slack-chatter-client",
        client_secret="your_client_secret"  # Get from server logs
    )
    
    # Authenticate
    await client.authenticate()
    
    # Search messages
    results = await client.search_messages("deployment issues", top_k=5)
    print(json.dumps(results, indent=2))
    
    # Get channels
    channels = await client.get_channels()
    print(json.dumps(channels, indent=2))
    
    # Get stats
    stats = await client.get_stats()
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

#### JavaScript/Node.js Client

```javascript
const crypto = require('crypto');
const fetch = require('node-fetch');

class MCPRemoteClient {
    constructor(baseUrl, clientId, clientSecret) {
        this.baseUrl = baseUrl;
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.accessToken = null;
    }
    
    generatePKCEPair() {
        const codeVerifier = crypto.randomBytes(32).toString('base64url');
        const codeChallenge = crypto.createHash('sha256').update(codeVerifier).digest('base64url');
        return { codeVerifier, codeChallenge };
    }
    
    async authenticate(redirectUri = 'http://localhost:3000/callback') {
        const { codeVerifier, codeChallenge } = this.generatePKCEPair();
        
        // Start authorization
        const authParams = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: redirectUri,
            scope: 'mcp:search mcp:channels mcp:stats',
            state: crypto.randomBytes(32).toString('base64url'),
            code_challenge: codeChallenge,
            code_challenge_method: 'S256'
        });
        
        const authUrl = `${this.baseUrl}/oauth/authorize?${authParams}`;
        console.log('Visit this URL to authorize:', authUrl);
        
        // Get authorization code (in practice, this would come from redirect)
        const authCode = process.env.AUTH_CODE || 'your_auth_code_here';
        
        // Exchange code for token
        const tokenResponse = await fetch(`${this.baseUrl}/oauth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: authCode,
                redirect_uri: redirectUri,
                client_id: this.clientId,
                client_secret: this.clientSecret,
                code_verifier: codeVerifier
            })
        });
        
        const tokenData = await tokenResponse.json();
        this.accessToken = tokenData.access_token;
        return tokenData;
    }
    
    async searchMessages(query, options = {}) {
        if (!this.accessToken) {
            throw new Error('Not authenticated. Call authenticate() first.');
        }
        
        const requestData = {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'search_slack_messages',
                arguments: { query, ...options }
            },
            id: 1
        };
        
        const response = await fetch(`${this.baseUrl}/mcp/request`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        return response.json();
    }
    
    async getChannels() {
        if (!this.accessToken) {
            throw new Error('Not authenticated. Call authenticate() first.');
        }
        
        const requestData = {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'get_slack_channels',
                arguments: {}
            },
            id: 2
        };
        
        const response = await fetch(`${this.baseUrl}/mcp/request`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        return response.json();
    }
    
    async getStats() {
        if (!this.accessToken) {
            throw new Error('Not authenticated. Call authenticate() first.');
        }
        
        const requestData = {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'get_search_stats',
                arguments: {}
            },
            id: 3
        };
        
        const response = await fetch(`${this.baseUrl}/mcp/request`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        return response.json();
    }
}

// Usage
async function main() {
    const client = new MCPRemoteClient(
        'http://localhost:8080',
        'mcp-slack-chatter-client',
        'your_client_secret'  // Get from server logs
    );
    
    // Authenticate
    await client.authenticate();
    
    // Search messages
    const results = await client.searchMessages('deployment issues', { top_k: 5 });
    console.log(JSON.stringify(results, null, 2));
    
    // Get channels
    const channels = await client.getChannels();
    console.log(JSON.stringify(channels, null, 2));
    
    // Get stats
    const stats = await client.getStats();
    console.log(JSON.stringify(stats, null, 2));
}

if (require.main === module) {
    main().catch(console.error);
}
```

## Configuration Options

### OAuth Client Configuration

The server automatically registers a default OAuth client:
- **Client ID**: `mcp-slack-chatter-client`
- **Client Secret**: Generated on startup (check server logs)
- **Scopes**: `mcp:search`, `mcp:channels`, `mcp:stats`
- **Redirect URIs**: `http://localhost:3000/callback`, `https://*.replit.app/callback`

### Scoped Permissions

- **mcp:search**: Required for `search_slack_messages`
- **mcp:channels**: Required for `get_slack_channels`
- **mcp:stats**: Required for `get_search_stats`

### Environment Variables

```bash
# Required
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key

# Optional
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=slack-chatter-index
MCP_SERVER_NAME=slack-chatter-mcp
MCP_SERVER_VERSION=1.0.0
```

## Testing

### Manual Testing

```bash
# Test OAuth discovery
curl http://localhost:8080/.well-known/oauth-authorization-server

# Test health
curl http://localhost:8080/health

# Test debug endpoint
curl http://localhost:8080/debug/oauth-clients

# Test MCP request (should fail without auth)
curl -X POST http://localhost:8080/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Automated Testing

```python
# test_mcp_integration.py
import asyncio
import pytest
from your_mcp_client import MCPRemoteClient

@pytest.mark.asyncio
async def test_mcp_search():
    client = MCPRemoteClient(
        base_url="http://localhost:8080",
        client_id="mcp-slack-chatter-client",
        client_secret="your_client_secret"
    )
    
    await client.authenticate()
    
    # Test search
    results = await client.search_messages("test query")
    assert "result" in results
    assert results["jsonrpc"] == "2.0"
    
    # Test channels
    channels = await client.get_channels()
    assert "result" in channels
    
    # Test stats
    stats = await client.get_stats()
    assert "result" in stats
```

## Error Handling

### Common Errors

1. **Authentication Failed** (401): Invalid or expired token
2. **Insufficient Scope** (403): Missing required scope for operation
3. **Invalid Request** (400): Malformed JSON-RPC request
4. **Service Unavailable** (503): Search service not initialized

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Authentication failed",
    "data": {
      "details": "Invalid token"
    }
  }
}
```

## Best Practices

1. **Token Management**: Store tokens securely and handle expiration
2. **Rate Limiting**: Implement client-side rate limiting
3. **Error Handling**: Always check for error responses
4. **Scopes**: Request only the scopes you need
5. **HTTPS**: Use HTTPS in production
6. **Validation**: Validate all inputs and outputs
7. **Logging**: Log requests for debugging

## Integration Support

For integration support:
1. Check server logs for OAuth client secret
2. Verify environment variables are set
3. Test with curl commands first
4. Use debug endpoints for troubleshooting
5. Check network connectivity and firewall rules 