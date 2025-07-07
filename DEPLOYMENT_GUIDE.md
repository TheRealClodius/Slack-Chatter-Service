# Deployment Guide

## Overview

The Slack Chatter Service has two components:
1. **Ingestion Worker** - Runs 24/7 to keep embeddings fresh (needs deployment)
2. **MCP Tool** - Invoked on-demand by clients (no deployment needed)

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

3. **Deploy with one command:**
   ```bash
   python replit_deploy.py
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

1. **Go to [Railway.app](https://railway.app)**
2. **Sign in with GitHub**
3. **Create New Project → Deploy from GitHub repo**
4. **Add environment variables in dashboard**
5. **Set start command:** `python main_orchestrator.py ingestion`
6. **Deploy automatically!**

**Cost**: ~$5-10/month

### Option 3: Render (Background Worker)

1. **Go to [Render.com](https://render.com)**
2. **Create New → Background Worker**
3. **Connect GitHub repository**
4. **Set start command:** `python main_orchestrator.py ingestion`
5. **Add environment variables**
6. **Deploy!**

**Cost**: ~$7/month

### Option 4: Docker Deployment (Recommended)

1. **Build and run with Docker Compose:**
```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your actual values

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f slack-ingestion-worker

# Stop
docker-compose down
```

2. **Deploy to cloud platforms:**
   - **Railway**: Connect repo, deploy automatically
   - **Render**: Deploy as background worker
   - **DigitalOcean App Platform**: Deploy as worker service
   - **AWS ECS/Fargate**: Deploy container
   - **Google Cloud Run**: Deploy as background service

### Option 5: Traditional VPS Deployment

1. **Setup on any Linux server:**
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

# Run ingestion worker
python main_orchestrator.py ingestion
```

2. **Process management with systemd:**
```ini
# /etc/systemd/system/slack-chatter.service
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

### Option 6: Serverless/Cron-based (Alternative)

If you prefer serverless, you could modify the ingestion to run as scheduled functions:

- **AWS Lambda** + CloudWatch Events
- **Google Cloud Functions** + Cloud Scheduler  
- **Vercel Cron** + Vercel Functions
- **GitHub Actions** (for development)

### Option 7: Local Development

For development and testing:
```bash
# Run locally
python main_orchestrator.py ingestion

# Or combined mode (ingestion + MCP server)
python main_orchestrator.py combined
```

## Platform Comparison

| Platform | Cost/Month | Setup Time | Ease of Use | Best For |
|----------|------------|------------|-------------|----------|
| **Replit** | ~$5 | 5 mins | ⭐⭐⭐⭐⭐ | Beginners, learning |
| **Railway** | ~$5-10 | 10 mins | ⭐⭐⭐⭐ | Production apps |
| **Render** | ~$7 | 15 mins | ⭐⭐⭐ | Background workers |
| **Docker** | Varies | 30 mins | ⭐⭐ | Maximum flexibility |
| **VPS** | ~$5-20 | 1+ hour | ⭐ | Full control |

## Cloud Platform Specific Instructions

### Railway
1. Connect GitHub repo
2. Add environment variables in dashboard
3. Deploy automatically

### Render
1. Create new Background Worker
2. Connect repo
3. Set start command: `python main_orchestrator.py ingestion`
4. Add environment variables

### Replit
1. Import from GitHub
2. Add environment variables in Secrets tab
3. Run: `python replit_deploy.py`
4. Enable "Always On"

### DigitalOcean App Platform
1. Create new App
2. Add Worker component
3. Set run command: `python main_orchestrator.py ingestion`
4. Configure environment variables

### AWS ECS
1. Create task definition with container
2. Use image: `your-registry/slack-chatter-service:latest`
3. Set environment variables
4. Create service with desired count = 1

## Monitoring & Logs

The ingestion worker logs to:
- **Console**: Real-time ingestion progress
- **Notion**: Ingestion success/failure logs
- **Docker logs**: `docker-compose logs -f`

## Resource Requirements

- **CPU**: 0.5-1 CPU (mostly I/O bound)
- **Memory**: 256-512MB (depends on message volume)
- **Storage**: Minimal (only for logs and state)
- **Network**: Outbound API calls to Slack, OpenAI, Pinecone, Notion

## Scaling

- **Single instance**: Sufficient for most teams
- **Multiple instances**: Not recommended (could cause duplicate processing)
- **Horizontal scaling**: Scale via multiple independent deployments per team

## Cost Estimation

Monthly costs (estimated):
- **Replit**: $5/month (Always On)
- **VPS**: $5-20/month (DigitalOcean, Linode)
- **Container hosting**: $7-25/month (Railway, Render)
- **Serverless**: $0-5/month (AWS Lambda, functions)
- **API costs**: 
  - OpenAI: ~$0.50-5/month (embeddings)
  - Pinecone: ~$70/month (1M vectors)
  - Notion: Free

## Security

- Use environment variables for secrets
- Don't commit credentials to git
- Use least-privilege Slack bot permissions
- Consider using secret management services 