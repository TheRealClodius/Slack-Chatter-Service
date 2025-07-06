from typing import List
from datetime import datetime, timezone
import json
import os

def chunk_text(text: str, max_chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of this chunk
        end = start + max_chunk_size
        
        # If this isn't the last chunk, try to break at a word boundary
        if end < len(text):
            # Look for the last space within a reasonable distance
            space_pos = text.rfind(' ', start, end)
            if space_pos > start + max_chunk_size // 2:
                end = space_pos
        
        chunks.append(text[start:end])
        
        # Move start position, accounting for overlap
        start = end - overlap
        if start < 0:
            start = 0
    
    return chunks

def save_state(data: dict, filename: str = "worker_state.json"):
    """Save worker state to file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, default=str)
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state(filename: str = "worker_state.json") -> dict:
    """Load worker state from file"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading state: {e}")
    
    return {}

def get_current_utc_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
