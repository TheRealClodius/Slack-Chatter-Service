# Secure API Key Management Guide

## 🔐 Security Overview

The Slack Chatter MCP server implements enterprise-grade API key security with the following features:

- **Cryptographic Security**: 192-bit entropy using SHA256 + secrets.token_bytes(32)
- **Whitelisting System**: Only pre-approved keys are accepted
- **Environment Variable Configuration**: Keys are never hardcoded in the codebase
- **Automatic Fallback**: Secure deployment-specific keys when no user key is provided

## 📋 API Key Management

### Setting Your API Key

There are three ways to configure API keys:

#### 1. Single API Key (Recommended)
```bash
export MCP_API_KEY=mcp_key_[your-48-character-key]
```

#### 2. Multiple Whitelisted Keys
```bash
export MCP_WHITELIST_KEYS=mcp_key_abc123...,mcp_key_def456...,mcp_key_ghi789...
```

#### 3. Automatic Generation (Fallback)
If no keys are provided, the server will generate a secure deployment-specific key automatically.

### Key Format Requirements

- **Prefix**: Must start with `mcp_key_`
- **Length**: 48 hexadecimal characters after prefix
- **Total Length**: 56 characters (`mcp_key_` + 48 chars)
- **Example**: `mcp_key_a1b2c3d4e5f6...` (48 more characters)

## 🛠️ Client Configuration

### Python Client Example
```python
import os
import requests

# Get API key from environment
API_KEY = os.getenv('MCP_API_KEY')
if not API_KEY:
    raise ValueError("MCP_API_KEY environment variable not set")

# Connection details
MCP_SERVER_URL = 'https://your-replit-app.replit.app/mcp'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}

# Initialize session
init_request = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'your-client', 'version': '1.0.0'}
    }
}

response = requests.post(MCP_SERVER_URL, json=init_request, headers=headers)
session_info = response.json()['session_info']
session_id = session_info['session_id']

# Add session to headers for subsequent requests
headers['Mcp-Session-Id'] = session_id
```

### JavaScript Client Example
```javascript
const API_KEY = process.env.MCP_API_KEY;
if (!API_KEY) {
    throw new Error('MCP_API_KEY environment variable not set');
}

const MCP_SERVER_URL = 'https://your-replit-app.replit.app/mcp';

const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`
};

// Initialize session
const initRequest = {
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'your-client', version: '1.0.0' }
    }
};

const response = await fetch(MCP_SERVER_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify(initRequest)
});

const sessionInfo = (await response.json()).session_info;
headers['Mcp-Session-Id'] = sessionInfo.session_id;
```

## 🔑 Key Generation

### Generating a Secure API Key

Use this Python script to generate a cryptographically secure API key:

```python
import secrets
import hashlib

def generate_secure_mcp_key():
    """Generate a cryptographically secure MCP API key"""
    # Generate 32 bytes (256 bits) of cryptographic entropy
    random_bytes = secrets.token_bytes(32)
    
    # Create additional entropy from system information
    system_entropy = f"mcp_key_generation_{secrets.token_urlsafe(16)}"
    
    # Combine entropy sources using SHA256
    combined_entropy = hashlib.sha256(
        system_entropy.encode() + random_bytes
    ).hexdigest()
    
    # Create the final key (48 hex chars = 192 bits of entropy)
    api_key = f"mcp_key_{combined_entropy[:48]}"
    
    return api_key

# Generate your key
secure_key = generate_secure_mcp_key()
print(f"Your secure API key: {secure_key}")
print(f"Set it with: export MCP_API_KEY={secure_key}")
```

### Key Security Best Practices

1. **Never commit keys to version control**
2. **Use environment variables only**
3. **Rotate keys regularly (recommended: every 90 days)**
4. **Use different keys for different environments**
5. **Monitor key usage in server logs**

## 🚀 Deployment Configuration

### Replit Deployment

1. **Set Environment Variable**:
   - Go to your Replit project
   - Click "Secrets" tab
   - Add key: `MCP_API_KEY`
   - Value: Your generated secure key

2. **Verify Configuration**:
   ```bash
   # Check server logs for confirmation
   tail -f /path/to/server.log | grep "Whitelisted API key"
   ```

### Local Development

```bash
# Create .env file (never commit this!)
echo "MCP_API_KEY=your_generated_key_here" > .env

# Load environment variables
source .env

# Start server
python main_orchestrator.py remote
```

## 🔍 Security Features

### Whitelisting System
- Only explicitly approved keys are accepted
- Keys must match the `mcp_key_` prefix format
- Expired keys are automatically rejected
- Invalid keys are logged for security monitoring

### Session Management
- 24-hour session lifetime
- Automatic session cleanup
- Session ID rotation on each authentication
- Secure session headers (`Mcp-Session-Id`)

### Audit Logging
- All authentication attempts are logged
- Key usage statistics are tracked
- Failed authentication attempts are monitored
- Security events are recorded with timestamps

## ⚠️ Security Warnings

### DO NOT:
- ❌ Hardcode API keys in source code
- ❌ Commit keys to GitHub or version control
- ❌ Share keys in documentation or examples
- ❌ Use weak or predictable keys
- ❌ Reuse keys across different environments

### DO:
- ✅ Use environment variables exclusively
- ✅ Generate keys with cryptographic security
- ✅ Rotate keys on a regular schedule
- ✅ Monitor key usage and access logs
- ✅ Use different keys for dev/staging/production

## 📞 Support

If you experience authentication issues:

1. **Verify Key Format**: Ensure your key starts with `mcp_key_` and is 56 characters total
2. **Check Environment Variables**: Confirm `MCP_API_KEY` is set correctly
3. **Review Server Logs**: Look for authentication-related error messages
4. **Generate New Key**: If issues persist, generate a fresh secure key

---

**Remember**: Security is only as strong as your weakest link. Always follow these best practices to keep your MCP server secure.