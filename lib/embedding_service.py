import asyncio
from typing import List, Tuple
from openai import OpenAI

from lib.config import config
from lib.data_models import SlackMessage
from lib.rate_limiter import rate_limiter
from lib.utils import chunk_text

class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
    
    async def generate_embeddings(self, messages: List[SlackMessage]) -> List[Tuple[str, List[float], dict]]:
        """Generate embeddings for messages, returning (id, embedding, metadata) tuples"""
        embeddings_data = []
        
        for message in messages:
            # Convert message to text for embedding
            text = message.to_text_for_embedding()
            
            # Chunk the text if it's too long
            chunks = chunk_text(text, config.max_chunk_size, config.chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{message.id}"
                if len(chunks) > 1:
                    chunk_id += f"_chunk_{i}"
                
                # Generate embedding
                embedding = await self._generate_single_embedding(chunk)
                if embedding:
                    # Create metadata
                    metadata = message.to_metadata()
                    metadata['chunk_index'] = i
                    metadata['total_chunks'] = len(chunks)
                    metadata['text'] = chunk
                    
                    embeddings_data.append((chunk_id, embedding, metadata))
        
        return embeddings_data
    
    async def _generate_single_embedding(self, text: str) -> List[float]:
        """Generate a single embedding for text"""
        try:
            await rate_limiter.wait_if_needed("openai", config.openai_rate_limit_per_minute)
            
            # Note: the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # For embeddings, we use text-embedding-3-small which is efficient and effective
            response = self.client.embeddings.create(
                model=config.embedding_model,
                input=text,
                dimensions=config.embedding_dimensions
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
