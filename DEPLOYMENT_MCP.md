# MCP Tool Deployment Guide

## 🚀 How to Deploy Slack Chatter Service as an MCP Tool

Since this is a pure MCP (Model Context Protocol) tool, deployment is fundamentally different from REST APIs. MCP tools are executed as **subprocess tools** by MCP clients, not as web servers.

## 🎯 MCP Deployment Models

### 1. **Local Package Installation** (Recommended)

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

### 2. **Direct Python Execution**

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

### 3. **Docker Container Deployment**

For consistent environments across different systems:

```dockerfile
# Create Dockerfile
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

### 4. **Cloud Deployment with MCP Transport**

Deploy to cloud platforms but still use MCP protocol:

```json
{
  "mcpServers": {
    "slack-chatter": {
      "command": "ssh",
      "args": ["user@your-server.com", "slack-chatter", "mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-token"
      }
    }
  }
}
```

### 5. **Standalone Server Mode**

For shared team usage, run as a persistent background service:

```bash
# Start ingestion worker
slack-chatter combined  # Runs both ingestion and MCP server

# Or separate processes
slack-chatter ingestion &  # Background ingestion
slack-chatter mcp          # MCP server
```

## 🔧 MCP Client Examples

### Claude Desktop Configuration

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

### Custom Agent Configuration

For custom MCP agents, add this exact configuration:

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

**Required Environment Variables:**
- `SLACK_BOT_TOKEN` - Your Slack bot token (starts with `xoxb-`)
- `OPENAI_API_KEY` - Your OpenAI API key (starts with `sk-`)
- `SLACK_CHANNELS` - Comma-separated channel IDs where your bot is a member
- `PINECONE_API_KEY` - Your Pinecone API key
- `PINECONE_ENVIRONMENT` - Your Pinecone environment (e.g., `us-west1-gcp`)
- `NOTION_INTEGRATION_SECRET` - Your Notion integration secret
- `NOTION_DATABASE_ID` - Your Notion database ID

### Cline/Continue Configuration

Add to your editor's MCP configuration:

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

## 📦 Distribution Methods

### 1. **PyPI Package** (Public)

```bash
# Build and publish
python -m build
python -m twine upload dist/*

# Users install with:
pip install slack-chatter-service
```

### 2. **GitHub Releases** (Private/Public)

```bash
# Users install directly from GitHub
pip install git+https://github.com/yourusername/slack-chatter-service.git

# Or specific version
pip install git+https://github.com/yourusername/slack-chatter-service.git@v2.0.0
```

### 3. **Docker Hub** (Containerized)

```bash
# Build and push
docker build -t yourusername/slack-chatter-service:latest .
docker push yourusername/slack-chatter-service:latest

# Users run with:
docker pull yourusername/slack-chatter-service:latest
```

## 🏗️ Production Deployment Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   MCP Client    │    │   MCP Client    │
│    (Claude)     │    │    (Cline)      │    │   (Custom)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │         JSON-RPC over stdin/stdout          │
          │                      │                      │
    ┌─────▼──────────────────────▼──────────────────────▼─────┐
    │            Slack Chatter MCP Server                     │
    │                                                         │
    │  ┌─────────────────┐  ┌─────────────────┐              │
    │  │ Search Service  │  │ Search Agent    │              │
    │  └─────────────────┘  └─────────────────┘              │
    └─────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────▼───────────────────────────────────────┐
    │            Background Services                          │
    │                                                         │
    │  ┌─────────────────┐  ┌─────────────────┐              │
    │  │ Ingestion Worker│  │ Vector Storage  │              │
    │  └─────────────────┘  └─────────────────┘              │
    └─────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────▼───────────────────────────────────────┐
    │                External APIs                            │
    │                                                         │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
    │  │   Slack     │ │   OpenAI    │ │   Notion    │       │
    │  │ (Bot must be│ │             │ │             │       │
    │  │ in channels)│ │             │ │             │       │
    │  └─────────────┘ └─────────────┘ └─────────────┘       │
    └─────────────────────────────────────────────────────────┘
```

**⚠️ Prerequisites:**
- **Slack bot must be added to all channels** you want to index
- Bot needs appropriate permissions (`channels:history`, `channels:read`, `users:read`)
- OpenAI API key with embedding access (used for both embeddings AND intelligent query enhancement)
- Notion integration (optional) for logging

**🤖 AI-Powered Search Enhancement:**
- Uses LLM-powered search agent with deep vector search expertise
- Automatically enhances user queries for better semantic search results
- Powered by gpt-4o-mini using the same OpenAI key as embeddings
- **YAML-Configured**: Prompts loaded from `agent_prompt.yaml` for easy customization
- Cost: ~$0.001 per search query + embedding costs

## 🔐 Security Considerations

### Environment Variables
- **Never hardcode secrets** in MCP configuration
- Use environment variables or secret management
- Consider using `.env` files for local development

### Access Control
- MCP tools run with **user permissions**
- No network exposure by default
- Consider containerization for isolation

### Data Protection
- Local vector storage is file-based
- Consider encryption for sensitive data
- Regular backups of state files

## 🔧 Troubleshooting

### Bot Not Reading Messages
**Problem:** The ingestion worker shows 0 messages found or search returns no results.

**Solution:** Ensure your Slack bot is properly configured:
1. **Check bot permissions** in your Slack app settings
2. **Verify bot is added to channels** - bot must be a member of each channel
3. **Confirm channel IDs** are correct in `SLACK_CHANNELS` environment variable
4. **Test bot access** by running: `slack-chatter ingestion --validate-config`

### Common Permission Issues
- `missing_scope` error → Add required OAuth scopes to your Slack app
- `channel_not_found` → Check if channel ID is correct and bot has access
- `not_in_channel` → Bot needs to be invited to the channel first

### Getting Channel IDs
1. Right-click on channel in Slack
2. Select "View channel details"
3. Scroll down and click "Copy channel ID"
4. Use the ID (starts with 'C') in your `SLACK_CHANNELS` environment variable

## 🚀 Getting Started

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Set up your Slack bot:**
   - Create a Slack app and get your bot token
   - **⚠️ IMPORTANT:** Add your bot to the channels you want to index
   - Your bot needs to be a member of each channel to read messages
   - Get the channel IDs from Slack (right-click channel → View channel details → Copy channel ID)

3. **Set environment variables:**
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-token"
   export OPENAI_API_KEY="sk-your-key"
   export SLACK_CHANNELS="C1234567890,C0987654321"  # Channel IDs where your bot is a member
   ```

4. **Test the MCP server:**
   ```bash
   slack-chatter mcp --validate-config
   ```

5. **Configure your MCP client** (Claude, Cline, etc.)

6. **Start using the search tools!**

## 📝 Key Differences from REST APIs

| Aspect | REST API | MCP Tool |
|--------|----------|----------|
| **Transport** | HTTP/HTTPS | stdin/stdout JSON-RPC |
| **Deployment** | Web server | Subprocess execution |
| **Discovery** | API docs | Tool registration |
| **Authentication** | API keys/tokens | Environment variables |
| **Scaling** | Load balancers | Process management |
| **Monitoring** | Web metrics | Process monitoring |

The MCP model is **much simpler** - no web servers, no ports, no network configuration. Just install, configure, and use! 🎉 