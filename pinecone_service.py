import asyncio
from typing import List, Tuple, Optional
from datetime import datetime

# Import Pinecone v7.3.0+ API components
from pinecone import Pinecone, ServerlessSpec

from config import config

class PineconeService:
    def __init__(self):
        self.index_name = config.pinecone_index_name
        
        # Initialize with Pinecone v7+ API
        self.pc = Pinecone(api_key=config.pinecone_api_key)
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index_exists(self):
        """Create index if it doesn't exist (Pinecone v3+ API)"""
        existing_indexes = self.pc.list_indexes().names()
        
        if self.index_name not in existing_indexes:
            print(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # text-embedding-3-small dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            
            # Wait for index to be ready
            import time
            while self.index_name not in self.pc.list_indexes().names():
                time.sleep(1)
    

    
    async def upsert_embeddings(self, embeddings_data: List[Tuple[str, List[float], dict]], 
                               batch_size: int = 100) -> int:
        """Upsert embeddings to Pinecone in batches"""
        total_upserted = 0
        
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i:i + batch_size]
            
            # Prepare vectors for upsert
            vectors = []
            for chunk_id, embedding, metadata in batch:
                vectors.append({
                    'id': chunk_id,
                    'values': embedding,
                    'metadata': metadata
                })
            
            try:
                # Upsert to Pinecone
                self.index.upsert(vectors=vectors)
                total_upserted += len(vectors)
                print(f"Upserted batch of {len(vectors)} embeddings to Pinecone")
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error upserting batch to Pinecone: {e}")
                continue
        
        return total_upserted
    
    def get_index_stats(self) -> dict:
        """Get statistics about the Pinecone index"""
        try:
            stats = self.index.describe_index_stats()
            return {
                'total_vector_count': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0.0)
            }
        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}
    
    def is_index_empty(self) -> bool:
        """Check if the index is empty"""
        stats = self.get_index_stats()
        return stats.get('total_vector_count', 0) == 0
    
    async def delete_old_vectors(self, before_timestamp: datetime):
        """Delete vectors older than specified timestamp"""
        try:
            # Query for old vectors
            query_response = self.index.query(
                vector=[0.0] * 1536,  # Dummy vector
                filter={
                    "timestamp": {"$lt": before_timestamp.isoformat()}
                },
                top_k=10000,
                include_metadata=True
            )
            
            # Delete old vectors
            if query_response.matches:
                ids_to_delete = [match.id for match in query_response.matches]
                self.index.delete(ids=ids_to_delete)
                print(f"Deleted {len(ids_to_delete)} old vectors from Pinecone")
                
        except Exception as e:
            print(f"Error deleting old vectors: {e}")
    
    async def query_similar(self, query_embedding: List[float], top_k: int = 10, 
                           filter_dict: Optional[dict] = None) -> List[dict]:
        """Query for similar vectors"""
        try:
            response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True,
                include_values=False
            )
            
            results = []
            for match in response.matches:
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                })
            
            return results
            
        except Exception as e:
            print(f"Error querying Pinecone: {e}")
            return []
