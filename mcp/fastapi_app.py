"""
FastAPI application for MCP Streamable HTTP Standard (March 2025)
Implements single endpoint with session headers and simplified authentication
"""

import asyncio
import json
import logging
import secrets
import hashlib
import base64
import time
from typing import Dict, List, Optional
from urllib.parse import unquote, urlencode, parse_qs
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException, Header, Query, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

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

# OAuth 2.1 Configuration
OAUTH_CONFIG = {
    "client_id": "mcp-slack-chatter-client",
    "client_secret": "mcp_client_secret_12345",  # In production, use environment variable
    "redirect_uri": "http://localhost:3000/callback",  # Default redirect URI
    "scopes": ["mcp:search", "mcp:channels", "mcp:stats"],
    "authorization_code_expiry": 600,  # 10 minutes
    "access_token_expiry": 86400,  # 24 hours
}

# In-memory storage (use Redis/database in production)
authorization_codes: Dict[str, Dict] = {}
access_tokens: Dict[str, Dict] = {}
refresh_tokens: Dict[str, Dict] = {}


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


# Helper functions for OAuth 2.1
def generate_pkce_challenge():
    """Generate PKCE code verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


def verify_pkce_challenge(code_verifier: str, code_challenge: str):
    """Verify PKCE code challenge"""
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return secrets.compare_digest(expected_challenge, code_challenge)


def generate_token():
    """Generate a secure token"""
    return secrets.token_urlsafe(32)


def is_token_expired(token_data: Dict) -> bool:
    """Check if a token is expired"""
    return datetime.utcnow() > token_data["expires_at"]


# OAuth 2.1 Discovery Endpoint
@app.get("/.well-known/oauth-authorization-server")
async def oauth_discovery():
    """OAuth 2.1 authorization server discovery endpoint"""
    base_url = "http://0.0.0.0:5000"  # In production, use request.base_url
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "scopes_supported": OAUTH_CONFIG["scopes"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "introspection_endpoint": f"{base_url}/oauth/introspect",
        "revocation_endpoint": f"{base_url}/oauth/revoke"
    }


# OAuth 2.1 Authorization Endpoint
@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...)
):
    """OAuth 2.1 authorization endpoint with PKCE"""
    
    # Validate parameters
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")
    
    if client_id != OAUTH_CONFIG["client_id"]:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Unsupported code_challenge_method")
    
    requested_scopes = scope.split(" ")
    invalid_scopes = [s for s in requested_scopes if s not in OAUTH_CONFIG["scopes"]]
    if invalid_scopes:
        raise HTTPException(status_code=400, detail=f"Invalid scopes: {invalid_scopes}")
    
    # Generate authorization code
    auth_code = generate_token()
    authorization_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "expires_at": datetime.utcnow() + timedelta(seconds=OAUTH_CONFIG["authorization_code_expiry"]),
        "used": False
    }
    
    # In a real implementation, you would show a consent page
    # For MCP Remote Protocol, we'll auto-approve
    
    # Redirect with authorization code
    params = {
        "code": auth_code,
        "state": state
    }
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    
    return RedirectResponse(url=redirect_url, status_code=302)


# OAuth 2.1 Token Endpoint
@app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None)
):
    """OAuth 2.1 token endpoint"""
    
    # Validate client credentials
    if client_id != OAUTH_CONFIG["client_id"] or client_secret != OAUTH_CONFIG["client_secret"]:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    if grant_type == "authorization_code":
        # Authorization code flow
        if not code or not code_verifier or not redirect_uri:
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Validate authorization code
        if code not in authorization_codes:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        
        auth_data = authorization_codes[code]
        
        if auth_data["used"]:
            raise HTTPException(status_code=400, detail="Authorization code already used")
        
        if is_token_expired(auth_data):
            del authorization_codes[code]
            raise HTTPException(status_code=400, detail="Authorization code expired")
        
        if auth_data["redirect_uri"] != redirect_uri:
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")
        
        # Verify PKCE
        if not verify_pkce_challenge(code_verifier, auth_data["code_challenge"]):
            raise HTTPException(status_code=400, detail="Invalid code_verifier")
        
        # Mark code as used
        auth_data["used"] = True
        
        # Generate tokens
        access_token = generate_token()
        refresh_token_value = generate_token()
        
        # Store tokens
        token_data = {
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": datetime.utcnow() + timedelta(seconds=OAUTH_CONFIG["access_token_expiry"]),
            "refresh_token": refresh_token_value
        }
        
        access_tokens[access_token] = token_data
        refresh_tokens[refresh_token_value] = {
            "access_token": access_token,
            "client_id": client_id,
            "scope": auth_data["scope"]
        }
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": OAUTH_CONFIG["access_token_expiry"],
            "refresh_token": refresh_token_value,
            "scope": auth_data["scope"]
        }
    
    elif grant_type == "refresh_token":
        # Refresh token flow
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")
        
        if refresh_token not in refresh_tokens:
            raise HTTPException(status_code=400, detail="Invalid refresh_token")
        
        refresh_data = refresh_tokens[refresh_token]
        
        # Revoke old access token
        old_access_token = refresh_data["access_token"]
        if old_access_token in access_tokens:
            del access_tokens[old_access_token]
        
        # Generate new tokens
        new_access_token = generate_token()
        new_refresh_token = generate_token()
        
        # Store new tokens
        token_data = {
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": datetime.utcnow() + timedelta(seconds=OAUTH_CONFIG["access_token_expiry"]),
            "refresh_token": new_refresh_token
        }
        
        access_tokens[new_access_token] = token_data
        refresh_tokens[new_refresh_token] = {
            "access_token": new_access_token,
            "client_id": client_id,
            "scope": refresh_data["scope"]
        }
        
        # Remove old refresh token
        del refresh_tokens[refresh_token]
        
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": OAUTH_CONFIG["access_token_expiry"],
            "refresh_token": new_refresh_token,
            "scope": refresh_data["scope"]
        }
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")


# OAuth 2.1 Token Introspection
@app.post("/oauth/introspect")
async def oauth_introspect(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """OAuth 2.1 token introspection endpoint"""
    
    # Validate client credentials
    if client_id != OAUTH_CONFIG["client_id"] or client_secret != OAUTH_CONFIG["client_secret"]:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    if token in access_tokens:
        token_data = access_tokens[token]
        if not is_token_expired(token_data):
            return {
                "active": True,
                "client_id": token_data["client_id"],
                "scope": token_data["scope"],
                "exp": int(token_data["expires_at"].timestamp())
            }
    
    return {"active": False}


# OAuth 2.1 Token Revocation
@app.post("/oauth/revoke")
async def oauth_revoke(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """OAuth 2.1 token revocation endpoint"""
    
    # Validate client credentials
    if client_id != OAUTH_CONFIG["client_id"] or client_secret != OAUTH_CONFIG["client_secret"]:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    # Revoke access token
    if token in access_tokens:
        token_data = access_tokens[token]
        refresh_token_value = token_data.get("refresh_token")
        
        del access_tokens[token]
        
        # Also revoke associated refresh token
        if refresh_token_value and refresh_token_value in refresh_tokens:
            del refresh_tokens[refresh_token_value]
    
    # Revoke refresh token
    elif token in refresh_tokens:
        refresh_data = refresh_tokens[token]
        access_token = refresh_data["access_token"]
        
        del refresh_tokens[token]
        
        # Also revoke associated access token
        if access_token in access_tokens:
            del access_tokens[access_token]
    
    return {"revoked": True}


# Debug endpoints for development
@app.get("/debug/oauth-client-info")
async def debug_oauth_client_info():
    """Debug endpoint to get OAuth client information"""
    return {
        "client_id": OAUTH_CONFIG["client_id"],
        "client_secret": OAUTH_CONFIG["client_secret"],  # Only for development!
        "scopes": OAUTH_CONFIG["scopes"],
        "redirect_uri": OAUTH_CONFIG["redirect_uri"],
        "endpoints": {
            "discovery": "/.well-known/oauth-authorization-server",
            "authorization": "/oauth/authorize",
            "token": "/oauth/token",
            "introspection": "/oauth/introspect",
            "revocation": "/oauth/revoke"
        },
        "note": "⚠️ This endpoint exposes client secrets and should only be used in development!"
    }


@app.get("/debug/tokens")
async def debug_tokens():
    """Debug endpoint to see active tokens (development only)"""
    return {
        "active_access_tokens": len(access_tokens),
        "active_refresh_tokens": len(refresh_tokens),
        "active_auth_codes": len(authorization_codes),
        "tokens": {
            "access_tokens": [
                {
                    "token": token[:16] + "...",
                    "client_id": data["client_id"],
                    "scope": data["scope"],
                    "expires_at": data["expires_at"].isoformat()
                }
                for token, data in access_tokens.items()
            ]
        },
        "note": "⚠️ This endpoint is for development debugging only!"
    }

def validate_oauth_token(authorization_header: str) -> Dict:
    """Validate OAuth 2.1 access token"""
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization_header[7:]  # Remove "Bearer " prefix
    
    if token not in access_tokens:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    token_data = access_tokens[token]
    if is_token_expired(token_data):
        del access_tokens[token]
        raise HTTPException(status_code=401, detail="Access token expired")
    
    return token_data


def validate_api_key(authorization_header: str) -> Dict:
    """Validate API key - delegate to MCP server for validation"""
    if not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization_header[7:]  # Remove "Bearer " prefix
    
    # Check if this looks like an API key
    if not token.startswith("mcp_key_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    # Return API key info - let MCP server handle actual validation
    return {
        "type": "api_key",
        "scope": "mcp:search mcp:channels mcp:stats",  # Default scopes for API keys
        "token": token
    }


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
    authorization: Optional[str] = Header(None)
):
    """
    MCP 2.0 compliant endpoint (2025-03-26 specification)
    
    Only accepts HTTP POST with JSON-RPC 2.0 body
    Supports OAuth 2.1 authentication or API key authentication
    
    Headers:
    - Mcp-Session-Id: Session identifier for authenticated sessions
    - Authorization: Bearer <oauth_access_token> OR Bearer <mcp_key_...>
    """
    if not mcp_streamable_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        # Authentication required (OAuth or API key)
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        # Try OAuth token first, then fall back to API key
        token_data = None
        auth_type = None
        
        # Extract token from authorization header
        token = authorization[7:] if authorization.startswith("Bearer ") else None
        if not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Check if it's an OAuth token or API key
        if token.startswith("mcp_key_"):
            # API key authentication - let MCP server handle validation
            token_data = validate_api_key(authorization)
            auth_type = "api_key"
            logging.info(f"API key authentication attempt for key: {token[:16]}...")
        else:
            # OAuth token authentication
            token_data = validate_oauth_token(authorization)
            auth_type = "oauth"
            logging.info(f"OAuth authentication successful with scopes: {token_data['scope']}")
        
        # Log all incoming headers for debugging
        all_headers = dict(request.headers)
        logging.debug(f"Incoming request headers: {all_headers}")
        
        # Prepare headers dict
        headers = {}
        if mcp_session_id:
            headers["Mcp-Session-Id"] = mcp_session_id
            logging.debug(f"Session ID found: {mcp_session_id}")
        
        headers["Authorization"] = authorization
        
        # Pass appropriate scope information to MCP server
        if auth_type == "oauth":
            headers["OAuth-Scopes"] = token_data["scope"]  # Pass OAuth scopes
        # For API keys, let MCP server handle scope determination
        
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