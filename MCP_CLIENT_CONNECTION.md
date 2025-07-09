# MCP Client Connection Guide

## Local MCP Server (Our Implementation)

**Server URL:** `http://localhost:5000/mcp`
**Current API Key:** `mcp_key__Kc0WiL-R2F-Gf594N02ueiSYhvgsm44FE-X_oemKc0`

### MCP 2.0 Compliant Connection

```python
import requests
import json

# Initialize session
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer mcp_key__Kc0WiL-R2F-Gf594N02ueiSYhvgsm44FE-X_oemKc0'
}

init_request = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {
            'name': 'slack-search-client',
            'version': '1.0.0'
        }
    }
}

# Initialize
response = requests.post('http://localhost:5000/mcp', json=init_request, headers=headers)
session_id = response.json()['session_info']['session_id']

# Add session header for subsequent requests
headers['Mcp-Session-Id'] = session_id

# Search messages
search_request = {
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'tools/call',
    'params': {
        'name': 'search_slack_messages',
        'arguments': {
            'query': 'your search query',
            'top_k': 10
        }
    }
}

response = requests.post('http://localhost:5000/mcp', json=search_request, headers=headers)
```

### Available Tools

1. **search_slack_messages** - Search through Slack messages
2. **get_slack_channels** - Get list of available channels  
3. **get_search_stats** - Get indexing statistics

### Connection Issue Resolution

**PROBLEM:** You're connecting to `https://slack-chronicler-andreiclodius.replit.app` (external service)
**SOLUTION:** Connect to our local server at `http://localhost:5000/mcp`

**Key Differences:**
- External service: `https://slack-chronicler-andreiclodius.replit.app` ❌ (Wrong API key)
- Our local service: `http://localhost:5000/mcp` ✅ (Working authentication)

### Important Notes

- **DO NOT** connect to `https://slack-chronicler-andreiclodius.replit.app` - that's a different service
- **USE** our local server at `http://localhost:5000/mcp` 
- **API Key** changes on each server restart (check logs for current key)
- **MCP 2.0 Only** - No GET requests, JSON-RPC 2.0 POST only
- **Session Management** - Use `Mcp-Session-Id` header after initialization

### Current Status

- ✅ Server running and authenticated
- ✅ MCP 2.0 specification compliant
- ✅ 124+ messages indexed and searchable
- ✅ Canvas content extraction working
- ⏳ Continued ingestion in progress