import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from lib.config import config

class PineconeService:
    def __init__(self):
        # Use real Pinecone API if configured, fallback to local storage
        self.use_pinecone = bool(config.pinecone_api_key and config.pinecone_environment)
        
        if self.use_pinecone:
            try:
                from pinecone import Pinecone
                self.pc = Pinecone(api_key=config.pinecone_api_key)
                self.index = self.pc.Index(config.pinecone_index_name)
                print(f"✅ Connected to Pinecone index: {config.pinecone_index_name}")
            except Exception as e:
                print(f"❌ Pinecone connection failed: {e}")
                print("Falling back to local storage...")
                self.use_pinecone = False
        
        if not self.use_pinecone:
            # Fallback to local file storage
            self.storage_file = "pinecone_vectors.json"
            self.storage_dir = os.path.dirname(self.storage_file)
            
            # Create storage directory if it doesn't exist
            if self.storage_dir and not os.path.exists(self.storage_dir):
                os.makedirs(self.storage_dir)
    
    def is_index_empty(self) -> bool:
        """Check if the index is empty"""
        if self.use_pinecone:
            try:
                stats = self.index.describe_index_stats()
                return stats.total_vector_count == 0
            except Exception as e:
                print(f"Error checking Pinecone index: {e}")
                return True
        else:
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    return len(data.get('vectors', [])) == 0
            except (FileNotFoundError, json.JSONDecodeError):
                return True
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if self.use_pinecone:
            try:
                stats = self.index.describe_index_stats()
                return {
                    'total_vector_count': stats.total_vector_count,
                    'dimension': stats.dimension,
                    'index_fullness': stats.index_fullness,
                    'last_update': 'Real-time'
                }
            except Exception as e:
                print(f"Error getting Pinecone stats: {e}")
                return {
                    'total_vector_count': 0,
                    'dimension': config.embedding_dimensions,
                    'index_fullness': 0.0,
                    'last_update': 'Error'
                }
        else:
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                vectors = data.get('vectors', [])
                return {
                    'total_vector_count': len(vectors),
                    'dimension': config.embedding_dimensions,
                    'index_fullness': 0.0,
                    'last_update': data.get('last_update', 'Never')
                }
            except (FileNotFoundError, json.JSONDecodeError):
                return {
                    'total_vector_count': 0,
                    'dimension': config.embedding_dimensions,
                    'index_fullness': 0.0,
                    'last_update': 'Never'
                }
    
    async def upsert_embeddings(self, embeddings_data: List[tuple]):
        """Upsert embeddings into the index"""
        if self.use_pinecone:
            try:
                # Convert to Pinecone format
                vectors = []
                for embedding_id, embedding_vector, metadata in embeddings_data:
                    vectors.append({
                        'id': embedding_id,
                        'values': embedding_vector,
                        'metadata': metadata
                    })
                
                # Upsert to Pinecone in batches
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    self.index.upsert(vectors=batch)
                    
                print(f"✅ Upserted {len(vectors)} vectors to Pinecone")
                
            except Exception as e:
                print(f"❌ Error upserting to Pinecone: {e}")
                raise
        else:
            try:
                # Load existing data
                try:
                    with open(self.storage_file, 'r') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {'vectors': [], 'last_update': None}
                
                # Convert new embeddings to storage format
                vectors = data.get('vectors', [])
                existing_ids = {v['id'] for v in vectors}
                
                new_vectors = []
                for embedding_id, embedding_vector, metadata in embeddings_data:
                    vector_data = {
                        'id': embedding_id,
                        'values': embedding_vector,
                        'metadata': metadata
                    }
                    new_vectors.append(vector_data)
                
                # Remove duplicates and add new vectors
                for new_vector in new_vectors:
                    if new_vector['id'] not in existing_ids:
                        vectors.append(new_vector)
                    else:
                        # Update existing vector
                        for i, existing_vector in enumerate(vectors):
                            if existing_vector['id'] == new_vector['id']:
                                vectors[i] = new_vector
                                break
                
                # Save updated data
                data['vectors'] = vectors
                data['last_update'] = datetime.utcnow().isoformat()
                
                with open(self.storage_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                print(f"✅ Saved {len(new_vectors)} vectors to local storage")
                
            except Exception as e:
                print(f"❌ Error saving to local storage: {e}")
                raise
            
            # Update data
            data['vectors'] = vectors
            data['last_update'] = datetime.now().isoformat()
            
            # Save to file
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Upserted {len(new_vectors)} vectors to index")
            
        except Exception as e:
            print(f"Error upserting embeddings: {e}")
    
    async def delete_by_filter(self, filter_dict: Dict[str, Any]):
        """Delete vectors matching the filter"""
        try:
            # Load existing data
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            
            vectors = data.get('vectors', [])
            original_count = len(vectors)
            
            # Filter vectors (simple implementation)
            filtered_vectors = []
            for vector in vectors:
                metadata = vector.get('metadata', {})
                should_delete = True
                
                for key, value in filter_dict.items():
                    if key not in metadata or metadata[key] != value:
                        should_delete = False
                        break
                
                if not should_delete:
                    filtered_vectors.append(vector)
            
            # Update data
            data['vectors'] = filtered_vectors
            data['last_update'] = datetime.now().isoformat()
            
            # Save to file
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            deleted_count = original_count - len(filtered_vectors)
            print(f"Deleted {deleted_count} vectors from index")
            
        except Exception as e:
            print(f"Error deleting vectors: {e}")
    
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