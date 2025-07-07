# Deployment Guide

## Overview

The Slack Chatter Service has multiple deployment modes:
1. **Ingestion Worker** - Runs 24/7 to keep embeddings fresh (needs deployment)
2. **MCP Tool (Local)** - Invoked on-demand by clients via stdio (no deployment needed)
3. **MCP Remote Protocol** - OAuth 2.1 + SSE server for remote access (optional deployment)

## Deployment Modes

### Mode 1: Ingestion Worker Only
Deploy only the background worker to keep embeddings fresh. Clients use local MCP stdio access.

### Mode 2: Full Remote MCP Server
Deploy both ingestion worker AND MCP Remote Protocol server for OAuth 2.1 authenticated remote access.

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

   **MCP Remote Protocol Server:**
   ```bash
   python main_orchestrator.py remote
   # Server runs on port 8080 with OAuth 2.1 + SSE
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

#### MCP Remote Protocol Server Deployment

1. **Create second Railway service in same project**
2. **Set start command:** `python main_orchestrator.py remote`
3. **Configure port:** Set `PORT=8080`
4. **Add same environment variables**
5. **Generate domain** for OAuth redirect URIs

**Cost**: ~$5-15/month (depending on usage)

### Option 3: Render (Background Worker + Web Service)

#### Background Worker (Ingestion)

1. **Go to [Render.com](https://render.com)**
2. **Create New → Background Worker**
3. **Connect GitHub repository**
4. **Set start command:** `python main_orchestrator.py ingestion`
5. **Add environment variables**
6. **Deploy!**

#### Web Service (MCP Remote Protocol)

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

  mcp-remote-server:
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
docker-compose logs -f mcp-remote-server

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

# Option B: MCP Remote Protocol server only  
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

**MCP Remote Protocol Server Service:**
```ini
# /etc/systemd/system/slack-chatter-remote.service
[Unit]
Description=Slack Chatter MCP Remote Protocol Server
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
sudo systemctl enable slack-chatter-remote
sudo systemctl start slack-chatter-ingestion
sudo systemctl start slack-chatter-remote
```

### Option 6: Serverless/Cron-based (Alternative)

For serverless ingestion (less reliable than 24/7 worker):

- **AWS Lambda** + CloudWatch Events
- **Google Cloud Functions** + Cloud Scheduler  
- **Vercel Cron** + Vercel Functions
- **GitHub Actions** (for development)

**Note**: MCP Remote Protocol server needs persistent deployment.

### Option 7: Local Development

For development and testing:
```bash
# Run ingestion worker locally
python main_orchestrator.py ingestion

# Run MCP Remote Protocol server locally
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
| **MCP Remote** | Remote API access | Worker + Remote Server | 8080 | OAuth 2.1 |
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

## MCP Remote Protocol Configuration

### OAuth 2.1 Setup

The MCP Remote Protocol server automatically registers a default OAuth client:

- **Client ID**: `mcp-slack-chatter-client`
- **Client Secret**: Generated on startup (check server logs)
- **Scopes**: `mcp:search`, `mcp:channels`, `mcp:stats`
- **Redirect URIs**: `http://localhost:3000/callback`, `https://*.replit.app/callback`

### Production OAuth Configuration

For production deployments:

1. **Configure proper redirect URIs** based on your deployment URL
2. **Enable HTTPS** for OAuth 2.1 flows
3. **Update CORS settings** in the FastAPI application
4. **Implement rate limiting** for OAuth endpoints
5. **Set up monitoring** for authentication failures

### Client Integration

**Local MCP (stdio):**
```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "slack-chatter",
      "args": ["mcp"]
    }
  }
}
```

**Remote MCP (OAuth 2.1):**
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

## Cloud Platform Specific Instructions

### Railway
1. Connect GitHub repo
2. Add environment variables in dashboard
3. Choose deployment command:
   - Ingestion: `python main_orchestrator.py ingestion`
   - Remote: `python main_orchestrator.py remote`
   - Combined: `python main_orchestrator.py combined`

### Render
1. Create Background Worker (for ingestion) + Web Service (for remote)
2. Set appropriate start commands
3. Configure port 8080 for remote server

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

**MCP Remote Protocol Server:**
```bash
# Test OAuth discovery
curl https://your-deployment.com/.well-known/oauth-authorization-server

# Test health endpoint
curl https://your-deployment.com/health

# Test MCP endpoint (should fail without auth)
curl -X POST https://your-deployment.com/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Common Issues

1. **Environment variables not set**: Check deployment platform configuration
2. **OAuth client secret**: Check server startup logs for generated secret
3. **Port configuration**: Ensure port 8080 is exposed for remote server
4. **CORS issues**: Update allowed origins for production domains
5. **Token expiration**: Implement token refresh in client applications

## Security Considerations

### Production Checklist

- [ ] **HTTPS enabled** for OAuth 2.1 flows
- [ ] **CORS configured** with specific origins (not `*`)
- [ ] **Environment variables secured** (not in code)
- [ ] **Rate limiting implemented** for OAuth endpoints
- [ ] **Monitoring enabled** for failed authentication attempts
- [ ] **Token expiration** properly handled in clients
- [ ] **Redirect URIs validated** and restricted
- [ ] **Firewall rules** configured for required ports only

The deployment guide now covers both the traditional ingestion worker deployment and the new MCP Remote Protocol server deployment options. 