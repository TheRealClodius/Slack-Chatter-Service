#!/usr/bin/env python3
"""
Slack Chatter MCP 2.0 Compliant Server
Pure JSON-RPC 2.0 implementation following MCP 2025-06-18 specification
Provides semantic search capabilities for Slack messages via official MCP protocol
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.service import SearchService
from mcp.llm_search_agent import LLMSearchAgent
from lib.config import config

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# Security
security = HTTPBearer()

# Load API keys from environment
def load_api_keys() -> Dict[str, str]:
    """Load API keys from environment variables or generate default"""
    api_keys = {}
    
    # Try environment first
    env_key = os.getenv("MCP_API_KEY")
    if env_key:
        api_keys[env_key] = {"name": "env_key", "created": datetime.now().isoformat()}
        logger.info(f"Using environment API key: {env_key[:8]}...")
        return api_keys
    
    # Generate default key if none found
    import secrets
    default_key = f"mcp_key_{secrets.token_urlsafe(32)}"
    api_keys[default_key] = {"name": "default", "created": datetime.now().isoformat()}
    logger.info(f"Generated default API key: {default_key}")
    
    return api_keys

api_keys = load_api_keys()

# MCP 2.0 JSON-RPC Models (Following 2025-06-18 specification)
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

# MCP 2.0 Protocol Constants
JSONRPC_VERSION = "2.0"
PROTOCOL_VERSION = "2025-06-18"

# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Global services
search_service: Optional[SearchService] = None
search_agent: Optional[LLMSearchAgent] = None

def set_services(search_svc: SearchService, agent: LLMSearchAgent):
    """Set the search service and agent instances"""
    global search_service, search_agent
    search_service = search_svc
    search_agent = agent

# Authentication
async def verify_api_key(request: Request) -> str:
    """Verify API key from Authorization header"""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Handle Bearer token format
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = auth_header
    
    if token not in api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token

# MCP 2.0 Tool Handlers
async def handle_search_slack_messages(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle search_slack_messages tool call"""
    try:
        if not search_service:
            raise Exception("Search service not initialized")
        
        # Extract parameters from MCP 2.0 arguments
        arguments = params.get("arguments", {})
        
        query = arguments.get("query")
        top_k = arguments.get("top_k", 10)
        channel_filter = arguments.get("channel_filter")
        user_filter = arguments.get("user_filter")
        date_from = arguments.get("date_from")
        date_to = arguments.get("date_to")
        
        if not query:
            return {
                "error": {
                    "code": INVALID_PARAMS,
                    "message": "Parameter 'query' is required"
                }
            }
        
        logger.info(f"Searching Slack messages for: '{query[:50]}...'")
        
        # Build filter parameters
        filter_params = {}
        if channel_filter:
            filter_params["channel"] = channel_filter
        if user_filter:
            filter_params["user"] = user_filter
        if date_from:
            filter_params["date_from"] = date_from
        if date_to:
            filter_params["date_to"] = date_to
        
        # Perform search using enhanced search service
        if search_agent:
            # Use AI-enhanced search
            results = await search_agent.search(query, top_k=top_k, **filter_params)
        else:
            # Use basic search
            results = await search_service.search(query, top_k=top_k, **filter_params)
        
        # Format results according to MCP 2.0 spec
        formatted_results = []
        for result in results.get("results", []):
            formatted_results.append({
                "message_id": result.get("message_id"),
                "text": result.get("text"),
                "user_name": result.get("user_name"),
                "channel_name": result.get("channel_name"),
                "timestamp": result.get("timestamp"),
                "similarity_score": result.get("similarity_score", 0.0),
                "metadata": result.get("metadata", {})
            })
        
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "total_results": len(formatted_results),
                    "results": formatted_results,
                    "search_metadata": {
                        "top_k": top_k,
                        "filters_applied": filter_params,
                        "ai_enhanced": search_agent is not None
                    }
                }, indent=2)
            }],
            "isError": False
        }
        
    except Exception as e:
        logger.error(f"Error in search_slack_messages: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Error searching Slack messages: {str(e)}"
            }],
            "isError": True
        }

async def handle_get_slack_channels(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_slack_channels tool call"""
    try:
        if not search_service:
            raise Exception("Search service not initialized")
        
        logger.info("Getting Slack channels")
        
        # Get channels from search service
        channels = await search_service.get_channels()
        
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "channels": channels
                }, indent=2)
            }],
            "isError": False
        }
        
    except Exception as e:
        logger.error(f"Error in get_slack_channels: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Error getting Slack channels: {str(e)}"
            }],
            "isError": True
        }

async def handle_get_search_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_search_stats tool call"""
    try:
        if not search_service:
            raise Exception("Search service not initialized")
        
        logger.info("Getting search statistics")
        
        # Get stats from search service
        stats = await search_service.get_stats()
        
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "stats": stats
                }, indent=2)
            }],
            "isError": False
        }
        
    except Exception as e:
        logger.error(f"Error in get_search_stats: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Error getting search statistics: {str(e)}"
            }],
            "isError": True
        }

# MCP 2.0 Tool Registry (Following 2025-06-18 specification)
MCP_TOOLS = {
    "search_slack_messages": {
        "name": "search_slack_messages",
        "description": "Search for Slack messages using semantic similarity with AI-enhanced query processing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "Natural language search query",
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
        },
        "handler": handle_search_slack_messages
    },
    "get_slack_channels": {
        "name": "get_slack_channels",
        "description": "Get list of available Slack channels",
        "inputSchema": {
            "type": "object",
            "properties": {}
        },
        "handler": handle_get_slack_channels
    },
    "get_search_stats": {
        "name": "get_search_stats",
        "description": "Get statistics about the indexed Slack messages",
        "inputSchema": {
            "type": "object",
            "properties": {}
        },
        "handler": handle_get_search_stats
    }
}

# MCP 2.0 Protocol Handlers
async def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP 2.0 initialize request"""
    protocol_version = params.get("protocolVersion", PROTOCOL_VERSION)
    client_info = params.get("clientInfo", {})
    capabilities = params.get("capabilities", {})
    
    logger.info(f"MCP client connecting: {client_info.get('name', 'Unknown')} v{client_info.get('version', 'Unknown')}")
    logger.info(f"Protocol version: {protocol_version}")
    
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {
            "name": config.mcp_server_name,
            "version": config.mcp_server_version,
            "title": "Slack Chatter Search"
        },
        "capabilities": {
            "tools": {
                "listChanged": False
            },
            "logging": {}
        },
        "instructions": "This server provides semantic search capabilities for Slack messages. Use 'search_slack_messages' to find relevant conversations, 'get_slack_channels' to list available channels, and 'get_search_stats' to view indexing statistics."
    }

async def handle_tools_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/list request"""
    tools = []
    for tool_name, tool_config in MCP_TOOLS.items():
        tools.append({
            "name": tool_config["name"],
            "description": tool_config["description"],
            "inputSchema": tool_config["inputSchema"]
        })
    
    return {"tools": tools}

async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/call request"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name not in MCP_TOOLS:
        raise Exception(f"Unknown tool: {tool_name}")
    
    tool_config = MCP_TOOLS[tool_name]
    handler = tool_config["handler"]
    
    # Call the tool handler with proper parameters
    return await handler({"arguments": arguments})

async def handle_ping(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ping request"""
    return {}

# Main MCP 2.0 Protocol Handler
async def handle_mcp_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main MCP 2.0 JSON-RPC request handler"""
    try:
        # Validate JSON-RPC structure
        if request_data.get("jsonrpc") != JSONRPC_VERSION:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_data.get("id"),
                "error": {
                    "code": INVALID_REQUEST,
                    "message": "Invalid JSON-RPC version"
                }
            }
        
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        # Route to appropriate handler
        if method == "initialize":
            result = await handle_initialize(params)
        elif method == "tools/list":
            result = await handle_tools_list(params)
        elif method == "tools/call":
            result = await handle_tools_call(params)
        elif method == "ping":
            result = await handle_ping(params)
        else:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": METHOD_NOT_FOUND,
                    "message": f"Method not found: {method}"
                }
            }
        
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_data.get("id"),
            "error": {
                "code": INTERNAL_ERROR,
                "message": str(e)
            }
        }

# FastAPI Application
app = FastAPI(
    title="Slack Chatter MCP 2.0 Server",
    description="MCP 2025-06-18 compliant server for Slack message search",
    version=config.mcp_server_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "protocol": "MCP 2025-06-18",
        "server": {
            "name": config.mcp_server_name,
            "version": config.mcp_server_version
        },
        "services": {
            "search_service": search_service is not None,
            "ai_agent": search_agent is not None
        }
    }

@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Main MCP 2.0 JSON-RPC endpoint"""
    try:
        # Parse JSON-RPC request
        body = await request.body()
        request_data = json.loads(body.decode())
        
        # Handle the MCP request
        response = await handle_mcp_request(request_data)
        
        return JSONResponse(content=response)
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {
                    "code": PARSE_ERROR,
                    "message": "Parse error"
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {
                    "code": INTERNAL_ERROR,
                    "message": "Internal error"
                }
            }
        )

@app.get("/mcp/tools")
async def list_tools(api_key: str = Depends(verify_api_key)):
    """List available MCP tools (convenience endpoint)"""
    tools = []
    for tool_name, tool_config in MCP_TOOLS.items():
        tools.append({
            "name": tool_config["name"],
            "description": tool_config["description"],
            "inputSchema": tool_config["inputSchema"]
        })
    return {"tools": tools}

def create_mcp_2_0_app(search_svc: SearchService, agent: LLMSearchAgent = None) -> FastAPI:
    """Create and configure the MCP 2.0 compliant FastAPI application"""
    set_services(search_svc, agent)
    return app

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)