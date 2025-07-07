"""
FastAPI application for Official MCP Remote Protocol
Implements OAuth 2.1 authentication and SSE communication
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query, Form
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette import EventSourceResponse
import secrets
import base64
import hashlib

from mcp.server import MCPRemoteServer, create_mcp_remote_server


app = FastAPI(
    title="MCP Remote Protocol Server",
    description="Official MCP Remote Protocol with OAuth 2.1 and SSE",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP remote server instance
mcp_remote_server: Optional[MCPRemoteServer] = None
security = HTTPBearer()

def get_authorization_header(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate authorization header"""
    return f"Bearer {credentials.credentials}"


# Global variable to store the search service
_search_service = None

def set_search_service(search_service):
    """Set the search service for the MCP remote server"""
    global _search_service
    _search_service = search_service

@app.on_event("startup")
async def startup_event():
    """Initialize the MCP remote server on startup"""
    global mcp_remote_server
    
    # Create MCP remote server with the configured search service
    mcp_remote_server = create_mcp_remote_server(search_service=_search_service)
    
    logging.info("MCP Remote Protocol Server started")


@app.get("/")
async def root():
    """Root endpoint with information about the MCP server"""
    return {
        "message": "MCP Remote Protocol Server",
        "version": "1.0.0",
        "protocol": "MCP Remote with OAuth 2.1 and SSE",
        "endpoints": {
            "oauth_discovery": "/.well-known/oauth-authorization-server",
            "authorization": "/oauth/authorize",
            "token": "/oauth/token",
            "mcp_sse": "/mcp/sse",
            "mcp_request": "/mcp/request",
            "session_info": "/mcp/session"
        }
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_discovery():
    """OAuth 2.1 discovery endpoint"""
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    return mcp_remote_server.get_oauth_discovery()


@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str = Query(..., description="Must be 'code'"),
    client_id: str = Query(..., description="OAuth client ID"),
    redirect_uri: str = Query(..., description="Redirect URI"),
    scope: str = Query(..., description="Space-separated scopes"),
    state: str = Query(..., description="State parameter"),
    code_challenge: str = Query(..., description="PKCE code challenge"),
    code_challenge_method: str = Query(..., description="PKCE challenge method")
):
    """
    OAuth 2.1 authorization endpoint
    For development/testing, this returns the authorization code directly
    In production, this would show a user consent screen
    """
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Validate response type
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid response_type")
    
    try:
        # Parse scopes
        scopes = scope.split()
        
        # Start authorization flow
        auth_result = await mcp_remote_server.start_authorization(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        
        # For testing, return the authorization code directly
        # In production, this would redirect to a consent screen
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Authorization</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .code-box {{ background: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace; }}
                .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>MCP Authorization</h1>
                <p>Authorization requested for client: <strong>{client_id}</strong></p>
                <p>Scopes: <strong>{', '.join(scopes)}</strong></p>
                <p>Your authorization code (for testing):</p>
                <div class="code-box">{auth_result['code']}</div>
                <p>In production, you would be redirected to: <code>{redirect_uri}</code></p>
                <button class="btn" onclick="copyToClipboard()">Copy Code</button>
            </div>
            <script>
                function copyToClipboard() {{
                    navigator.clipboard.writeText('{auth_result['code']}');
                    alert('Authorization code copied to clipboard!');
                }}
            </script>
        </body>
        </html>
        """)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(..., description="Must be 'authorization_code'"),
    code: str = Form(..., description="Authorization code"),
    redirect_uri: str = Form(..., description="Redirect URI"),
    client_id: str = Form(..., description="OAuth client ID"),
    client_secret: str = Form(..., description="OAuth client secret"),
    code_verifier: str = Form(..., description="PKCE code verifier")
):
    """OAuth 2.1 token endpoint"""
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Validate grant type
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Invalid grant_type")
    
    try:
        # Exchange code for token
        token_result = await mcp_remote_server.exchange_code_for_token(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )
        
        return token_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mcp/sse")
async def mcp_sse_endpoint(authorization: str = Depends(get_authorization_header)):
    """
    MCP communication over Server-Sent Events
    Handles real-time bidirectional communication
    """
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    async def event_generator():
        """Generate SSE events for MCP communication"""
        try:
            async for event in mcp_remote_server.handle_mcp_sse(authorization):
                yield event
        except Exception as e:
            logging.error(f"SSE error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return EventSourceResponse(event_generator())


@app.post("/mcp/request")
async def mcp_request_endpoint(
    request: Request,
    authorization: str = Depends(get_authorization_header)
):
    """
    Direct MCP JSON-RPC request endpoint
    Alternative to SSE for single request/response
    """
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        # Parse request body
        request_data = await request.json()
        
        # Handle the MCP request
        response = await mcp_remote_server.handle_mcp_request(authorization, request_data)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logging.error(f"MCP request error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp/session")
async def mcp_session_info(authorization: str = Depends(get_authorization_header)):
    """Get information about the current MCP session"""
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    session_info = mcp_remote_server.get_session_info(authorization)
    
    if "error" in session_info:
        raise HTTPException(status_code=401, detail=session_info["error"])
    
    return session_info


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not mcp_remote_server:
        return {"status": "unhealthy", "error": "Server not initialized"}
    
    return {
        "status": "healthy",
        "server": "MCP Remote Protocol Server",
        "version": "1.0.0",
        "oauth_clients": len(mcp_remote_server.oauth_clients),
        "active_sessions": len(mcp_remote_server.sessions)
    }


@app.get("/debug/oauth-clients")
async def debug_oauth_clients():
    """Debug endpoint to view OAuth clients (development only)"""
    if not mcp_remote_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Return client info without secrets
    clients = {}
    for client_id, client_data in mcp_remote_server.oauth_clients.items():
        clients[client_id] = {
            "name": client_data["name"],
            "redirect_uris": client_data["redirect_uris"],
            "scopes": client_data["scopes"]
        }
    
    return {"clients": clients}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the server
    uvicorn.run(
        "mcp.fastapi_app:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    ) 