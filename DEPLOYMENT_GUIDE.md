# Deployment Guide

## Overview

The Slack Chatter Service has multiple deployment modes:
1. **Ingestion Worker** - Runs 24/7 to keep embeddings fresh (needs deployment)
2. **MCP Tool (Local)** - Invoked on-demand by clients via stdio (no deployment needed)
3. **MCP Streamable HTTP** - Single endpoint with session headers for remote access (March 2025 Standard)

## Deployment Modes

### Mode 1: Ingestion Worker Only
Deploy only the background worker to keep embeddings fresh. Clients use local MCP stdio access.

### Mode 2: MCP Streamable HTTP Server
Deploy both ingestion worker AND MCP Streamable HTTP server for modern remote access with session management.

### Mode 3: Combined Deployment
Single deployment running both components together.

## Environment Variables

Create a `.env` file with these required variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_CHANNELS=C1234567890,C0987654321,C1122334455

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment-name
PINECONE_INDEX_NAME=slack-messages

# Notion Configuration
NOTION_INTEGRATION_SECRET=secret_your-notion-integration-secret-here
NOTION_DATABASE_ID=your-notion-database-id-here
```

## MCP Streamable HTTP Standard (March 2025)

The service now implements the **latest MCP Streamable HTTP standard** with these features:

### ✨ Key Features
- **Single endpoint** (`/mcp`) supporting both GET and POST requests
- **Session management** via `mcp-session-id` headers
- **JSON-RPC protocol** compliance
- **Bidirectional communication**
- **Authentication support** (API keys, OAuth tokens)

### 🔗 Client Configuration Examples

#### For MCP-Compatible AI Agents

**Claude Desktop (Local MCP):**
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

**Remote MCP (Streamable HTTP):**
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
        "session_management": true
      }
    }
  }
}
```

#### For Custom Applications

**Python Client Example:**
```python
import httpx
import json

class MCPStreamableClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id = None
        
    async def search_messages(self, query: str, top_k: int = 10):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
            
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
                f"{self.base_url}/mcp",
                json=request_data,
                headers=headers
            )
            
            # Extract session ID from response headers
            if "mcp-session-id" in response.headers:
                self.session_id = response.headers["mcp-session-id"]
            
            return response.json()

# Usage
client = MCPStreamableClient(
    base_url="https://your-deployment.com",
    api_key="mcp_key_your_api_key_here"
)

results = await client.search_messages("deployment issues")
```

**JavaScript/Node.js Client Example:**
```javascript
class MCPStreamableClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.sessionId = null;
    }
    
    async searchMessages(query, topK = 10) {
        const headers = { 'Authorization': `Bearer ${this.apiKey}` };
        if (this.sessionId) {
            headers['mcp-session-id'] = this.sessionId;
        }
        
        const requestData = {
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "search_slack_messages",
                arguments: { query, top_k: topK }
            },
            id: 1
        };
        
        const response = await fetch(`${this.baseUrl}/mcp`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        // Extract session ID from response headers
        const sessionId = response.headers.get('mcp-session-id');
        if (sessionId) {
            this.sessionId = sessionId;
        }
        
        return response.json();
    }
    
    // Alternative: GET request (simplified)
    async getTools() {
        const headers = { 'Authorization': `Bearer ${this.apiKey}` };
        if (this.sessionId) {
            headers['mcp-session-id'] = this.sessionId;
        }
        
        const response = await fetch(`${this.baseUrl}/mcp?method=tools/list`, {
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

const results = await client.searchMessages('deployment issues');
```

**cURL Examples:**
```bash
# Get API key (development only)
curl https://your-deployment.com/dev/api-key

# POST request to search messages
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer mcp_key_your_api_key_here" \
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

# GET request to list tools (simplified)
curl "https://your-deployment.com/mcp?method=tools/list" \
  -H "Authorization: Bearer mcp_key_your_api_key_here"

# Using session ID for subsequent requests
curl "https://your-deployment.com/mcp?method=tools/call&name=get_search_stats" \
  -H "mcp-session-id: mcp_session_abc123"
```

## Deployment Options

### Option 1: Replit (Easiest)

**Perfect for beginners and quick deployments!**

1. **Import from GitHub:**
   - Go to [Replit.com](https://replit.com)
   - Create New Repl → Import from GitHub
   - Paste your repository URL
   - Replit auto-detects Python and sets up environment

2. **Add environment variables:**
   - Click the Secrets tab (🔒 icon) in Replit
   - Add all environment variables from your `.env` file

3. **Deploy based on your needs:**

   **Ingestion Worker Only:**
   ```bash
   python replit_deploy.py
   # Or manually: python main_orchestrator.py ingestion
   ```

   **MCP Streamable HTTP Server:**
   ```bash
   python main_orchestrator.py remote
   # Server runs on port 8080 with Streamable HTTP standard
   ```

   **Combined Mode:**
   ```bash
   python main_orchestrator.py combined
   # Runs both ingestion and MCP stdio server
   ```

4. **Enable Always On:**
   - Go to Repl settings
   - Enable "Always On" to keep it running 24/7
   - **Cost**: ~$5/month

5. **Get your API key:**
   ```bash
   # Visit: https://your-repl-name.your-username.repl.co/dev/api-key
   # Copy the API key for client authentication
   ```

**Replit Pros:**
- Super simple setup (5 minutes)
- Built-in IDE for editing
- Auto dependency management
- GitHub sync
- Great for learning/prototyping

### Option 2: Railway (Recommended for Production)

#### Ingestion Worker Deployment

1. **Go to [Railway.app](https://railway.app)**
2. **Sign in with GitHub**
3. **Create New Project → Deploy from GitHub repo**
4. **Add environment variables in dashboard**
5. **Set start command:** `python main_orchestrator.py ingestion`
6. **Deploy automatically!**

#### MCP Streamable HTTP Server Deployment

1. **Create second Railway service in same project**
2. **Set start command:** `python main_orchestrator.py remote`
3. **Configure port:** Set `PORT=8080`
4. **Add same environment variables**
5. **Generate domain** for client access

**Cost**: ~$5-15/month (depending on usage)

### Option 3: Render (Background Worker + Web Service)

#### Background Worker (Ingestion)

1. **Go to [Render.com](https://render.com)**
2. **Create New → Background Worker**
3. **Connect GitHub repository**
4. **Set start command:** `python main_orchestrator.py ingestion`
5. **Add environment variables**
6. **Deploy!**

#### Web Service (MCP Streamable HTTP)

1. **Create New → Web Service**
2. **Connect same GitHub repository**
3. **Set start command:** `python main_orchestrator.py remote`
4. **Set port:** `8080`
5. **Add environment variables**
6. **Deploy!**

**Cost**: ~$14/month ($7 per service)

### Option 4: Docker Deployment (Recommended)

#### Single Container (Combined Mode)
```dockerfile
# Dockerfile.combined
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
CMD ["python", "main_orchestrator.py", "combined"]
```

#### Multi-Container Setup

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  ingestion-worker:
    build: .
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
      - NOTION_INTEGRATION_SECRET=${NOTION_INTEGRATION_SECRET}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - SLACK_CHANNELS=${SLACK_CHANNELS}
    command: ["python", "main_orchestrator.py", "ingestion"]
    restart: unless-stopped

  mcp-streamable-server:
    build: .
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
      - NOTION_INTEGRATION_SECRET=${NOTION_INTEGRATION_SECRET}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - SLACK_CHANNELS=${SLACK_CHANNELS}
    command: ["python", "main_orchestrator.py", "remote"]
    ports:
      - "8080:8080"
    restart: unless-stopped
```

**Deploy Commands:**
```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your actual values

# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f ingestion-worker
docker-compose logs -f mcp-streamable-server

# Stop all services
docker-compose down
```

### Option 5: Traditional VPS Deployment

#### Single Server Setup

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-pip

# Clone repo
git clone https://github.com/your-username/slack-chatter-service.git
cd slack-chatter-service

# Install dependencies
pip install uv
uv sync

# Install package
uv pip install -e .

# Set environment variables
export SLACK_BOT_TOKEN="xoxb-..."
export OPENAI_API_KEY="sk-..."
# ... etc

# Choose deployment mode:

# Option A: Ingestion worker only
python main_orchestrator.py ingestion

# Option B: MCP Streamable HTTP server only  
python main_orchestrator.py remote

# Option C: Combined mode
python main_orchestrator.py combined
```

#### Process Management with systemd

**Ingestion Worker Service:**
```ini
# /etc/systemd/system/slack-chatter-ingestion.service
[Unit]
Description=Slack Chatter Ingestion Worker
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/opt/slack-chatter-service
Environment=SLACK_BOT_TOKEN=xoxb-...
Environment=OPENAI_API_KEY=sk-...
Environment=PINECONE_API_KEY=...
Environment=PINECONE_ENVIRONMENT=...
Environment=NOTION_INTEGRATION_SECRET=...
Environment=NOTION_DATABASE_ID=...
Environment=SLACK_CHANNELS=C1234567890,C0987654321
ExecStart=/usr/bin/python3 main_orchestrator.py ingestion
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**MCP Streamable HTTP Server Service:**
```ini
# /etc/systemd/system/slack-chatter-streamable.service
[Unit]
Description=Slack Chatter MCP Streamable HTTP Server
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/opt/slack-chatter-service
Environment=SLACK_BOT_TOKEN=xoxb-...
Environment=OPENAI_API_KEY=sk-...
Environment=PINECONE_API_KEY=...
Environment=PINECONE_ENVIRONMENT=...
Environment=NOTION_INTEGRATION_SECRET=...
Environment=NOTION_DATABASE_ID=...
Environment=SLACK_CHANNELS=C1234567890,C0987654321
ExecStart=/usr/bin/python3 main_orchestrator.py remote
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable Services:**
```bash
sudo systemctl enable slack-chatter-ingestion
sudo systemctl enable slack-chatter-streamable
sudo systemctl start slack-chatter-ingestion
sudo systemctl start slack-chatter-streamable
```

### Option 6: Serverless/Cron-based (Alternative)

For serverless ingestion (less reliable than 24/7 worker):

- **AWS Lambda** + CloudWatch Events
- **Google Cloud Functions** + Cloud Scheduler  
- **Vercel Cron** + Vercel Functions
- **GitHub Actions** (for development)

**Note**: MCP Streamable HTTP server needs persistent deployment.

### Option 7: Local Development

For development and testing:
```bash
# Run ingestion worker locally
python main_orchestrator.py ingestion

# Run MCP Streamable HTTP server locally
python main_orchestrator.py remote

# Run combined mode (ingestion + MCP stdio server)
python main_orchestrator.py combined

# Run only MCP stdio server (for local client testing)
python main_orchestrator.py mcp
```

## Deployment Mode Comparison

| Mode | Use Case | Components | Port | Authentication |
|------|----------|------------|------|----------------|
| **Ingestion Only** | Background data processing | Worker only | None | N/A |
| **MCP Streamable** | Remote API access | Worker + Streamable Server | 8080 | API Keys/OAuth |
| **Combined** | All-in-one deployment | Worker + Stdio Server | None | N/A |
| **Local MCP** | Development/testing | Stdio Server only | None | N/A |

## Platform Comparison

| Platform | Cost/Month | Setup Time | Ease of Use | Best For |
|----------|------------|------------|-------------|----------|
| **Replit** | ~$5 | 5 mins | ⭐⭐⭐⭐⭐ | Beginners, learning |
| **Railway** | ~$5-15 | 10 mins | ⭐⭐⭐⭐ | Production apps |
| **Render** | ~$7-14 | 15 mins | ⭐⭐⭐ | Background workers |
| **Docker** | Varies | 30 mins | ⭐⭐ | Maximum flexibility |
| **VPS** | ~$5-20 | 1+ hour | ⭐ | Full control |

## MCP Streamable HTTP Configuration

### Authentication

The MCP Streamable HTTP server supports:

1. **API Key Authentication** (Recommended for most clients)
   ```
   Authorization: Bearer mcp_key_generated_key_here
   ```

2. **OAuth Token Authentication** (For advanced integrations)
   ```
   Authorization: Bearer oauth_token_here
   ```

3. **Session Management** (After initial authentication)
   ```
   mcp-session-id: mcp_session_generated_session_id
   ```

### Getting Your API Key

**Development:**
```bash
# Visit your deployment URL
curl https://your-deployment.com/dev/api-key
```

**Production:** API keys should be managed securely through environment variables or a key management system.

### Client Integration

**Local MCP (stdio):**
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

**Remote MCP (Streamable HTTP):**
```json
{
  "mcpServers": {
    "slack-chatter-remote": {
      "transport": "http",
      "endpoint": "https://your-deployment.replit.app/mcp",
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

## Cloud Platform Specific Instructions

### Railway
1. Connect GitHub repo
2. Add environment variables in dashboard
3. Choose deployment command:
   - Ingestion: `python main_orchestrator.py ingestion`
   - Streamable: `python main_orchestrator.py remote`
   - Combined: `python main_orchestrator.py combined`

### Render
1. Create Background Worker (for ingestion) + Web Service (for streamable)
2. Set appropriate start commands
3. Configure port 8080 for streamable server

### Replit
1. Import from GitHub
2. Add environment variables in Secrets
3. Choose deployment mode in run command
4. Enable Always On for 24/7 operation

## Monitoring and Troubleshooting

### Health Checks

**Ingestion Worker:**
```bash
# Check if worker is processing messages
python scripts/verify_ingestion.py
```

**MCP Streamable HTTP Server:**
```bash
# Test server info
curl https://your-deployment.com/info

# Test health endpoint
curl https://your-deployment.com/health

# Test MCP endpoint (should fail without auth)
curl -X POST https://your-deployment.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test with authentication
curl -X POST https://your-deployment.com/mcp \
  -H "Authorization: Bearer mcp_key_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Common Issues

1. **Environment variables not set**: Check deployment platform configuration
2. **API key not working**: Check server logs for generated API key
3. **Port configuration**: Ensure port 8080 is exposed for streamable server
4. **Session management**: Use session IDs for subsequent requests after initial auth
5. **CORS issues**: Update allowed origins for production domains

## Security Considerations

### Production Checklist

- [ ] **HTTPS enabled** for all HTTP communication
- [ ] **API keys secured** (not in code or logs)
- [ ] **Environment variables protected** on deployment platform
- [ ] **Session expiration** properly configured (24 hours default)
- [ ] **CORS configured** with specific origins (not `*`)
- [ ] **Rate limiting enabled** for the `/mcp` endpoint
- [ ] **Input validation** for all MCP parameters
- [ ] **Monitoring enabled** for failed authentication attempts
- [ ] **Firewall rules** configured for required ports only

### Development Security
- [ ] **Development endpoints** removed in production (`/dev/api-key`)
- [ ] **API key rotation** implemented for long-running deployments
- [ ] **Secure local development** environment
- [ ] **Regular dependency updates** via `uv sync`

The deployment guide now covers the new MCP Streamable HTTP standard with clear client configuration examples and comprehensive deployment options. 