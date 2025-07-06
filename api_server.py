"""
FastAPI web server for Slack message vector search
Provides REST API endpoints for other repos to search indexed messages
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator, constr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import hashlib
import hmac
import os

from config import config
from pinecone_service import PineconeService
from embedding_service import EmbeddingService
from scheduler import SlackWorkerScheduler
from data_models import SlackMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)

# Pydantic models for API requests/responses with validation
class SearchRequest(BaseModel):
    query: constr(min_length=1, max_length=1000, strip_whitespace=True)
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results (max 50)")
    channel_filter: Optional[constr(min_length=1, max_length=100)] = None
    user_filter: Optional[constr(min_length=1, max_length=100)] = None
    date_from: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    date_to: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    
    @validator('query')
    def validate_query(cls, v):
        # Basic sanitization - remove potential harmful characters
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        # Remove potential script injection attempts
        dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'data:']
        for char in dangerous_chars:
            if char in v.lower():
                raise ValueError("Query contains potentially dangerous characters")
        return v.strip()
    
    @validator('date_from', 'date_to')
    def validate_dates(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

class SearchResult(BaseModel):
    message_id: str
    text: str
    user_name: str
    channel_name: str
    timestamp: str
    similarity_score: float
    metadata: Dict[str, Any]

class IndexStats(BaseModel):
    total_vectors: int
    channels_indexed: List[str]
    last_refresh: Optional[str]
    status: str

class HealthResponse(BaseModel):
    status: str
    message: str
    background_worker_running: bool
    vector_storage_available: bool

class APIKeyValidationError(Exception):
    pass

# Security functions
async def verify_api_key(
    request: Request,
    authorization: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify API key from Authorization header"""
    try:
        # Get the token from Authorization header
        token = authorization.credentials
        
        # Check if API key is configured
        expected_key = config.api_key
        if not expected_key:
            logger.error("API key not configured in environment")
            raise HTTPException(
                status_code=500, 
                detail="API authentication not properly configured"
            )
        
        # Verify API key using constant-time comparison
        if not hmac.compare_digest(token, expected_key):
            client_ip = request.client.host
            logger.warning(f"Invalid API key attempt from {client_ip}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Log successful authentication
        client_ip = request.client.host
        logger.info(f"Authenticated API access from {client_ip}")
        return token
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"API key verification error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

# Global services
pinecone_service = None
embedding_service = None
background_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start background worker on startup"""
    global pinecone_service, embedding_service, background_scheduler
    
    try:
        # Initialize services
        pinecone_service = PineconeService()
        embedding_service = EmbeddingService()
        background_scheduler = SlackWorkerScheduler()
        
        # Start background worker
        logger.info("🚀 Starting background Slack worker...")
        await background_scheduler.start()
        
        yield
        
    finally:
        # Cleanup on shutdown
        if background_scheduler:
            logger.info("🛑 Stopping background Slack worker...")
            await background_scheduler.stop()

# Create FastAPI app
app = FastAPI(
    title="Slack Message Vector Search API",
    description="Secure API for searching indexed Slack messages using AI-powered semantic search",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.enable_docs else None,
    redoc_url="/redoc" if config.enable_docs else None
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware for logging and headers
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and logging"""
    start_time = time.time()
    
    # Log request
    client_ip = request.client.host
    method = request.method
    path = request.url.path
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(f"API Request: {client_ip} {method} {path} - User-Agent: {user_agent}")
    
    # Call the endpoint
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"API Response: {client_ip} {method} {path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

# Restrictive CORS middleware
allowed_origins = config.allowed_origins or ["https://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
async def root():
    """Root endpoint - minimal information disclosure"""
    return {
        "name": "Slack Message Vector Search API",
        "version": "1.0.0",
        "status": "operational",
        "authentication": "required"
    }

@app.get("/health", response_model=HealthResponse)
@limiter.limit("30/minute")
async def health_check(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Health check endpoint"""
    try:
        # Check if vector storage is accessible
        storage_available = True
        if pinecone_service:
            try:
                stats = pinecone_service.get_index_stats()
            except Exception:
                storage_available = False
        else:
            storage_available = False
        
        # Check if background worker is running
        worker_running = background_scheduler is not None
        
        return HealthResponse(
            status="healthy" if storage_available and worker_running else "degraded",
            message="Slack message search API is operational",
            background_worker_running=worker_running,
            vector_storage_available=storage_available
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/stats", response_model=IndexStats)
@limiter.limit("20/minute")
async def get_index_stats(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Get statistics about the indexed messages"""
    try:
        if not pinecone_service:
            raise HTTPException(status_code=503, detail="Vector storage service not initialized")
            
        stats = pinecone_service.get_index_stats()
        
        return IndexStats(
            total_vectors=stats.get("total_vectors", 0),
            channels_indexed=stats.get("channels", []),
            last_refresh=stats.get("last_updated"),
            status="ready" if stats.get("total_vectors", 0) > 0 else "indexing"
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

@app.post("/search", response_model=List[SearchResult])
@limiter.limit("60/minute")
async def search_messages(
    request: Request,
    search_request: SearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """Search for similar messages using semantic search"""
    try:
        # Log search request for audit
        client_ip = request.client.host
        logger.info(f"Search request from {client_ip}: query='{search_request.query[:50]}...' top_k={search_request.top_k}")
        
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not initialized")
        if not pinecone_service:
            raise HTTPException(status_code=503, detail="Vector storage service not initialized")
            
        # Generate embedding for search query
        query_embedding = await embedding_service._generate_single_embedding(search_request.query)
        
        # Build filter for query
        filter_dict = {}
        if search_request.channel_filter:
            filter_dict["channel_name"] = search_request.channel_filter
        if search_request.user_filter:
            filter_dict["user_name"] = search_request.user_filter
        if search_request.date_from:
            filter_dict["timestamp"] = {"$gte": search_request.date_from}
        if search_request.date_to:
            if "timestamp" not in filter_dict:
                filter_dict["timestamp"] = {}
            filter_dict["timestamp"]["$lte"] = search_request.date_to
        
        # Query vector storage for similar vectors
        results = await pinecone_service.query_similar(
            query_embedding=query_embedding,
            top_k=search_request.top_k,
            filter_dict=filter_dict if filter_dict else None
        )
        
        # Convert results to response format
        search_results = []
        for result in results:
            metadata = result.get("metadata", {})
            search_results.append(SearchResult(
                message_id=result.get("id", ""),
                text=metadata.get("text", ""),
                user_name=metadata.get("user_name", ""),
                channel_name=metadata.get("channel_name", ""),
                timestamp=metadata.get("timestamp", ""),
                similarity_score=result.get("score", 0.0),
                metadata=metadata
            ))
        
        logger.info(f"Search completed for {client_ip}: returned {len(search_results)} results")
        return search_results
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/search", response_model=List[SearchResult])
@limiter.limit("60/minute")
async def search_messages_get(
    request: Request,
    q: str = Query(..., description="Search query", min_length=1, max_length=1000),
    top_k: int = Query(10, description="Number of results to return", ge=1, le=50),
    channel: Optional[str] = Query(None, description="Filter by channel", max_length=100),
    user: Optional[str] = Query(None, description="Filter by user", max_length=100),
    date_from: Optional[str] = Query(None, description="Filter messages from date (YYYY-MM-DD)", pattern=r'^\d{4}-\d{2}-\d{2}$'),
    date_to: Optional[str] = Query(None, description="Filter messages to date (YYYY-MM-DD)", pattern=r'^\d{4}-\d{2}-\d{2}$'),
    api_key: str = Depends(verify_api_key)
):
    """Search for similar messages using GET request"""
    search_request = SearchRequest(
        query=q,
        top_k=top_k,
        channel_filter=channel,
        user_filter=user,
        date_from=date_from,
        date_to=date_to
    )
    return await search_messages(request, search_request, api_key)

@app.post("/refresh")
@limiter.limit("5/minute")
async def trigger_refresh(
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Manually trigger a refresh of message embeddings"""
    try:
        client_ip = request.client.host
        logger.info(f"Refresh triggered by {client_ip}")
        
        if background_scheduler:
            background_tasks.add_task(background_scheduler.hourly_refresh)
            return {"message": "Refresh triggered successfully"}
        else:
            raise HTTPException(status_code=503, detail="Background scheduler not available")
    except Exception as e:
        logger.error(f"Failed to trigger refresh: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger refresh")

@app.get("/channels")
@limiter.limit("30/minute")
async def list_channels(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Get list of indexed channels"""
    try:
        if not pinecone_service:
            raise HTTPException(status_code=503, detail="Vector storage service not initialized")
            
        stats = pinecone_service.get_index_stats()
        return {"channels": stats.get("channels", [])}
    except Exception as e:
        logger.error(f"Failed to get channels: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get channels")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5000,
        log_level="info",
        ssl_keyfile=config.ssl_keyfile if config.ssl_keyfile else None,
        ssl_certfile=config.ssl_certfile if config.ssl_certfile else None
    )