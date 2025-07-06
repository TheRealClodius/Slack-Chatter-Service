from typing import List, Dict, Any
from datetime import datetime, timezone
import json
import os
import secrets
import string

def chunk_text(text: str, max_chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
    
    return chunks

def save_state(state: Dict[str, Any], filename: str = "worker_state.json"):
    """Save worker state to file"""
    with open(filename, 'w') as f:
        json.dump(state, f, indent=2, default=str)

def load_state(filename: str = "worker_state.json") -> Dict[str, Any]:
    """Load worker state from file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_current_utc_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def generate_secure_api_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure API key
    
    Args:
        length: Length of the API key (default 64 characters)
        
    Returns:
        Secure random API key string
    """
    # Use a mix of letters, digits, and some safe special characters
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not api_key:
        return False
    
    # Check minimum length
    if len(api_key) < 32:
        return False
    
    # Check maximum length (reasonable upper bound)
    if len(api_key) > 128:
        return False
    
    # Check allowed characters
    allowed_chars = set(string.ascii_letters + string.digits + "-_")
    if not all(c in allowed_chars for c in api_key):
        return False
    
    return True

def sanitize_log_data(data: str, max_length: int = 100) -> str:
    """
    Sanitize data for logging to prevent log injection
    
    Args:
        data: Data to sanitize
        max_length: Maximum length of sanitized data
        
    Returns:
        Sanitized data safe for logging
    """
    if not data:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = ''.join(c for c in data if c.isprintable() and c not in ['\n', '\r', '\t'])
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging (e.g., API keys)
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * 8
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]

if __name__ == "__main__":
    # Generate a new API key when script is run directly
    print("🔑 Generating secure API key...")
    api_key = generate_secure_api_key()
    print(f"Generated API key: {api_key}")
    print(f"Key length: {len(api_key)} characters")
    print("\n⚠️  IMPORTANT: Store this key securely and set it as the API_KEY environment variable!")
    print("Example: export API_KEY=\"" + api_key + "\"")
