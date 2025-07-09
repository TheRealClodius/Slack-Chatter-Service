"""
Dedicated Search Service for Slack Messages
Handles vector search operations independently from ingestion
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from lib.embedding_service import EmbeddingService
from lib.pinecone_service import PineconeService
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


class SearchService:
    """Dedicated service for searching Slack messages"""
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None, 
                 pinecone_service: Optional[PineconeService] = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.pinecone_service = pinecone_service or PineconeService()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Cache for frequently requested data
        self._channels_cache = None
        self._stats_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def search(self, query: str, top_k: int = 10, 
                    channel_filter: Optional[str] = None,
                    user_filter: Optional[str] = None,
                    date_from: Optional[str] = None,
                    date_to: Optional[str] = None) -> List[SearchResult]:
        """
        Search for similar messages using semantic search
        
        Args:
            query: Search query text
            top_k: Number of results to return (1-50)
            channel_filter: Filter by channel name
            user_filter: Filter by user name
            date_from: Filter messages from this date (YYYY-MM-DD)
            date_to: Filter messages to this date (YYYY-MM-DD)
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")
            
            top_k = max(1, min(top_k, 50))  # Clamp between 1 and 50
            
            self.logger.info(f"Searching for: '{query}' (top_k={top_k})")
            
            # Generate embedding for the query
            query_embedding = await self.embedding_service._generate_single_embedding(query)
            
            # Build filter for the query
            filter_dict = self._build_filter(
                channel_filter=channel_filter,
                user_filter=user_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            # Query vector database
            results = await self.pinecone_service.query_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_dict=filter_dict
            )
            
            # Convert to SearchResult objects
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
            
            self.logger.info(f"Search completed: returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise
    
    def _build_filter(self, channel_filter: Optional[str] = None,
                     user_filter: Optional[str] = None,
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Build filter dictionary for vector search"""
        filter_dict = {}
        
        if channel_filter:
            filter_dict["channel_name"] = channel_filter
        
        if user_filter:
            filter_dict["user_name"] = user_filter
        
        if date_from or date_to:
            date_filter = {}
            if date_from:
                date_filter["$gte"] = date_from
            if date_to:
                date_filter["$lte"] = date_to
            filter_dict["timestamp"] = date_filter
        
        return filter_dict if filter_dict else None
    
    async def get_channels(self) -> List[str]:
        """Get list of available channels"""
        try:
            # Check cache first
            if self._should_use_cache():
                if self._channels_cache is not None:
                    return self._channels_cache
            
            # Get channels from indexed data
            # This is a simplified implementation - in production you'd query the actual index
            channels = []
            
            # Get sample of vectors to extract channel names
            dummy_vector = [0.0] * 1536  # text-embedding-3-small dimension
            results = await self.pinecone_service.query_similar(
                query_embedding=dummy_vector,
                top_k=100
            )
            
            channel_names = set()
            for result in results:
                metadata = result.get("metadata", {})
                channel_name = metadata.get("channel_name")
                if channel_name:
                    channel_names.add(channel_name)
            
            channels = sorted(list(channel_names))
            
            # Cache the result
            self._channels_cache = channels
            self._cache_timestamp = datetime.now()
            
            return channels
            
        except Exception as e:
            self.logger.error(f"Failed to get channels: {str(e)}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        try:
            # Check cache first
            if self._should_use_cache():
                if self._stats_cache is not None:
                    return self._stats_cache
            
            # Get stats from pinecone service
            pinecone_stats = self.pinecone_service.get_index_stats()
            
            # Get additional stats
            channels = await self.get_channels()
            
            stats = {
                "total_vectors": pinecone_stats.get("total_vector_count", 0),
                "channels_indexed": len(channels),
                "dimension": pinecone_stats.get("dimension", 1536),
                "index_fullness": pinecone_stats.get("index_fullness", 0.0),
                "last_refresh": self._get_last_refresh_time(),
                "status": "operational" if pinecone_stats.get("total_vector_count", 0) > 0 else "empty"
            }
            
            # Cache the result
            self._stats_cache = stats
            self._cache_timestamp = datetime.now()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {str(e)}")
            return {
                "total_vectors": 0,
                "channels_indexed": 0,
                "dimension": 1536,
                "index_fullness": 0.0,
                "last_refresh": "Unknown",
                "status": "error"
            }
    
    def _should_use_cache(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl
    
    def _get_last_refresh_time(self) -> str:
        """Get the last refresh time from ingestion state"""
        try:
            from lib.utils import load_state
            state = load_state("ingestion_state.json")
            last_run = state.get("last_run")
            if last_run:
                return last_run
        except Exception:
            pass
        
        return "Unknown"
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the search service"""
        try:
            # Test basic connectivity
            stats = await self.get_stats()
            
            # Test embedding service
            embedding_available = True
            try:
                test_embedding = await self.embedding_service._generate_single_embedding("test")
                embedding_available = len(test_embedding) > 0
            except Exception:
                embedding_available = False
            
            # Test vector database
            vector_db_available = stats.get("status") != "error"
            
            return {
                "status": "healthy" if embedding_available and vector_db_available else "degraded",
                "embedding_service_available": embedding_available,
                "vector_db_available": vector_db_available,
                "total_vectors": stats.get("total_vectors", 0),
                "channels_indexed": stats.get("channels_indexed", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "embedding_service_available": False,
                "vector_db_available": False,
                "total_vectors": 0,
                "channels_indexed": 0
            }
    
    def clear_cache(self):
        """Clear the internal cache"""
        self._channels_cache = None
        self._stats_cache = None
        self._cache_timestamp = None
        self.logger.info("Cache cleared")


# Factory function to create the search service
def create_search_service(embedding_service: Optional[EmbeddingService] = None,
                         pinecone_service: Optional[PineconeService] = None) -> SlackSearchService:
    """Create a configured search service"""
    return SlackSearchService(
        embedding_service=embedding_service,
        pinecone_service=pinecone_service
    ) 