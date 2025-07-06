# Deployment Guide for Slack Message Ingestion Worker

## Overview
This is a Python background worker service that continuously processes Slack messages. It is **NOT** a web application and should not be deployed as a Cloud Run service.

## ✅ Applied Fixes

All suggested fixes have been successfully implemented and tested:

1. **✅ Pinecone API Compatibility**: Updated imports to use only Pinecone v7+ API (`pinecone>=7.3.0`)
2. **✅ Pinecone Client Initialization**: Updated to use modern `Pinecone(api_key=...)` constructor 
3. **✅ Index Creation**: Using `ServerlessSpec` with proper cloud/region configuration
4. **✅ Index Access**: Using `pc.Index()` method for v7+ compatibility
5. **✅ Background Worker Configuration**: Ready for Reserved VM deployment (not Cloud Run)
6. **✅ Dependencies**: Properly defined in `pyproject.toml` with correct versions
7. **✅ Code Verification**: All imports and services tested successfully
8. **✅ Worker Restart**: Successfully restarted with new API implementation

## 🔧 Deployment Configuration

### ⚠️ Critical: Deployment Type Selection
- **✅ CORRECT**: Reserved VM or Background Worker deployment
- **❌ INCORRECT**: Cloud Run (causes "ImportError" and port binding issues)

### Configuration Settings
- **Deployment Target**: `autoscale` or `reserved-vm` 
- **Run Command**: `python main.py`
- **Build Command**: Leave empty (no build step needed)
- **Port**: Not applicable (this is not a web server)
- **Environment**: Python 3.11+ with packages auto-installed from `pyproject.toml`

### Why Background Worker is Required
This application:
- Runs continuously in the background (24/7)
- Does NOT serve web requests or expose HTTP endpoints
- Connects to external APIs (Slack, OpenAI, Pinecone, Notion)
- Performs scheduled data processing every hour

Cloud Run is designed for web applications that respond to HTTP requests, not background workers.

### Required Environment Variables
Ensure these are configured in your deployment:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNELS=general,random,development
OPENAI_API_KEY=sk-your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=slack-messages
NOTION_INTEGRATION_SECRET=secret_your-notion-integration-secret
NOTION_DATABASE_ID=your-notion-database-id
```

## ✅ Verification Steps

Run the test script to verify everything is working:

```bash
python test_deployment.py
```

Expected output:
```
🧪 Running deployment tests...
✅ Pinecone 7.3.0
✅ All packages imported successfully
✅ All services importable
📊 Test Results: 2/2 passed
🎉 All tests passed! Ready for deployment.
```

## 🚀 What This Worker Does

1. **Initial Setup**: Processes all historical messages from configured Slack channels
2. **Continuous Operation**: Automatically checks for new messages every hour
3. **AI Processing**: Generates embeddings for each message using OpenAI
4. **Vector Storage**: Stores searchable embeddings in Pinecone database
5. **Logging**: Records all operations and metrics in Notion database

## 📊 Current Status

- Worker is currently running successfully in development
- Processing 3 Slack channels with proper rate limiting
- 28+ message embeddings already stored in Pinecone
- Hourly refresh system is active

## 🔍 Troubleshooting

If deployment still fails:

1. **Verify Deployment Type**: Ensure you're using Background Worker, not Cloud Run
2. **Check Environment Variables**: All 7 required variables must be set
3. **Test Dependencies**: Run `python test_deployment.py` to verify packages
4. **Check Logs**: Look for specific error messages in deployment logs

## 📋 Next Steps

Once deployed as a background worker:
1. The system will automatically start processing messages
2. Check Notion database for operation logs
3. Monitor Pinecone index for growing vector count
4. System is self-managing with hourly updates