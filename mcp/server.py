"""
MCP (Model Context Protocol) Server Implementation
- Pure MCP over stdio for local client connections
- New Streamable HTTP standard (March 2025) for remote access
"""

import asyncio
import json
import logging
import sys
import uuid
import secrets
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import hmac

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
            self.logger.error(f"Search error: {str(e)}")
            raise MCPJsonRpcError(-32603, "Search failed", {"details": str(e)})
    
    async def _handle_get_channels(self, arguments: Dict) -> Dict:
        """Handle get channels request"""
        if not self.search_service:
            raise MCPJsonRpcError(-32603, "Search service not available")
        
        try:
            channels = await self.search_service.get_channels()
            
            channel_list = "\n".join([f"#{channel}" for channel in channels])
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Available Slack channels:\n{channel_list}"
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Get channels error: {str(e)}")
            raise MCPJsonRpcError(-32603, "Failed to get channels", {"details": str(e)})
    
    async def _handle_get_stats(self, arguments: Dict) -> Dict:
        """Handle get stats request"""
        if not self.search_service:
            raise MCPJsonRpcError(-32603, "Search service not available")
        
        try:
            stats = await self.search_service.get_stats()
            
            stats_text = f"""Slack Message Search Statistics:
Total Messages: {stats.get('total_vectors', 0)}
Channels Indexed: {stats.get('channels_indexed', 0)}
Last Refresh: {stats.get('last_refresh', 'Unknown')}
Index Status: {stats.get('status', 'Unknown')}
"""
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": stats_text
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Get stats error: {str(e)}")
            raise MCPJsonRpcError(-32603, "Failed to get stats", {"details": str(e)})


@dataclass
class MCPSession:
    """Represents an MCP session with Streamable HTTP standard"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    scopes: List[str]
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    mcp_server: Optional[PureMCPServer] = None


class MCPStreamableHTTPServer:
    """
    MCP Streamable HTTP Server Implementation (March 2025 Standard)
    
    Features:
    - Single endpoint supporting both GET and POST
    - Session management via headers (mcp-session-id)
    - JSON-RPC protocol compliance
    - Bidirectional communication
    - Authentication support (OAuth, API keys)
    """
    
    def __init__(self, search_service=None):
        self.search_service = search_service
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, MCPSession] = {}
        self.api_keys: Dict[str, Dict] = {}
        self.oauth_tokens: Dict[str, Dict] = {}
        
        # Server configuration
        self.server_config = {
            "name": config.mcp_server_name,
            "version": config.mcp_server_version,
            "protocol": "MCP Streamable HTTP",
            "standard_version": "2025-03"
        }
        
        # Initialize API key system with whitelisting
        self._initialize_api_keys()
    
    def _initialize_api_keys(self):
        """Initialize API key system with secure whitelisting"""
        import os
        import secrets
        import hashlib
        
        # Load whitelisted API keys from environment
        self._load_whitelisted_keys()
        
        # Generate deployment-specific key if none provided
        if not self.api_keys:
            self._generate_deployment_key()
    
    def _load_whitelisted_keys(self):
        """Load pre-approved API keys from environment variables"""
        import os
        
        # Check for user-provided API key (secure method)
        user_key = os.getenv("MCP_API_KEY")
        if user_key and user_key.startswith("mcp_key_"):
            self._whitelist_api_key(user_key, "User Provided Key")
            self.logger.info("Whitelisted user-provided API key")
        
        # Check for multiple keys (comma-separated)
        whitelist_keys = os.getenv("MCP_WHITELIST_KEYS", "")
        if whitelist_keys:
            for key in whitelist_keys.split(","):
                key = key.strip()
                if key and key.startswith("mcp_key_"):
                    self._whitelist_api_key(key, "Whitelisted Key")
            self.logger.info(f"Loaded {len(whitelist_keys.split(','))} whitelisted keys")
    
    def _whitelist_api_key(self, api_key: str, name: str = "Whitelisted Key"):
        """Add an API key to the whitelist"""
        self.api_keys[api_key] = {
            "name": name,
            "scopes": ["mcp:search", "mcp:channels", "mcp:stats"],
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=365),
            "whitelisted": True
        }
        
        # Log securely (only first 16 chars)
        self.logger.info(f"Whitelisted API key: {api_key[:16]}...")
    
    def _generate_deployment_key(self):
        """Generate a secure deployment-specific API key as fallback"""
        import os
        import secrets
        import hashlib
        
        # Generate cryptographically secure key
        # Use 32 bytes (256 bits) of entropy
        random_bytes = secrets.token_bytes(32)
        # Create a deterministic but secure key for this deployment
        deployment_seed = f"slack_chatter_mcp_{os.getenv('REPL_ID', 'local')}"
        combined_entropy = hashlib.sha256(deployment_seed.encode() + random_bytes).hexdigest()
        api_key = f"mcp_key_{combined_entropy[:48]}"  # 48 hex chars = 192 bits
        
        self.api_keys[api_key] = {
            "name": "Auto-Generated Deployment Key",
            "scopes": ["mcp:search", "mcp:channels", "mcp:stats"],
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=365),
            "auto_generated": True
        }
        
        self.logger.info(f"Generated secure deployment key: {api_key[:16]}...")
        return api_key
    
    def _create_session(self, user_id: str, scopes: List[str], 
                       api_key: Optional[str] = None, 
                       oauth_token: Optional[str] = None) -> MCPSession:
        """Create a new MCP session"""
        session_id = f"mcp_session_{secrets.token_urlsafe(16)}"
        
        session = MCPSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            scopes=scopes,
            api_key=api_key,
            oauth_token=oauth_token,
            mcp_server=PureMCPServer(search_service=self.search_service)
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"Created session {session_id} for user {user_id}")
        
        return session
    
    def _validate_session(self, session_id: str) -> MCPSession:
        """Validate and return session"""
        if not session_id:
            raise ValueError("Missing session ID")
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session ID")
        
        if datetime.utcnow() > session.expires_at:
            # Clean up expired session
            del self.sessions[session_id]
            raise ValueError("Session expired")
        
        return session
    
    def _authenticate_request(self, headers: Dict[str, str]) -> MCPSession:
        """Authenticate request and return session"""
        # Check for existing session (MCP 2.0 compliant header)
        session_id = headers.get("Mcp-Session-Id")
        if session_id:
            try:
                return self._validate_session(session_id)
            except ValueError:
                pass  # Continue to other auth methods
        
        # Check for API key authentication
        auth_header = headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
            
            if api_key.startswith("mcp_key_"):
                # API key authentication
                key_info = self.api_keys.get(api_key)
                if key_info and datetime.utcnow() < key_info["expires_at"]:
                    # Create session for API key
                    return self._create_session(
                        user_id=f"api_key_user_{secrets.token_urlsafe(8)}",
                        scopes=key_info["scopes"],
                        api_key=api_key
                    )
            
            elif api_key.startswith("oauth_"):
                # OAuth token authentication
                token_info = self.oauth_tokens.get(api_key)
                if token_info and datetime.utcnow() < token_info["expires_at"]:
                    # Create session for OAuth token
                    return self._create_session(
                        user_id=token_info["user_id"],
                        scopes=token_info["scopes"],
                        oauth_token=api_key
                    )
        
        # No valid authentication found
        raise ValueError("Authentication required")
    
    async def handle_mcp_request(self, method: str, headers: Dict[str, str], 
                               body: Optional[str] = None, 
                               query_params: Optional[Dict] = None) -> Dict:
        """
        Handle MCP request via Streamable HTTP
        
        Args:
            method: HTTP method (GET or POST)
            headers: Request headers
            body: Request body (for POST)
            query_params: Query parameters (for GET)
        
        Returns:
            JSON-RPC response
        """
        try:
            # Authenticate request
            session = self._authenticate_request(headers)
            
            # Parse JSON-RPC request data (MCP 2.0 only accepts POST)
            if method != "POST":
                raise ValueError("MCP 2.0 specification requires HTTP POST")
            
            if not body:
                raise ValueError("JSON-RPC request body required")
            
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in request body")
            
            # Validate JSON-RPC 2.0 format
            if request_data.get("jsonrpc") != "2.0":
                raise ValueError("JSON-RPC 2.0 format required")
            
            if "method" not in request_data:
                raise ValueError("JSON-RPC method required")
            
            # Validate scopes for the request
            self._validate_request_scopes(request_data, session.scopes)
            
            # Process the request through the MCP server
            response = await session.mcp_server._handle_request(request_data)
            
            # Add session information to response
            if response and "result" in response:
                response["session_info"] = {
                    "session_id": session.session_id,
                    "expires_at": session.expires_at.isoformat()
                }
            
            return response
            
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32001,
                    "message": "Authentication failed",
                    "data": {"details": str(e)}
                }
            }
        except Exception as e:
            self.logger.error(f"MCP request error: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)}
                }
            }
    
    def _validate_request_scopes(self, request_data: Dict, session_scopes: List[str]):
        """Validate that the session has required scopes for the request"""
        method = request_data.get("method")
        
        if method == "tools/call":
            tool_name = request_data.get("params", {}).get("name")
            
            if tool_name == "search_slack_messages" and "mcp:search" not in session_scopes:
                raise ValueError("Insufficient scope: mcp:search required")
            elif tool_name == "get_slack_channels" and "mcp:channels" not in session_scopes:
                raise ValueError("Insufficient scope: mcp:channels required")
            elif tool_name == "get_search_stats" and "mcp:stats" not in session_scopes:
                raise ValueError("Insufficient scope: mcp:stats required")
    
    def get_server_info(self) -> Dict:
        """Get server information"""
        return {
            **self.server_config,
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
                "session": "/session"
            },
            "authentication": {
                "methods": ["api_key", "oauth_token"],
                "scopes": ["mcp:search", "mcp:channels", "mcp:stats"]
            },
            "active_sessions": len(self.sessions)
        }
    
    def get_session_info(self, session_id: str) -> Dict:
        """Get information about a specific session"""
        try:
            session = self._validate_session(session_id)
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "scopes": session.scopes,
                "authentication_method": "api_key" if session.api_key else "oauth_token"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if now > session.expires_at
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            self.logger.info(f"Cleaned up expired session {session_id}")
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Factory functions
def create_mcp_server(search_service=None):
    """Create a pure MCP server for stdio communication"""
    return PureMCPServer(search_service=search_service)


def create_mcp_streamable_server(search_service=None):
    """Create an MCP Streamable HTTP server (March 2025 Standard)"""
    return MCPStreamableHTTPServer(search_service=search_service)


# Legacy alias for backward compatibility during transition
def create_mcp_remote_server(search_service=None):
    """Create an MCP remote server (legacy alias)"""
    return create_mcp_streamable_server(search_service=search_service) 