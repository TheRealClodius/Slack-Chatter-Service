# AI Agent Integration Prompt for Slack-Chatter-Service

## Context
I need to integrate a secure Slack Message Vector Search API into my AI agent. The API is already deployed and secured with enterprise-grade authentication and rate limiting.

## API Details
- **Base URL**: `http://localhost:5000` (or your deployed URL)
- **Authentication**: Bearer token authentication required
- **API Key**: 64-character secure key (already generated)
- **Rate Limits**: 60 requests/minute for search, 30 requests/minute for health checks
- **Security**: Full input validation, CORS protection, comprehensive security headers

## Available Endpoints

### 1. Health Check
- **Endpoint**: `GET /health`
- **Purpose**: Check API status and availability
- **Authentication**: Required
- **Rate Limit**: 30/minute
- **Response**: JSON with status, message, background_worker_running, vector_storage_available

### 2. Search Messages (POST)
- **Endpoint**: `POST /search`
- **Purpose**: Semantic search through Slack messages
- **Authentication**: Required
- **Rate Limit**: 60/minute
- **Body**: JSON with query, top_k (1-50), optional filters (channel, user, date range)
- **Response**: Array of search results with message_id, text, user_name, channel_name, timestamp, similarity_score, metadata

### 3. Search Messages (GET)
- **Endpoint**: `GET /search`
- **Purpose**: Same as POST but via query parameters
- **Authentication**: Required
- **Rate Limit**: 60/minute
- **Parameters**: q (query), top_k, channel, user, date_from, date_to

### 4. Get Index Stats
- **Endpoint**: `GET /stats`
- **Purpose**: Get information about indexed messages
- **Authentication**: Required
- **Rate Limit**: 20/minute
- **Response**: JSON with total_vectors, channels_indexed, last_refresh, status

### 5. List Channels
- **Endpoint**: `GET /channels`
- **Purpose**: Get list of available Slack channels
- **Authentication**: Required
- **Rate Limit**: 30/minute
- **Response**: Array of channel names

### 6. Trigger Refresh
- **Endpoint**: `POST /refresh`
- **Purpose**: Manually trigger reindexing of Slack messages
- **Authentication**: Required
- **Rate Limit**: 5/minute
- **Response**: JSON with status message

## Security Requirements
1. **API Key**: Must be stored securely (environment variable or secure vault)
2. **Authentication**: Use Bearer token in Authorization header
3. **Rate Limiting**: Respect rate limits to avoid 429 errors
4. **Input Validation**: API validates all inputs, but client should also validate
5. **Error Handling**: Handle 401 (unauthorized), 429 (rate limit), 422 (validation errors)
6. **HTTPS**: Use HTTPS in production deployments

## Integration Requirements
Please generate code that:

1. **Creates a SlackSearchTool class** that can be used as a tool by my AI agent
2. **Implements proper authentication** with the API key
3. **Includes comprehensive error handling** for all possible API responses
4. **Respects rate limits** with exponential backoff retry logic
5. **Provides a clean interface** for the agent to search Slack messages
6. **Includes input validation** before sending requests to the API
7. **Supports all search parameters** (query, filters, date ranges)
8. **Returns structured results** that the agent can easily process
9. **Includes logging** for debugging and monitoring
10. **Has proper docstrings** and type hints

## Example Usage Pattern
The agent should be able to use it like this:
```python
slack_tool = SlackSearchTool(api_key="your_api_key", base_url="http://localhost:5000")

# Search for messages
results = slack_tool.search("python debugging", top_k=5, channel="engineering")

# Check if service is healthy
health = slack_tool.health_check()

# Get available channels
channels = slack_tool.list_channels()
```

## Error Scenarios to Handle
- **401 Unauthorized**: Invalid or missing API key
- **429 Too Many Requests**: Rate limit exceeded
- **422 Unprocessable Entity**: Invalid input parameters
- **500 Internal Server Error**: API server issues
- **Connection errors**: Network issues, timeout, service unavailable

## Configuration
- API key should be configurable via environment variable `SLACK_SEARCH_API_KEY`
- Base URL should be configurable via environment variable `SLACK_SEARCH_BASE_URL`
- Timeout settings should be configurable (default: 30 seconds)
- Retry settings should be configurable (default: 3 retries with exponential backoff)

## Response Format
All search results should be returned in a consistent format that includes:
- Message content and metadata
- Relevance score
- Source information (channel, user, timestamp)
- Proper error messages for failed requests

Generate production-ready Python code that implements this integration with proper error handling, logging, and security practices. The code should be ready to use immediately without additional modifications. 