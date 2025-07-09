# OAuth 2.1 Client Integration Guide for MCP Remote Protocol

## Overview

The Slack Chatter Service now implements full OAuth 2.1 with PKCE for secure authentication. This guide provides complete client integration instructions for accessing the MCP Remote Protocol.

## Quick Start

### 1. OAuth 2.1 Discovery

```bash
curl http://localhost:5000/.well-known/oauth-authorization-server
```

**Response:**
```json
{
  "issuer": "http://0.0.0.0:5000",
  "authorization_endpoint": "http://0.0.0.0:5000/oauth/authorize",
  "token_endpoint": "http://0.0.0.0:5000/oauth/token",
  "scopes_supported": ["mcp:search", "mcp:channels", "mcp:stats"],
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_post"]
}
```

### 2. Get Client Credentials (Development Only)

```bash
curl http://localhost:5000/debug/oauth-client-info
```

**Response:**
```json
{
  "client_id": "mcp-slack-chatter-client",
  "client_secret": "mcp_client_secret_12345",
  "scopes": ["mcp:search", "mcp:channels", "mcp:stats"],
  "redirect_uri": "http://localhost:3000/callback"
}
```

## Complete OAuth 2.1 Flow

### Step 1: Generate PKCE Values

```bash
# Generate code verifier
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)

# Generate code challenge
CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | cut -c1-43)

echo "Code Verifier: $CODE_VERIFIER"
echo "Code Challenge: $CODE_CHALLENGE"
```

### Step 2: Authorization Request

**Manual Browser Flow:**
```
http://localhost:5000/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=random_state_123&code_challenge=YOUR_CODE_CHALLENGE&code_challenge_method=S256
```

**Using curl (will redirect):**
```bash
curl -L "http://localhost:5000/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=random_state_123&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"
```

### Step 3: Extract Authorization Code

The server will redirect to `http://localhost:3000/callback?code=AUTH_CODE&state=random_state_123`

Extract the `code` parameter from the redirect URL.

### Step 4: Exchange Code for Tokens

```bash
curl -X POST http://localhost:5000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTH_CODE" \
  -d "redirect_uri=http://localhost:3000/callback" \
  -d "client_id=mcp-slack-chatter-client" \
  -d "client_secret=mcp_client_secret_12345" \
  -d "code_verifier=$CODE_VERIFIER"
```

**Response:**
```json
{
  "access_token": "abcdef123456...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "refresh_token": "refresh123456...",
  "scope": "mcp:search mcp:channels mcp:stats"
}
```

### Step 5: Use Access Token for MCP Requests

```bash
curl -X POST http://localhost:5000/mcp \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Client Implementation Examples

### Python Client

```python
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode, parse_qs, urlparse

class MCPOAuthClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.client_id = "mcp-slack-chatter-client"
        self.client_secret = "mcp_client_secret_12345"
        self.redirect_uri = "http://localhost:3000/callback"
        self.access_token = None
        self.refresh_token = None
    
    def generate_pkce(self):
        """Generate PKCE code verifier and challenge"""
        self.code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return self.code_verifier, code_challenge
    
    def get_authorization_url(self):
        """Get the authorization URL for the user to visit"""
        code_verifier, code_challenge = self.generate_pkce()
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "mcp:search mcp:channels mcp:stats",
            "state": secrets.token_urlsafe(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        return f"{self.base_url}/oauth/authorize?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, authorization_code):
        """Exchange authorization code for access and refresh tokens"""
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": self.code_verifier
        }
        
        response = requests.post(f"{self.base_url}/oauth/token", data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        
        return token_data
    
    def refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(f"{self.base_url}/oauth/token", data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        
        return token_data
    
    def mcp_request(self, method, params=None, request_id=1):
        """Make an authenticated MCP request"""
        if not self.access_token:
            raise ValueError("No access token available")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params:
            payload["params"] = params
        
        response = requests.post(f"{self.base_url}/mcp", 
                               headers=headers, 
                               json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def search_messages(self, query, top_k=10):
        """Search Slack messages"""
        return self.mcp_request("tools/call", {
            "name": "search_slack_messages",
            "arguments": {
                "query": query,
                "top_k": top_k
            }
        })

# Usage example
client = MCPOAuthClient()

# Step 1: Get authorization URL
auth_url = client.get_authorization_url()
print(f"Visit this URL: {auth_url}")

# Step 2: After user visits URL and gets redirected, extract the code
authorization_code = input("Enter the authorization code: ")

# Step 3: Exchange code for tokens
tokens = client.exchange_code_for_tokens(authorization_code)
print("Tokens obtained!")

# Step 4: Make MCP requests
results = client.search_messages("deployment issues", top_k=5)
print(results)
```

### JavaScript/Node.js Client

```javascript
const crypto = require('crypto');
const axios = require('axios');

class MCPOAuthClient {
    constructor(baseUrl = 'http://localhost:5000') {
        this.baseUrl = baseUrl;
        this.clientId = 'mcp-slack-chatter-client';
        this.clientSecret = 'mcp_client_secret_12345';
        this.redirectUri = 'http://localhost:3000/callback';
        this.accessToken = null;
        this.refreshToken = null;
    }
    
    generatePKCE() {
        // Generate code verifier
        this.codeVerifier = crypto
            .randomBytes(32)
            .toString('base64url');
        
        // Generate code challenge
        const codeChallenge = crypto
            .createHash('sha256')
            .update(this.codeVerifier)
            .digest('base64url');
        
        return { codeVerifier: this.codeVerifier, codeChallenge };
    }
    
    getAuthorizationUrl() {
        const { codeChallenge } = this.generatePKCE();
        
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            scope: 'mcp:search mcp:channels mcp:stats',
            state: crypto.randomBytes(16).toString('hex'),
            code_challenge: codeChallenge,
            code_challenge_method: 'S256'
        });
        
        return `${this.baseUrl}/oauth/authorize?${params}`;
    }
    
    async exchangeCodeForTokens(authorizationCode) {
        const data = {
            grant_type: 'authorization_code',
            code: authorizationCode,
            redirect_uri: this.redirectUri,
            client_id: this.clientId,
            client_secret: this.clientSecret,
            code_verifier: this.codeVerifier
        };
        
        const response = await axios.post(`${this.baseUrl}/oauth/token`, data, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        
        this.accessToken = response.data.access_token;
        this.refreshToken = response.data.refresh_token;
        
        return response.data;
    }
    
    async refreshAccessToken() {
        const data = {
            grant_type: 'refresh_token',
            refresh_token: this.refreshToken,
            client_id: this.clientId,
            client_secret: this.clientSecret
        };
        
        const response = await axios.post(`${this.baseUrl}/oauth/token`, data, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        
        this.accessToken = response.data.access_token;
        this.refreshToken = response.data.refresh_token;
        
        return response.data;
    }
    
    async mcpRequest(method, params = null, requestId = 1) {
        if (!this.accessToken) {
            throw new Error('No access token available');
        }
        
        const payload = {
            jsonrpc: '2.0',
            method,
            id: requestId
        };
        
        if (params) {
            payload.params = params;
        }
        
        const response = await axios.post(`${this.baseUrl}/mcp`, payload, {
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        return response.data;
    }
    
    async searchMessages(query, topK = 10) {
        return this.mcpRequest('tools/call', {
            name: 'search_slack_messages',
            arguments: {
                query,
                top_k: topK
            }
        });
    }
}

// Usage example
(async () => {
    const client = new MCPOAuthClient();
    
    // Step 1: Get authorization URL
    const authUrl = client.getAuthorizationUrl();
    console.log(`Visit this URL: ${authUrl}`);
    
    // Step 2: After user visits URL, extract the code
    const authorizationCode = 'YOUR_AUTH_CODE_HERE';
    
    // Step 3: Exchange code for tokens
    const tokens = await client.exchangeCodeForTokens(authorizationCode);
    console.log('Tokens obtained!', tokens);
    
    // Step 4: Make MCP requests
    const results = await client.searchMessages('deployment issues', 5);
    console.log(results);
})();
```

## Scopes and Permissions

| Scope | Description | Required For |
|-------|-------------|--------------|
| `mcp:search` | Search Slack messages | `search_slack_messages` tool |
| `mcp:channels` | Get channel information | `get_slack_channels` tool |
| `mcp:stats` | View system statistics | `get_search_stats` tool |

## Token Management

### Access Token
- **Lifetime**: 24 hours (86400 seconds)
- **Format**: Bearer token
- **Usage**: Include in `Authorization: Bearer <token>` header

### Refresh Token
- **Purpose**: Obtain new access tokens
- **Lifetime**: Until explicitly revoked
- **Usage**: Exchange for new access/refresh token pair

### Token Introspection

```bash
curl -X POST http://localhost:5000/oauth/introspect \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=YOUR_ACCESS_TOKEN" \
  -d "client_id=mcp-slack-chatter-client" \
  -d "client_secret=mcp_client_secret_12345"
```

### Token Revocation

```bash
curl -X POST http://localhost:5000/oauth/revoke \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=YOUR_TOKEN" \
  -d "client_id=mcp-slack-chatter-client" \
  -d "client_secret=mcp_client_secret_12345"
```

## Error Handling

### Common OAuth Errors

| Error | Description | Solution |
|-------|-------------|----------|
| `invalid_client` | Invalid client credentials | Check client_id and client_secret |
| `invalid_grant` | Invalid authorization code | Get new authorization code |
| `invalid_request` | Missing required parameters | Check all required parameters |
| `access_denied` | User denied authorization | User must approve the request |

### MCP Authentication Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `-32001` | Authentication failed | Check access token validity |
| `401` | Unauthorized | Token expired or invalid |
| `403` | Insufficient scope | Request appropriate scopes |

## Production Considerations

1. **Environment Variables**: Store client secrets in environment variables
2. **HTTPS Required**: OAuth 2.1 requires HTTPS in production
3. **Secure Storage**: Store tokens securely (encrypted storage)
4. **Token Rotation**: Implement automatic token refresh
5. **Error Handling**: Handle token expiration gracefully
6. **Rate Limiting**: Respect API rate limits

## Testing the Integration

### 1. Complete Flow Test

```bash
# Get client info
curl http://localhost:5000/debug/oauth-client-info

# Generate PKCE
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)
CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | cut -c1-43)

# Get authorization (copy the redirect URL from browser)
curl -L "http://localhost:5000/oauth/authorize?response_type=code&client_id=mcp-slack-chatter-client&redirect_uri=http://localhost:3000/callback&scope=mcp:search+mcp:channels+mcp:stats&state=test123&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"

# Exchange code for tokens (replace YOUR_AUTH_CODE)
curl -X POST http://localhost:5000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=YOUR_AUTH_CODE&redirect_uri=http://localhost:3000/callback&client_id=mcp-slack-chatter-client&client_secret=mcp_client_secret_12345&code_verifier=$CODE_VERIFIER"

# Test MCP request (replace YOUR_ACCESS_TOKEN)
curl -X POST http://localhost:5000/mcp \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 2. Debug Token Status

```bash
curl http://localhost:5000/debug/tokens
```

## Support

For issues with OAuth integration:

1. Check the `/debug/oauth-client-info` endpoint for current configuration
2. Verify all required parameters are included in requests
3. Ensure PKCE values are generated correctly
4. Check token expiration with `/oauth/introspect`
5. Review server logs for detailed error messages

The OAuth 2.1 implementation follows RFC 6749, RFC 7636 (PKCE), and OAuth 2.1 best practices for secure authentication.