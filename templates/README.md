# Client Implementation Templates

This directory contains templates for building **client applications** that use the Slack Chatter MCP server.

## 📁 Templates Overview

### `slack_search_tool.py`
**MCP Client Implementation** - Shows how to connect to and use the Slack Chatter MCP server from your own application.

**Key Features:**
- MCP client connection handling
- Tool method wrappers (`search_slack_messages`, `get_slack_channels`, `get_search_stats`)
- Smart search functionality with LLM integration points
- Result formatting and processing
- Error handling and reconnection logic

### `client_prompt.yaml`
**Client-side System Prompt** - Template for the LLM prompt that determines when and how to use Slack search.

**Key Features:**
- Guidelines for when to search Slack history
- Search strategy and best practices
- Response formatting guidelines
- Example interactions and workflows
- Configuration options for search behavior

### `example_usage.py`
**Working Examples** - Complete examples showing different integration patterns.

**Includes:**
- Basic search functionality
- Smart search with LLM integration
- Filtered searches (user, channel, date)
- Application integration patterns
- Performance testing examples

## 🚀 Quick Start

### 1. Copy and Customize the Template

```bash
# Copy the template to your project
cp templates/slack_search_tool.py your_project/
cp templates/client_prompt.yaml your_project/

# Customize for your needs
vim your_project/slack_search_tool.py
vim your_project/client_prompt.yaml
```

### 2. Install Dependencies

```bash
# You'll need these in your client application
pip install asyncio pydantic
# pip install mcp-client  # When MCP client library becomes available
```

### 3. Basic Usage

```python
from slack_search_tool import SlackSearchTool

# Initialize the tool
search_tool = SlackSearchTool([
    "python", "/path/to/slack-chatter-service/main_orchestrator.py", "mcp"
])

# Connect and search
await search_tool.connect()
results = await search_tool.search_slack_messages("deployment issues")
await search_tool.disconnect()
```

## 🔧 Integration Patterns

### Pattern 1: Direct Tool Usage
Use the `SlackSearchTool` directly in your application for simple search functionality.

```python
class MyApp:
    def __init__(self):
        self.slack_search = SlackSearchTool(mcp_command)
    
    async def handle_question(self, question):
        results = await self.slack_search.search_slack_messages(question)
        return self.format_results(results)
```

### Pattern 2: LLM Integration
Integrate with your main LLM to automatically determine when to search Slack.

```python
class AIAssistant:
    def __init__(self):
        self.slack_search = SlackSearchTool(mcp_command)
        self.llm = YourLLMClient()
        self.system_prompt = load_prompt("client_prompt.yaml")
    
    async def chat(self, user_message):
        # Your LLM decides whether to use Slack search
        response = await self.llm.chat(
            system=self.system_prompt,
            user=user_message,
            tools=[self.slack_search]  # Make tool available
        )
        return response
```

### Pattern 3: Multi-Step Search
Implement intelligent multi-step search workflows.

```python
async def deep_search(self, topic):
    # Step 1: Broad search
    broad_results = await self.slack_search.search_slack_messages(topic, top_k=20)
    
    # Step 2: Analyze results and refine
    refined_query = await self.extract_key_terms(broad_results)
    focused_results = await self.slack_search.search_slack_messages(refined_query, top_k=10)
    
    # Step 3: Get related discussions
    related = await self.find_related_discussions(focused_results)
    
    return self.synthesize_results([broad_results, focused_results, related])
```

## 🎯 Customization Guide

### Modifying the Search Tool

**Add New Methods:**
```python
class CustomSlackSearchTool(SlackSearchTool):
    async def search_by_sentiment(self, sentiment: str):
        """Custom search method for finding messages by sentiment"""
        # Your custom logic here
        pass
    
    async def get_user_activity(self, username: str):
        """Get activity summary for a specific user"""
        # Your custom logic here
        pass
```

**Custom Result Processing:**
```python
def _format_search_response(self, question, search_query, results):
    """Override to customize response formatting"""
    # Your custom formatting logic
    return formatted_response
```

### Modifying the Client Prompt

**Add Domain-Specific Guidelines:**
```yaml
system_prompt: |
  # Add your company-specific context
  
  ## Company Context
  We are a [industry] company with [specific context].
  Our main projects include: [list projects].
  Key team members: [list key people].
  
  ## Domain-Specific Search Patterns
  - For technical issues, search in #dev-team and #infrastructure
  - For product decisions, check #product and #leadership
  - For customer issues, look in #support and #customer-success
```

**Custom Tool Configuration:**
```yaml
slack_search:
  default_results: 15  # Increase for more comprehensive results
  max_results: 100     # Higher limit for complex queries
  include_urls: true   # Always include Slack URLs
  search_timeout: 60   # Longer timeout for complex searches
```

## 📋 MCP Protocol Details

### Tool Interface
Your client will call these MCP tools:

```json
{
  "search_slack_messages": {
    "query": "string",
    "top_k": "integer",
    "channel_filter": "string?",
    "user_filter": "string?", 
    "date_from": "string?",
    "date_to": "string?"
  },
  "get_slack_channels": {},
  "get_search_stats": {}
}
```

### Server Configuration
The Slack Chatter MCP server needs to be running:

```bash
# Start the MCP server
python main_orchestrator.py mcp

# Or use combined mode (ingestion + MCP)
python main_orchestrator.py combined
```

### Environment Variables
Your client needs access to configure the MCP server:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export OPENAI_API_KEY="sk-your-key"
export SLACK_CHANNELS="C1234567890,C0987654321"
# ... other required variables
```

## 🔍 Debugging and Testing

### Test the Connection
```python
async def test_connection():
    tool = SlackSearchTool(mcp_command)
    try:
        await tool.connect()
        stats = await tool.get_search_stats()
        print(f"Connected! Index has {stats['total_messages']} messages")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
    finally:
        await tool.disconnect()
```

### Debug Search Queries
```python
async def debug_search(query):
    tool = SlackSearchTool(mcp_command)
    await tool.connect()
    
    print(f"Searching for: {query}")
    results = await tool.search_slack_messages(query, top_k=5)
    
    for i, result in enumerate(results):
        print(f"{i+1}. Score: {result.relevance_score:.2f}")
        print(f"   {result.user} in #{result.channel}")
        print(f"   {result.text[:100]}...")
        print()
    
    await tool.disconnect()
```

### Monitor Performance
```python
import time

async def benchmark_search(queries):
    tool = SlackSearchTool(mcp_command)
    await tool.connect()
    
    for query in queries:
        start = time.time()
        results = await tool.search_slack_messages(query)
        duration = time.time() - start
        print(f"Query: {query}")
        print(f"Results: {len(results)}, Time: {duration:.2f}s")
    
    await tool.disconnect()
```

## 🚀 Production Deployment

### Error Handling
```python
async def robust_search(self, query, retries=3):
    for attempt in range(retries):
        try:
            return await self.slack_search.search_slack_messages(query)
        except Exception as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Connection Pooling
```python
class SlackSearchPool:
    def __init__(self, pool_size=5):
        self.pool = []
        self.pool_size = pool_size
    
    async def get_client(self):
        if self.pool:
            return self.pool.pop()
        return SlackSearchTool(mcp_command)
    
    async def return_client(self, client):
        if len(self.pool) < self.pool_size:
            self.pool.append(client)
        else:
            await client.disconnect()
```

### Health Monitoring
```python
async def health_check(self):
    try:
        stats = await self.slack_search.get_search_stats()
        return {
            "status": "healthy",
            "last_updated": stats.get("last_updated"),
            "total_messages": stats.get("total_messages")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## 💡 Best Practices

1. **Connection Management**: Always use try/finally blocks to ensure disconnection
2. **Error Handling**: Implement retry logic for network-related failures
3. **Rate Limiting**: Don't overwhelm the MCP server with too many concurrent requests
4. **Caching**: Cache frequently requested information like channel lists
5. **Logging**: Log search queries and performance metrics for debugging
6. **Security**: Never log sensitive information from Slack messages
7. **Testing**: Test with realistic data volumes and query patterns

## 📚 Examples

See the `examples/` directory for complete working examples:
- `basic_client.py` - Simple search client
- `chatbot_integration.py` - Integration with chatbot frameworks
- `web_api_wrapper.py` - REST API wrapper around MCP tools
- `batch_processor.py` - Bulk search operations

## 🤝 Contributing

When creating new templates or examples:
1. Follow the existing code structure
2. Include comprehensive error handling
3. Add detailed docstrings and comments
4. Provide usage examples
5. Test with the actual MCP server

## 📞 Support

For issues with the client templates:
- Check the MCP server is running and accessible
- Verify environment variables are set correctly
- Review the logs for connection errors
- Test with the example scripts first 