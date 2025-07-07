"""
Pure MCP (Model Context Protocol) Server for Slack Message Search
Implements the MCP JSON-RPC 2.0 protocol over stdio
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from lib.config import config


@dataclass
class SearchResult:
    """Represents a search result from Slack messages"""
    message_id: str
    text: str
    user_name: str
    channel_name: str
    timestamp: str
    similarity_score: float
    metadata: Dict[str, Any]


class MCPJsonRpcError(Exception):
    """MCP JSON-RPC error"""
    def __init__(self, code: int, message: str, data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC Error {code}: {message}")


class PureMCPServer:
    """Pure MCP Server implementation using JSON-RPC 2.0 over stdio"""
    
    def __init__(self, search_service=None):
        self.search_service = search_service
        self.logger = logging.getLogger(__name__)
        self.initialized = False
        self.server_info = {
            "name": config.mcp_server_name,
            "version": config.mcp_server_version
        }
        
    async def run(self):
        """Run the MCP server over stdio"""
        self.logger.info(f"Starting MCP server {self.server_info['name']} v{self.server_info['version']}")
        
        # Set up stdio
        stdin = sys.stdin
        stdout = sys.stdout
        
        while True:
            try:
                # Read JSON-RPC request from stdin
                line = stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    response = self._create_error_response(
                        None, -32700, "Parse error", {"details": str(e)}
                    )
                    self._send_response(response, stdout)
                    continue
                
                # Handle the request
                response = await self._handle_request(request)
                if response:
                    self._send_response(response, stdout)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                response = self._create_error_response(
                    None, -32603, "Internal error", {"details": str(e)}
                )
                self._send_response(response, stdout)
    
    def _send_response(self, response: Dict, stdout):
        """Send JSON-RPC response to stdout"""
        json_response = json.dumps(response, separators=(',', ':'))
        stdout.write(json_response + '\n')
        stdout.flush()
    
    async def _handle_request(self, request: Dict) -> Optional[Dict]:
        """Handle a JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        # Validate JSON-RPC format
        if request.get("jsonrpc") != "2.0":
            return self._create_error_response(
                request_id, -32600, "Invalid Request", {"message": "Missing or invalid jsonrpc field"}
            )
        
        if not method:
            return self._create_error_response(
                request_id, -32600, "Invalid Request", {"message": "Missing method field"}
            )
        
        try:
            # Handle different MCP methods
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools(params)
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "ping":
                result = {"message": "pong"}
            else:
                return self._create_error_response(
                    request_id, -32601, "Method not found", {"method": method}
                )
            
            # Create successful response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except MCPJsonRpcError as e:
            return self._create_error_response(request_id, e.code, e.message, e.data)
        except Exception as e:
            self.logger.error(f"Error handling method {method}: {e}")
            return self._create_error_response(
                request_id, -32603, "Internal error", {"details": str(e)}
            )
    
    def _create_error_response(self, request_id: Optional[Union[str, int]], 
                              code: int, message: str, data: Optional[Dict] = None) -> Dict:
        """Create a JSON-RPC error response"""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if data:
            error_response["error"]["data"] = data
            
        return error_response
    
    async def _handle_initialize(self, params: Dict) -> Dict:
        """Handle MCP initialize request"""
        self.logger.info("Handling initialize request")
        
        # Mark as initialized
        self.initialized = True
        
        # Return server capabilities
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.server_info,
            "capabilities": {
                "tools": {}
            }
        }
    
    async def _handle_list_tools(self, params: Dict) -> Dict:
        """Handle MCP tools/list request"""
        if not self.initialized:
            raise MCPJsonRpcError(-32002, "Server not initialized")
        
        tools = [
            {
                "name": "search_slack_messages",
                "description": "Search through Slack messages using semantic search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for finding relevant messages",
                            "minLength": 1,
                            "maxLength": 1000
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (1-50)",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10
                        },
                        "channel_filter": {
                            "type": "string",
                            "description": "Filter results by channel name"
                        },
                        "user_filter": {
                            "type": "string", 
                            "description": "Filter results by user name"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Filter messages from this date (YYYY-MM-DD)",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "Filter messages to this date (YYYY-MM-DD)",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_slack_channels",
                "description": "Get list of available Slack channels",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_search_stats",
                "description": "Get statistics about the indexed Slack messages",
                "inputSchema": {
                    "type": "object", 
                    "properties": {}
                }
            }
        ]
        
        return {"tools": tools}
    
    async def _handle_call_tool(self, params: Dict) -> Dict:
        """Handle MCP tools/call request"""
        if not self.initialized:
            raise MCPJsonRpcError(-32002, "Server not initialized")
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise MCPJsonRpcError(-32600, "Invalid Request", {"message": "Missing tool name"})
        
        # Route to appropriate handler
        if tool_name == "search_slack_messages":
            result = await self._handle_search(arguments)
        elif tool_name == "get_slack_channels":
            result = await self._handle_get_channels(arguments)
        elif tool_name == "get_search_stats":
            result = await self._handle_get_stats(arguments)
        else:
            raise MCPJsonRpcError(-32601, "Method not found", {"tool": tool_name})
        
        return result
    
    async def _handle_search(self, arguments: Dict) -> Dict:
        """Handle search requests"""
        if not self.search_service:
            raise MCPJsonRpcError(-32603, "Search service not available")
        
        # Extract and validate parameters
        query = arguments.get("query", "")
        if not query.strip():
            raise MCPJsonRpcError(-32602, "Invalid params", {"message": "Search query cannot be empty"})
        
        top_k = arguments.get("top_k", 10)
        channel_filter = arguments.get("channel_filter")
        user_filter = arguments.get("user_filter")
        date_from = arguments.get("date_from")
        date_to = arguments.get("date_to")
        
        try:
            # Perform search
            results = await self.search_service.search(
                query=query,
                top_k=top_k,
                channel_filter=channel_filter,
                user_filter=user_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            # Format results for MCP
            if not results:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"No messages found matching '{query}'"
                        }
                    ]
                }
            
            # Create formatted response
            response_text = f"Found {len(results)} messages matching '{query}':\n\n"
            
            for i, result in enumerate(results, 1):
                response_text += f"**Result {i}:**\n"
                response_text += f"Channel: #{result.channel_name}\n"
                response_text += f"User: @{result.user_name}\n"
                response_text += f"Time: {result.timestamp}\n"
                response_text += f"Relevance: {result.similarity_score:.2f}\n"
                response_text += f"Message: {result.text}\n"
                response_text += "---\n"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response_text
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise MCPJsonRpcError(-32603, "Search failed", {"details": str(e)})
    
    async def _handle_get_channels(self, arguments: Dict) -> Dict:
        """Handle get channels requests"""
        if not self.search_service:
            raise MCPJsonRpcError(-32603, "Search service not available")
        
        try:
            channels = await self.search_service.get_channels()
            
            if not channels:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "No channels found."
                        }
                    ]
                }
            
            response_text = "Available Slack channels:\n\n"
            for channel in channels:
                response_text += f"- #{channel}\n"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response_text
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Get channels failed: {str(e)}")
            raise MCPJsonRpcError(-32603, "Get channels failed", {"details": str(e)})
    
    async def _handle_get_stats(self, arguments: Dict) -> Dict:
        """Handle get stats requests"""
        if not self.search_service:
            raise MCPJsonRpcError(-32603, "Search service not available")
        
        try:
            stats = await self.search_service.get_stats()
            
            response_text = "Search Index Statistics:\n\n"
            response_text += f"Total Messages: {stats.get('total_vectors', 0)}\n"
            response_text += f"Channels Indexed: {stats.get('channels_indexed', 0)}\n"
            response_text += f"Last Updated: {stats.get('last_refresh', 'Never')}\n"
            response_text += f"Index Status: {stats.get('status', 'Unknown')}\n"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response_text
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Get stats failed: {str(e)}")
            raise MCPJsonRpcError(-32603, "Get stats failed", {"details": str(e)})


# Factory function to create and configure the MCP server
def create_mcp_server(search_service=None):
    """Create a pure MCP server"""
    return PureMCPServer(search_service=search_service) 