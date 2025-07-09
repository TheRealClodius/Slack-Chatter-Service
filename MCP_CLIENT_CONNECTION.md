# MCP Client Connection Guide

## Remote MCP Server (Replit Deployment)

**CORRECT URL:** `https://slack-chronicler-andreiclodius.replit.app/mcp` ✅  
**STABLE API KEY:** `mcp_key_slack_chatter_2025_stable`

**FIXED AUTHENTICATION:** Using consistent API key across all deployments

**Note:** Server is accessible remotely on port 5000, bound to 0.0.0.0

### MCP 2.0 Compliant Connection

```python
import requests
import json

# Remote MCP server connection
MCP_SERVER_URL = 'https://slack-chronicler-andreiclodius.replit.app/mcp'
API_KEY = 'mcp_key_slack_chatter_2025_stable'

# Initialize session
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
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
response = requests.post(MCP_SERVER_URL, json=init_request, headers=headers)
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

response = requests.post(MCP_SERVER_URL, json=search_request, headers=headers)
```

### Available Tools

1. **search_slack_messages** - Search through Slack messages
2. **get_slack_channels** - Get list of available channels  
3. **get_search_stats** - Get indexing statistics

### Remote Access Configuration

**REPLIT URL:** The server is deployed on Replit and accessible remotely
**PORT:** 5000 (bound to 0.0.0.0 for external access)
**PROTOCOL:** HTTPS (Replit provides automatic SSL)

**Getting Your Server URL:**
1. Check your Replit console for the exact URL
2. Format: `https://[repl-name].[username].replit.app/mcp`
3. Use the current API key from server logs

### Important Notes

- **REMOTE ACCESS** - Server runs on 0.0.0.0:5000 for external connectivity
- **HTTPS REQUIRED** - Replit provides automatic SSL termination  
- **API Key** changes on each server restart (check logs for current key)
- **MCP 2.0 Only** - No GET requests, JSON-RPC 2.0 POST only
- **Session Management** - Use `Mcp-Session-Id` header after initialization

### Current Status

- ✅ Server running and authenticated
- ✅ MCP 2.0 specification compliant
- ✅ 124+ messages indexed and searchable
- ✅ Canvas content extraction working
- ⏳ Continued ingestion in progress