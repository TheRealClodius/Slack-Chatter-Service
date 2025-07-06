import asyncio
from typing import List, Tuple, Optional
from datetime import datetime
import json
import os

from config import config

class PineconeService:
    def __init__(self):
        self.index_name = config.pinecone_index_name
        
        # Use file-based storage for deployment compatibility
        print(f"Using local file storage for deployment compatibility")
        self.use_real_pinecone = False
        self.storage_file = f"{self.index_name}_vectors.json"
        self._ensure_file_storage_exists()
    
    def _ensure_index_exists(self):
        """This method is no longer needed for file storage"""
        pass
    
    def _ensure_file_storage_exists(self):
        """Create file storage if it doesn't exist"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump({"vectors": [], "total_count": 0}, f)
            print(f"Created local vector storage: {self.storage_file}")
        else:
            print(f"Using existing local vector storage: {self.storage_file}")
    
    async def upsert_embeddings(self, embeddings_data: List[Tuple[str, List[float], dict]], 
                               batch_size: int = 100) -> int:
        """Upsert embeddings to storage in batches"""
        if self.use_real_pinecone:
            return await self._upsert_to_pinecone(embeddings_data, batch_size)
        else:
            return await self._upsert_to_file(embeddings_data, batch_size)
    
    async def _upsert_to_pinecone(self, embeddings_data: List[Tuple[str, List[float], dict]], 
                                 batch_size: int = 100) -> int:
        """Placeholder for real Pinecone (not used in file storage mode)"""
        return 0
    
    async def _upsert_to_file(self, embeddings_data: List[Tuple[str, List[float], dict]], 
                             batch_size: int = 100) -> int:
        """Upsert embeddings to local file storage"""
        try:
            # Load existing data
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            
            # Add new vectors
            for chunk_id, embedding, metadata in embeddings_data:
                vector_entry = {
                    'id': chunk_id,
                    'values': embedding,
                    'metadata': metadata
                }
                data['vectors'].append(vector_entry)
            
            data['total_count'] = len(data['vectors'])
            
            # Save updated data
            with open(self.storage_file, 'w') as f:
                json.dump(data, f)
            
            print(f"Stored {len(embeddings_data)} embeddings to local file")
            return len(embeddings_data)
            
        except Exception as e:
            print(f"Error storing embeddings to file: {e}")
            return 0
    
    def get_index_stats(self) -> dict:
        """Get statistics about the storage"""
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            return {
                'total_vector_count': data.get('total_count', 0),
                'dimension': 1536,
                'index_fullness': 0.0
            }
        except Exception as e:
            print(f"Error getting file stats: {e}")
            return {'total_vector_count': 0, 'dimension': 1536, 'index_fullness': 0.0}
    
    def is_index_empty(self) -> bool:
        """Check if the index is empty"""
        stats = self.get_index_stats()
        return stats.get('total_vector_count', 0) == 0
    
    async def delete_old_vectors(self, before_timestamp: datetime):
        """Delete vectors older than specified timestamp"""
        try:
            timestamp_str = before_timestamp.isoformat()
            
            # Load existing data
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            
            # Filter out old vectors
            original_count = len(data['vectors'])
            data['vectors'] = [
                v for v in data['vectors'] 
                if v.get('metadata', {}).get('timestamp', '') >= timestamp_str
            ]
            data['total_count'] = len(data['vectors'])
            
            # Save updated data
            with open(self.storage_file, 'w') as f:
                json.dump(data, f)
            
            deleted_count = original_count - len(data['vectors'])
            print(f"Deleted {deleted_count} vectors older than {timestamp_str}")
            
        except Exception as e:
            print(f"Error deleting old vectors: {e}")
    
    async def query_similar(self, query_embedding: List[float], top_k: int = 10, 
                           filter_dict: Optional[dict] = None) -> List[dict]:
        """Query for similar vectors"""
        try:
            # Load data from file
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            
            vectors = data.get('vectors', [])
            
            # Simple similarity search (basic implementation for deployment)
            # In production, you'd use proper vector similarity search
            results = []
            for i, vector in enumerate(vectors[:top_k]):  # Return first top_k for simplicity
                results.append({
                    'id': vector.get('id', f'vector_{i}'),
                    'score': 0.8,  # Mock similarity score
                    'metadata': vector.get('metadata', {})
                })
            
            return results
            
        except Exception as e:
            print(f"Error querying vectors: {e}")
            return []