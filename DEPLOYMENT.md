# 🔒 Secure Deployment Guide for Slack Message Vector Search API

## Overview
This is a **secure** Slack message vector search API that requires proper authentication and configuration. It provides REST API endpoints for authorized agents to search indexed Slack messages using AI-powered semantic search.

## 🛡️ Security Features

- **API Key Authentication**: Bearer token authentication for all endpoints
- **Rate Limiting**: Per-IP rate limiting to prevent abuse
- **Input Validation**: Comprehensive input sanitization and validation
- **CORS Protection**: Restrictive cross-origin request policies
- **Security Headers**: Full set of security headers for protection
- **Access Logging**: Comprehensive audit trail for all requests
- **SSL/TLS Support**: HTTPS enforcement for production

## 🔧 Required Setup

### 1. Generate Secure API Key

```bash
# Generate a cryptographically secure API key
python utils.py
```

Save the generated 64-character API key securely.

### 2. Required Environment Variables

```bash
# Security Configuration (REQUIRED)
export API_KEY="your-64-character-secure-api-key"
export ALLOWED_ORIGINS="https://your-agent-domain.com"
export ENABLE_DOCS="false"  # Only enable for development

# SSL Configuration (Production)
export SSL_KEYFILE="/path/to/your/private.key"
export SSL_CERTFILE="/path/to/your/certificate.crt"

# Existing Slack/AI Configuration
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_CHANNELS="general,random,development"
export OPENAI_API_KEY="sk-your-openai-api-key"
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_ENVIRONMENT="your-pinecone-environment"
export PINECONE_INDEX_NAME="slack-messages"
export NOTION_INTEGRATION_SECRET="secret_your-notion-integration-secret"
export NOTION_DATABASE_ID="your-notion-database-id"
```

### 3. Agent Repository Configuration

In your agent repository, set these environment variables:

```bash
# API connection configuration
export SLACK_SEARCH_API_URL="https://your-secure-api-domain.com"
export SLACK_SEARCH_API_KEY="your-64-character-secure-api-key"
```

## 🚀 Deployment Configuration

### Cloud Run Deployment

- **Deployment Type**: Cloud Run (Web Service)
- **Run Command**: `python main.py`
- **Build Command**: Leave empty
- **Port**: 5000 (automatically configured)
- **Environment**: Python 3.11+ with auto-installed dependencies

### Environment Variable Setup

In your deployment platform, configure all required environment variables:

1. **API_KEY**: The 64-character secure key you generated
2. **ALLOWED_ORIGINS**: Comma-separated list of allowed domains (e.g., "https://agent1.com,https://agent2.com")
3. **SLACK_BOT_TOKEN**: Your Slack bot token
4. **SLACK_CHANNELS**: Comma-separated channel IDs
5. **OPENAI_API_KEY**: Your OpenAI API key
6. **PINECONE_API_KEY**: Your Pinecone API key
7. **PINECONE_ENVIRONMENT**: Your Pinecone environment
8. **NOTION_INTEGRATION_SECRET**: Your Notion integration secret
9. **NOTION_DATABASE_ID**: Your Notion database ID

Optional security variables:
- **ENABLE_DOCS**: Set to "true" only for development/testing
- **SSL_KEYFILE**: Path to SSL private key (for custom SSL)
- **SSL_CERTFILE**: Path to SSL certificate (for custom SSL)

## 🔍 Testing Your Deployment

### 1. Run Security Tests

```bash
# Set test environment variables
export TEST_API_URL="https://your-deployed-api.com"
export TEST_API_KEY="your-64-character-secure-api-key"

# Run comprehensive security tests
python test_security.py
```

Expected output:
```
🔒 Starting Security Test Suite...
✅ PASS API key format: Valid characters
✅ PASS No auth header rejected - Status: 401
✅ PASS Invalid API key rejected - Status: 401
✅ PASS Valid API key accepted - Status: 200
...
🎉 All security tests passed!
```

### 2. Test Agent Integration

```python
import requests
import os

# Test from your agent repository
api_url = os.getenv("SLACK_SEARCH_API_URL")
api_key = os.getenv("SLACK_SEARCH_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Test search
response = requests.post(
    f"{api_url}/search",
    json={"query": "test deployment", "top_k": 5},
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Results: {len(response.json())} messages found")
```

## 📊 API Endpoints & Rate Limits

All endpoints require Authentication header: `Authorization: Bearer YOUR_API_KEY`

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/search` | POST | 60/minute | Semantic search with full options |
| `/search` | GET | 60/minute | Simple search with query parameters |
| `/health` | GET | 30/minute | Health check and status |
| `/stats` | GET | 20/minute | Index statistics |
| `/channels` | GET | 30/minute | List indexed channels |
| `/refresh` | POST | 5/minute | Trigger manual refresh |

## 🚨 Security Monitoring

### Key Metrics to Monitor

1. **Authentication Failures (401 errors)**
   - Multiple failures from same IP may indicate attack
   - Set up alerts for unusual patterns

2. **Rate Limit Violations (429 errors)**
   - High rate limit hits may indicate abuse
   - Monitor for unusual usage patterns

3. **Search Query Patterns**
   - Log unusual or suspicious queries
   - Monitor for data extraction attempts

4. **Error Rates**
   - High 500 error rates indicate service issues
   - Monitor overall service health

### Log Analysis

The API logs all requests with:
- Client IP address
- Timestamp
- HTTP method and path
- User agent
- Response status and time
- Search queries (first 50 characters)

## 🔐 Production Security Checklist

Before going live:

- [ ] **API Key Generated**: 64-character secure key generated and stored safely
- [ ] **Environment Variables Set**: All required variables configured
- [ ] **CORS Configured**: ALLOWED_ORIGINS set to your agent domain(s) only
- [ ] **HTTPS Enabled**: SSL/TLS configured and working
- [ ] **Documentation Disabled**: ENABLE_DOCS set to "false"
- [ ] **Rate Limiting Tested**: Verified rate limits are working
- [ ] **Authentication Tested**: Verified unauthorized access is blocked
- [ ] **Security Tests Passed**: All tests in test_security.py pass
- [ ] **Agent Integration Tested**: Verified agent can connect and search
- [ ] **Monitoring Setup**: Logging and alerting configured
- [ ] **Firewall Rules**: Network access properly restricted

## 🛠️ Troubleshooting

### Common Issues

**401 Unauthorized**
- Check API key is exactly 64 characters
- Verify Authorization header: `Bearer YOUR_API_KEY`
- Ensure API_KEY environment variable is set correctly

**429 Too Many Requests**
- Implement exponential backoff in your agent
- Check if you're exceeding rate limits
- Consider if you need higher limits

**CORS Errors**
- Verify your domain is in ALLOWED_ORIGINS
- Ensure you're using HTTPS, not HTTP
- Check domain spelling exactly

**500 Internal Server Error**
- Check all environment variables are set
- Verify API services (OpenAI, Slack, etc.) are accessible
- Review application logs for details

### Testing Individual Components

```bash
# Test authentication
curl -H "Authorization: Bearer YOUR_API_KEY" https://your-api.com/health

# Test without authentication (should fail)
curl https://your-api.com/health

# Test search
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "top_k": 3}' \
     https://your-api.com/search
```

## 📝 What Changed from Previous Version

This secure version includes:

1. **Mandatory Authentication**: All endpoints now require API key
2. **Rate Limiting**: Per-IP limits on all endpoints
3. **Input Validation**: Strict validation of all inputs
4. **Security Headers**: Full security header suite
5. **CORS Restrictions**: Only allowed domains can access
6. **Comprehensive Logging**: Detailed audit trail
7. **SSL Support**: HTTPS enforcement capabilities

## 🎯 Next Steps

1. **Deploy the secure API** with all environment variables
2. **Run security tests** to verify everything works
3. **Update your agent** to use the new authentication
4. **Monitor logs** for any security issues
5. **Set up alerts** for authentication failures and rate limits

Your Slack data is now properly protected with enterprise-grade security! 🔒