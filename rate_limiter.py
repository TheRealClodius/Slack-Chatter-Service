import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Deque

class RateLimiter:
    def __init__(self):
        self.request_times: Dict[str, Deque[float]] = defaultdict(deque)
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def wait_if_needed(self, service: str, requests_per_minute: int):
        """Wait if necessary to respect rate limits"""
        async with self.locks[service]:
            now = time.time()
            minute_ago = now - 60
            
            # Remove old entries
            while self.request_times[service] and self.request_times[service][0] < minute_ago:
                self.request_times[service].popleft()
            
            # Check if we need to wait
            if len(self.request_times[service]) >= requests_per_minute:
                oldest_request = self.request_times[service][0]
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    print(f"Rate limiting {service}: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times[service].append(time.time())

rate_limiter = RateLimiter()
