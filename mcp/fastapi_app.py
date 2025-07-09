"""
FastAPI application for MCP Streamable HTTP Standard (March 2025)
Implements single endpoint with session headers and simplified authentication
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, Request, Response, HTTPException, Header, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import secrets

from mcp.server import MCPStreamableHTTPServer, create_mcp_streamable_server


app = FastAPI(
    title="MCP Streamable HTTP Server",
    description="MCP Streamable HTTP Standard (March 2025) - Single endpoint with session headers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Global MCP streamable server instance
mcp_streamable_server: Optional[MCPStreamableHTTPServer] = None
_search_service = None


def set_search_service(search_service):
    """Set the search service for the MCP server"""
    global _search_service
    _search_service = search_service


@app.on_event("startup")
async def startup_event():
    """Initialize the MCP streamable server on startup"""
    global mcp_streamable_server
    
    # Create MCP streamable server with the configured search service
    mcp_streamable_server = create_mcp_streamable_server(search_service=_search_service)
    
    logging.info("MCP Streamable HTTP Server (March 2025 Standard) started")


@app.get("/")
async def root():
    """Root endpoint with information about the MCP server"""
    return {
        "message": "MCP Streamable HTTP Server",
        "version": "2.0.0",
        "standard": "MCP Streamable HTTP (March 2025)",
        "features": [
            "MCP 2.0 specification compliant (2025-03-26)",
            "HTTP POST only with JSON-RPC 2.0 body",
            "Session management via Mcp-Session-Id headers",
            "Standard initialize, tools/list, tools/call methods",
            "Authentication support (API keys, OAuth tokens)"
        ],
        "endpoints": {
            "mcp": "/mcp (POST only - MCP 2.0 compliant)",
            "health": "/health",
            "session": "/session/{session_id}",
            "docs": "/docs"
        },
        "authentication": {
            "header": "Authorization: Bearer {api_key_or_oauth_token}",
            "session_header": "Mcp-Session-Id: {session_id}",
            "api_key_format": "mcp_key_...",
            "oauth_token_format": "oauth_...",
            "specification": "MCP 2.0 (2025-03-26)"
        }
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    logging.info(f"Incoming request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    logging.info(f"All headers: {dict(request.headers)}")
    response = await call_next(request)
    logging.info(f"Response status: {response.status_code}")
    return response

@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
    authorization: Optional[str] = Header(None)
):
    """
    MCP 2.0 compliant endpoint (2025-03-26 specification)
    
    Only accepts HTTP POST with JSON-RPC 2.0 body
    
    Headers:
    - Mcp-Session-Id: Session identifier for authenticated sessions
    - Authorization: Bearer token for authentication (API key or OAuth token)
    """
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        # Log all incoming headers for debugging
        all_headers = dict(request.headers)
        logging.debug(f"Incoming request headers: {all_headers}")
        
        # Prepare headers dict
        headers = {}
        if mcp_session_id:
            headers["Mcp-Session-Id"] = mcp_session_id
            logging.debug(f"Session ID found: {mcp_session_id}")
        if authorization:
            headers["Authorization"] = authorization
            logging.debug(f"Authorization header found: {authorization[:20]}...")
        else:
            logging.warning("No authorization header found in request")
            # Check if authorization is in the raw headers with different case
            for header_name, header_value in all_headers.items():
                if header_name.lower() == "authorization":
                    headers["Authorization"] = header_value
                    logging.info(f"Found authorization header with different case: {header_name}")
                    break
        
        # Only accept POST requests for MCP 2.0 compliance
        if request.method != "POST":
            raise HTTPException(
                status_code=405, 
                detail="MCP 2.0 specification requires HTTP POST with JSON-RPC body"
            )
        
        # Parse JSON-RPC from body
        body = await request.body()
        if not body:
            raise HTTPException(
                status_code=400,
                detail="Request body required for JSON-RPC 2.0"
            )
        
        body_str = body.decode('utf-8')
        
        # Log the complete request for debugging
        logging.info(f"Processing MCP request from {request.client.host if request.client else 'unknown'}")
        logging.info(f"Request headers prepared: {headers}")
        logging.info(f"Request body preview: {body_str[:100]}...")
        
        response = await mcp_streamable_server.handle_mcp_request(
            method="POST",
            headers=headers,
            body=body_str,
            query_params=None
        )
        
        # Add session header to response if session was created/updated
        if response and "session_info" in response:
            session_id = response["session_info"]["session_id"]
            return JSONResponse(
                content=response,
                headers={"Mcp-Session-Id": session_id}
            )
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        logging.error(f"MCP endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    session_info = mcp_streamable_server.get_session_info(session_id)
    
    if "error" in session_info:
        raise HTTPException(status_code=404, detail=session_info["error"])
    
    return session_info


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not mcp_streamable_server:
        return {"status": "unhealthy", "error": "Server not initialized"}
    
    server_info = mcp_streamable_server.get_server_info()
    
    return {
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z",  # Would be actual timestamp
        **server_info
    }


@app.get("/info")
async def server_info():
    """Get detailed server information"""
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    return mcp_streamable_server.get_server_info()


@app.get("/cleanup")
async def cleanup_sessions():
    """Cleanup expired sessions (admin endpoint)"""
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    mcp_streamable_server.cleanup_expired_sessions()
    
    return {"message": "Expired sessions cleaned up"}


@app.get("/dev/api-key")
async def get_current_api_key():
    """Get current deployment API key (development only)"""
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Get the first API key (auto-generated deployment key)
    api_keys = mcp_streamable_server.api_keys
    if not api_keys:
        raise HTTPException(status_code=404, detail="No API keys found")
    
    # Return the first key (usually the auto-generated one)
    current_key = list(api_keys.keys())[0]
    key_info = api_keys[current_key]
    
    return {
        "api_key": current_key,
        "name": key_info.get("name", "Unknown"),
        "created_at": key_info.get("created_at", "Unknown"),
        "expires_at": key_info.get("expires_at", "Unknown"),
        "scopes": key_info.get("scopes", []),
        "note": "Use this key for authentication with the MCP server"
    }


@app.get("/docs-example")
async def api_docs_example():
    """Example API usage documentation"""
    examples = {
        "authentication": {
            "api_key": {
                "description": "Use API key for authentication",
                "example": {
                    "curl": 'curl -X POST https://your-deployment.com/mcp -H "Authorization: Bearer mcp_key_..." -H "Content-Type: application/json" -d \'{"jsonrpc": "2.0", "method": "tools/list", "id": 1}\'',
                    "headers": {
                        "Authorization": "Bearer mcp_key_abcdef123456...",
                        "Content-Type": "application/json"
                    }
                }
            },
            "session": {
                "description": "Use session ID for subsequent requests",
                "example": {
                    "curl": 'curl -X GET "https://your-deployment.com/mcp?method=tools/list" -H "mcp-session-id: mcp_session_abc123"',
                    "headers": {
                        "mcp-session-id": "mcp_session_abc123"
                    }
                }
            }
        },
        "requests": {
            "post_search": {
                "description": "POST request to search messages",
                "method": "POST",
                "url": "/mcp",
                "headers": {
                    "Authorization": "Bearer mcp_key_...",
                    "Content-Type": "application/json"
                },
                "body": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "search_slack_messages",
                        "arguments": {
                            "query": "deployment issues",
                            "top_k": 5
                        }
                    },
                    "id": 1
                }
            },
            "get_tools": {
                "description": "GET request to list available tools",
                "method": "GET",
                "url": "/mcp?method=tools/list",
                "headers": {
                    "Authorization": "Bearer mcp_key_..."
                }
            },
            "get_search": {
                "description": "GET request to search (simplified)",
                "method": "GET",
                "url": "/mcp?method=tools/call&name=search_slack_messages&query=deployment&top_k=3",
                "headers": {
                    "Authorization": "Bearer mcp_key_..."
                }
            }
        },
        "responses": {
            "success": {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Found 3 messages matching 'deployment'..."
                        }
                    ]
                },
                "session_info": {
                    "session_id": "mcp_session_abc123",
                    "expires_at": "2025-01-02T00:00:00Z"
                }
            },
            "error": {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32001,
                    "message": "Authentication failed",
                    "data": {
                        "details": "Invalid API key"
                    }
                }
            }
        }
    }
    
    return examples


# Development helper endpoint
@app.get("/dev/api-key")
async def get_development_api_key():
    """Get development API key (remove in production)"""
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Get the first API key (development key)
    api_keys = list(mcp_streamable_server.api_keys.keys())
    if api_keys:
        return {
            "api_key": api_keys[0],
            "note": "This is for development only. Remove this endpoint in production.",
            "usage": f"Authorization: Bearer {api_keys[0]}"
        }
    
    return {"error": "No API keys available"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 