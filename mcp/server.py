"""
MCP (Model Context Protocol) Server Implementation
- Pure MCP over stdio for local client connections
- Official MCP Remote Protocol with OAuth 2.1 and SSE for remote access
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
import base64
import hashlib

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


@dataclass
class MCPSession:
    """Represents an authenticated MCP session"""
    session_id: str
    user_id: str
    access_token: str
    expires_at: datetime
    scopes: List[str]
    mcp_server: PureMCPServer


class MCPRemoteServer:
    """
    Official MCP Remote Protocol Implementation
    Uses OAuth 2.1 for authentication and SSE for communication
    """
    
    def __init__(self, search_service=None):
        self.search_service = search_service
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, MCPSession] = {}
        self.oauth_clients: Dict[str, Dict] = {}
        self.authorization_codes: Dict[str, Dict] = {}
        
        # OAuth 2.1 Configuration
        self.oauth_config = {
            "authorization_endpoint": "/oauth/authorize",
            "token_endpoint": "/oauth/token",
            "scopes_supported": ["mcp:search", "mcp:channels", "mcp:stats"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"]
        }
        
        # Register default OAuth client for testing
        self._register_default_client()
    
    def _register_default_client(self):
        """Register a default OAuth client for development/testing"""
        client_id = "mcp-slack-chatter-client"
        client_secret = secrets.token_urlsafe(32)
        
        self.oauth_clients[client_id] = {
            "client_secret": client_secret,
            "redirect_uris": [
                "http://localhost:3000/callback",
                "https://*.replit.app/callback",
                "urn:ietf:wg:oauth:2.0:oob"  # Out-of-band for CLI clients
            ],
            "scopes": ["mcp:search", "mcp:channels", "mcp:stats"],
            "name": "Slack Chatter MCP Client"
        }
        
        self.logger.info(f"Default OAuth client registered: {client_id}")
        self.logger.info(f"Client secret: {client_secret}")
    
    def _generate_pkce_challenge(self, verifier: str) -> str:
        """Generate PKCE challenge from verifier"""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    async def start_authorization(self, client_id: str, redirect_uri: str, 
                                state: str, scopes: List[str], 
                                code_challenge: str, code_challenge_method: str) -> Dict:
        """Start OAuth 2.1 authorization flow"""
        if client_id not in self.oauth_clients:
            raise ValueError("Invalid client_id")
        
        client = self.oauth_clients[client_id]
        
        # Validate redirect URI
        if redirect_uri not in client["redirect_uris"]:
            raise ValueError("Invalid redirect_uri")
        
        # Validate scopes
        invalid_scopes = set(scopes) - set(client["scopes"])
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")
        
        # Validate PKCE
        if code_challenge_method != "S256":
            raise ValueError("Only S256 code challenge method supported")
        
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        
        self.authorization_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "code_challenge": code_challenge,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "used": False
        }
        
        return {
            "authorization_url": f"/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&scope={'+'.join(scopes)}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}",
            "code": auth_code  # For testing - normally user would authorize via UI
        }
    
    async def exchange_code_for_token(self, client_id: str, client_secret: str,
                                    code: str, redirect_uri: str, 
                                    code_verifier: str) -> Dict:
        """Exchange authorization code for access token"""
        if client_id not in self.oauth_clients:
            raise ValueError("Invalid client_id")
        
        client = self.oauth_clients[client_id]
        if client["client_secret"] != client_secret:
            raise ValueError("Invalid client_secret")
        
        if code not in self.authorization_codes:
            raise ValueError("Invalid authorization code")
        
        auth_data = self.authorization_codes[code]
        
        # Validate code hasn't expired or been used
        if auth_data["used"] or datetime.utcnow() > auth_data["expires_at"]:
            raise ValueError("Authorization code expired or already used")
        
        # Validate PKCE
        expected_challenge = self._generate_pkce_challenge(code_verifier)
        if auth_data["code_challenge"] != expected_challenge:
            raise ValueError("Invalid code_verifier")
        
        # Validate redirect URI
        if auth_data["redirect_uri"] != redirect_uri:
            raise ValueError("Redirect URI mismatch")
        
        # Mark code as used
        auth_data["used"] = True
        
        # Generate access token
        access_token = secrets.token_urlsafe(32)
        user_id = f"user_{secrets.token_urlsafe(8)}"  # Generate unique user ID
        
        # Create session
        session_id = str(uuid.uuid4())
        session = MCPSession(
            session_id=session_id,
            user_id=user_id,
            access_token=access_token,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            scopes=auth_data["scopes"],
            mcp_server=PureMCPServer(search_service=self.search_service)
        )
        
        self.sessions[session_id] = session
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours
            "scope": " ".join(auth_data["scopes"]),
            "session_id": session_id
        }
    
    def _validate_token(self, authorization_header: str) -> MCPSession:
        """Validate Bearer token and return session"""
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise ValueError("Missing or invalid authorization header")
        
        token = authorization_header[7:]  # Remove "Bearer " prefix
        
        # Find session with this token
        for session in self.sessions.values():
            if session.access_token == token:
                if datetime.utcnow() > session.expires_at:
                    raise ValueError("Token expired")
                return session
        
        raise ValueError("Invalid token")
    
    async def handle_mcp_sse(self, authorization_header: str) -> AsyncGenerator[str, None]:
        """Handle MCP communication over Server-Sent Events"""
        try:
            session = self._validate_token(authorization_header)
            
            # Initialize the MCP server for this session
            if not session.mcp_server.initialized:
                init_response = await session.mcp_server._handle_request({
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {},
                    "id": "sse_init"
                })
                
                # Send initialization response
                yield f"data: {json.dumps(init_response)}\n\n"
            
            # Keep connection alive and handle incoming requests
            # In a real implementation, this would handle bidirectional communication
            # For now, we'll send a heartbeat
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
        except ValueError as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication failed",
                    "data": {"details": str(e)}
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
        except Exception as e:
            self.logger.error(f"SSE error: {str(e)}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)}
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    async def handle_mcp_request(self, authorization_header: str, request_data: Dict) -> Dict:
        """Handle MCP JSON-RPC request with authentication"""
        try:
            session = self._validate_token(authorization_header)
            
            # Check if the request requires specific scopes
            method = request_data.get("method")
            if method == "tools/call":
                tool_name = request_data.get("params", {}).get("name")
                if tool_name == "search_slack_messages" and "mcp:search" not in session.scopes:
                    raise ValueError("Insufficient scope for search operation")
                elif tool_name == "get_slack_channels" and "mcp:channels" not in session.scopes:
                    raise ValueError("Insufficient scope for channels operation")
                elif tool_name == "get_search_stats" and "mcp:stats" not in session.scopes:
                    raise ValueError("Insufficient scope for stats operation")
            
            # Process the request through the MCP server
            response = await session.mcp_server._handle_request(request_data)
            return response
            
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
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
                "id": request_data.get("id"),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)}
                }
            }
    
    def get_oauth_discovery(self) -> Dict:
        """Return OAuth 2.1 discovery information"""
        return {
            "issuer": "https://your-mcp-server.replit.app",
            "authorization_endpoint": f"https://your-mcp-server.replit.app{self.oauth_config['authorization_endpoint']}",
            "token_endpoint": f"https://your-mcp-server.replit.app{self.oauth_config['token_endpoint']}",
            "scopes_supported": self.oauth_config["scopes_supported"],
            "response_types_supported": self.oauth_config["response_types_supported"],
            "grant_types_supported": self.oauth_config["grant_types_supported"],
            "code_challenge_methods_supported": self.oauth_config["code_challenge_methods_supported"]
        }
    
    def get_session_info(self, authorization_header: str) -> Dict:
        """Get information about the current session"""
        try:
            session = self._validate_token(authorization_header)
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "scopes": session.scopes,
                "expires_at": session.expires_at.isoformat(),
                "server_info": session.mcp_server.server_info
            }
        except ValueError as e:
            return {"error": str(e)}


# Factory functions
def create_mcp_server(search_service=None):
    """Create a pure MCP server for stdio communication"""
    return PureMCPServer(search_service=search_service)


def create_mcp_remote_server(search_service=None):
    """Create an MCP remote server with OAuth 2.1 and SSE"""
    return MCPRemoteServer(search_service=search_service) 