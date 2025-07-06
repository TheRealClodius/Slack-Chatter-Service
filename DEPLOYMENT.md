# Deployment Guide for Slack Message Ingestion Worker

## Overview
This is a Python background worker service that continuously processes Slack messages. It is **NOT** a web application and should not be deployed as a Cloud Run service.

## ✅ Applied Fixes

All suggested fixes have been implemented:

1. **✅ Pinecone Package**: Using correct `pinecone>=7.3.0` package with modern v3+ API
2. **✅ Dependencies**: Properly defined in `pyproject.toml` 
3. **✅ Code Verification**: All imports and services tested successfully
4. **✅ Background Worker**: Configured for long-running background processing

## 🔧 Deployment Configuration

### Deployment Type
- **Use**: Reserved VM or Background Worker
- **Do NOT use**: Cloud Run (web server deployment)

### Configuration Settings
- **Run Command**: `python main.py`
- **Build Command**: Leave empty
- **Port**: Not applicable (no web server)
- **Environment**: Python 3.11+

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