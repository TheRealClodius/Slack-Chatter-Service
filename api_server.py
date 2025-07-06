"""
FastAPI web server for Slack message vector search
Provides REST API endpoints for other repos to search indexed messages
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from pinecone_service import PineconeService
from embedding_service import EmbeddingService
from scheduler import SlackWorkerScheduler
from data_models import SlackMessage


# Pydantic models for API requests/responses
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    channel_filter: Optional[str] = None
    user_filter: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


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
        print("🚀 Starting background Slack worker...")
        await background_scheduler.start()
        
        yield
        
    finally:
        # Cleanup on shutdown
        if background_scheduler:
            print("🛑 Stopping background Slack worker...")
            await background_scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Slack Message Vector Search API",
    description="Search indexed Slack messages using AI-powered semantic search",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Slack Message Vector Search API",
        "version": "1.0.0",
        "description": "Search indexed Slack messages using AI-powered semantic search",
        "endpoints": {
            "search": "/search?q=your_query&top_k=5",
            "health": "/health",
            "stats": "/stats", 
            "channels": "/channels",
            "documentation": "/docs"
        },
        "status": "operational",
        "background_worker": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
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
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/stats", response_model=IndexStats)
async def get_index_stats():
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
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/search", response_model=List[SearchResult])
async def search_messages(request: SearchRequest):
    """Search for similar messages using semantic search"""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not initialized")
        if not pinecone_service:
            raise HTTPException(status_code=503, detail="Vector storage service not initialized")
            
        # Generate embedding for search query
        query_embedding = await embedding_service._generate_single_embedding(request.query)
        
        # Build filter for Pinecone query
        filter_dict = {}
        if request.channel_filter:
            filter_dict["channel_name"] = request.channel_filter
        if request.user_filter:
            filter_dict["user_name"] = request.user_filter
        if request.date_from:
            filter_dict["timestamp"] = {"$gte": request.date_from}
        if request.date_to:
            if "timestamp" not in filter_dict:
                filter_dict["timestamp"] = {}
            filter_dict["timestamp"]["$lte"] = request.date_to
        
        # Query Pinecone for similar vectors
        results = await pinecone_service.query_similar(
            query_embedding=query_embedding,
            top_k=request.top_k,
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
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search", response_model=List[SearchResult])
async def search_messages_get(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(10, description="Number of results to return"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    user: Optional[str] = Query(None, description="Filter by user"),
    date_from: Optional[str] = Query(None, description="Filter messages from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter messages to date (YYYY-MM-DD)")
):
    """Search for similar messages using GET request (for easy testing)"""
    request = SearchRequest(
        query=q,
        top_k=top_k,
        channel_filter=channel,
        user_filter=user,
        date_from=date_from,
        date_to=date_to
    )
    return await search_messages(request)


@app.post("/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a refresh of message embeddings"""
    try:
        if background_scheduler:
            background_tasks.add_task(background_scheduler.hourly_refresh)
            return {"message": "Refresh triggered successfully"}
        else:
            raise HTTPException(status_code=503, detail="Background scheduler not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger refresh: {str(e)}")


@app.get("/channels")
async def list_channels():
    """Get list of indexed channels"""
    try:
        if not pinecone_service:
            raise HTTPException(status_code=503, detail="Vector storage service not initialized")
            
        stats = pinecone_service.get_index_stats()
        return {"channels": stats.get("channels", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)