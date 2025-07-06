# 🔒 Security Documentation

## Overview

This Slack Message Vector Search API implements enterprise-grade security measures to protect your Slack data and ensure secure access for authorized agents only.

## 🛡️ Security Features Implemented

### 1. **API Key Authentication**
- **Bearer Token Authentication**: All endpoints require a valid API key
- **Constant-Time Comparison**: Prevents timing attacks
- **Minimum 32-character requirement**: Ensures cryptographic strength
- **Secure Generation**: Uses cryptographically secure random generation

### 2. **Rate Limiting**
- **Per-IP Rate Limiting**: Prevents abuse and DoS attacks
- **Endpoint-Specific Limits**:
  - Search: 60 requests/minute
  - Health: 30 requests/minute
  - Stats: 20 requests/minute
  - Channels: 30 requests/minute
  - Refresh: 5 requests/minute

### 3. **Input Validation & Sanitization**
- **Query Length Limits**: 1-1000 characters
- **Result Limits**: 1-50 results maximum
- **Date Format Validation**: YYYY-MM-DD format only
- **Dangerous Character Filtering**: Prevents XSS and injection attacks
- **Request Size Limits**: Prevents oversized requests

### 4. **CORS Protection**
- **Restricted Origins**: Only allows specified domains
- **Limited Methods**: Only GET and POST allowed
- **Specific Headers**: Only Authorization and Content-Type

### 5. **Security Headers**
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-Frame-Options**: Prevents clickjacking
- **X-XSS-Protection**: Enables XSS filtering
- **Strict-Transport-Security**: Enforces HTTPS
- **Content-Security-Policy**: Prevents code injection
- **Referrer-Policy**: Controls referrer information

### 6. **Comprehensive Logging**
- **Access Logging**: All API requests logged with IP, timestamp, and user agent
- **Authentication Logging**: Failed authentication attempts tracked
- **Audit Trail**: Search queries and results logged for security monitoring
- **Error Logging**: Detailed error logging without exposing sensitive data

### 7. **Information Disclosure Protection**
- **Minimal Root Endpoint**: No longer exposes internal endpoints
- **Conditional Documentation**: API docs only enabled when explicitly configured
- **Sanitized Error Messages**: Generic error messages prevent information leakage

## 🔧 Setup Instructions

### 1. Generate a Secure API Key

```bash
# Generate a new secure API key
python utils.py
```

This will output a 64-character cryptographically secure API key.

### 2. Required Environment Variables

```bash
# Security Configuration
export API_KEY="your-64-character-secure-api-key"
export ALLOWED_ORIGINS="https://your-agent-domain.com,https://localhost:3000"
export ENABLE_DOCS="false"  # Set to "true" only for development

# SSL Configuration (for production)
export SSL_KEYFILE="/path/to/your/private.key"
export SSL_CERTFILE="/path/to/your/certificate.crt"

# Existing Configuration (unchanged)
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_CHANNELS="general,random,development"
export OPENAI_API_KEY="sk-your-openai-api-key"
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_ENVIRONMENT="your-pinecone-environment"
export PINECONE_INDEX_NAME="slack-messages"
export NOTION_INTEGRATION_SECRET="secret_your-notion-integration-secret"
export NOTION_DATABASE_ID="your-notion-database-id"
```

### 3. Configure for Your Agent Repository

Update `ALLOWED_ORIGINS` to include your agent's domain:

```bash
export ALLOWED_ORIGINS="https://your-agent-repo-domain.com"
```

## 📡 API Usage

### Authentication

All API requests must include the API key in the Authorization header:

```bash
# Example curl request
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://your-api-domain.com/search \
     -d '{"query": "deployment issues", "top_k": 5}'
```

### Rate Limiting

If you exceed rate limits, you'll receive a 429 status code. Implement exponential backoff in your agent:

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

### Agent Integration Example

```python
import requests
import os

class SlackSearchTool:
    def __init__(self):
        self.api_key = os.getenv("SLACK_SEARCH_API_KEY")
        self.base_url = os.getenv("SLACK_SEARCH_API_URL")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def search_messages(self, query: str, top_k: int = 10, channel: str = None):
        """Search Slack messages securely"""
        payload = {
            "query": query,
            "top_k": min(top_k, 50),  # Respect API limits
        }
        
        if channel:
            payload["channel_filter"] = channel
        
        try:
            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Search failed: {e}")
            return None
```

## 🚨 Security Monitoring

### Key Metrics to Monitor

1. **Failed Authentication Attempts**
   - Monitor logs for 401 errors
   - Implement alerting for multiple failures from same IP

2. **Rate Limit Violations**
   - Track 429 responses
   - Identify potential abuse patterns

3. **Unusual Search Patterns**
   - Monitor for suspicious queries
   - Track search volume anomalies

4. **Error Rates**
   - Monitor 500 errors
   - Track service availability

### Log Analysis

Search logs contain:
- Client IP address
- Request timestamp
- Search query (first 50 characters)
- Results count
- Response time

Example log entry:
```
2025-01-07 10:30:15 - api_server - INFO - Search request from 192.168.1.100: query='deployment issues with authentication...' top_k=5
```

## 🔐 Production Deployment

### 1. SSL/TLS Configuration

**Always use HTTPS in production:**

```bash
# Generate SSL certificates (using Let's Encrypt)
sudo certbot certonly --standalone -d your-api-domain.com

# Set environment variables
export SSL_KEYFILE="/etc/letsencrypt/live/your-api-domain.com/privkey.pem"
export SSL_CERTFILE="/etc/letsencrypt/live/your-api-domain.com/fullchain.pem"
```

### 2. Firewall Configuration

**Restrict access to necessary ports only:**

```bash
# Allow only HTTPS traffic
sudo ufw allow 443/tcp
sudo ufw deny 80/tcp
sudo ufw enable
```

### 3. Environment Security

**Secure environment variable storage:**

```bash
# Use a secure secrets management system
# AWS Secrets Manager, HashiCorp Vault, etc.

# For Docker deployments, use secrets
docker secret create slack_api_key /path/to/api_key_file
```

### 4. Regular Security Updates

```bash
# Keep dependencies updated
pip install --upgrade -r requirements.txt

# Monitor for security vulnerabilities
pip-audit
```

## 🛠️ Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check API key format (64 characters, letters/digits/-/_)
   - Verify Authorization header format: `Bearer YOUR_API_KEY`
   - Ensure API_KEY environment variable is set

2. **429 Too Many Requests**
   - Implement rate limiting in your agent
   - Use exponential backoff for retries

3. **CORS Errors**
   - Verify your domain is in ALLOWED_ORIGINS
   - Check that you're using HTTPS (not HTTP)

4. **SSL Certificate Issues**
   - Verify certificate files exist and are readable
   - Check certificate expiration date

## 📋 Security Checklist

Before deploying to production:

- [ ] Generate secure API key (64+ characters)
- [ ] Set all required environment variables
- [ ] Configure ALLOWED_ORIGINS for your agent domain
- [ ] Enable SSL/TLS with valid certificates
- [ ] Disable API documentation (ENABLE_DOCS=false)
- [ ] Set up monitoring and alerting
- [ ] Configure firewall rules
- [ ] Test authentication from agent repository
- [ ] Verify rate limiting is working
- [ ] Review log output for sensitive data exposure

## 🆘 Support

If you encounter security issues:

1. Check the logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test with curl to isolate agent vs API issues
4. Review the security headers in responses

## 📝 License & Compliance

This API implements security best practices for:
- Data protection
- Access control
- Audit logging
- Secure communication

Ensure compliance with your organization's security policies and any applicable regulations (GDPR, CCPA, etc.) regarding Slack data handling. 