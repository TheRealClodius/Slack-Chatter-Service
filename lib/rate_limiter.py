import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Deque, Optional, Callable, Any, cast
from functools import wraps
from slack_sdk.web import SlackResponse
from slack_sdk.errors import SlackApiError

class EnhancedRateLimiter:
    def __init__(self):
        self.request_times: Dict[str, Deque[float]] = defaultdict(deque)
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.retry_after_until: Dict[str, float] = {}  # Track Retry-After headers
        
        # Slack endpoint-specific rate limits (requests per minute)
        self.slack_endpoint_limits = {
            "conversations.history": 100,     # Tier 2
            "conversations.replies": 100,     # Tier 2
            "users.info": 100,               # Tier 3
            "conversations.info": 100,       # Tier 3
            "conversations.list": 20,        # Tier 4 (most restrictive)
            "users.lookupByEmail": 100,      # Tier 3
            "usergroups.list": 100,          # Tier 3
            "usergroups.users.list": 100,    # Tier 3
            "reactions.add": 100,            # Tier 3
            "reactions.remove": 100,         # Tier 3
            "chat.postMessage": 100,         # Tier 3
            "chat.postEphemeral": 100,       # Tier 3
            "chat.getPermalink": 100,        # Tier 3
            "auth.test": 100,                # Tier 3
            "default": 50                    # Conservative default
        }
    
    def set_retry_after(self, service: str, endpoint: str, retry_after_seconds: int):
        """Set retry-after time for a specific service endpoint"""
        key = f"{service}:{endpoint}"
        self.retry_after_until[key] = time.time() + retry_after_seconds
        print(f"Rate limited by {service} {endpoint}: waiting {retry_after_seconds} seconds")
    
    def get_endpoint_limit(self, service: str, endpoint: str) -> int:
        """Get the rate limit for a specific endpoint"""
        if service == "slack":
            return self.slack_endpoint_limits.get(endpoint, self.slack_endpoint_limits["default"])
        # For other services, use the provided limit
        return 60  # Default fallback
    
    async def wait_if_needed(self, service: str, requests_per_minute: int, endpoint: Optional[str] = None):
        """Wait if necessary to respect rate limits"""
        # Use endpoint-specific limit if available
        if endpoint and service == "slack":
            requests_per_minute = self.get_endpoint_limit(service, endpoint)
        
        key = f"{service}:{endpoint}" if endpoint else service
        
        async with self.locks[key]:
            now = time.time()
            
            # Check if we need to wait due to Retry-After header
            if key in self.retry_after_until:
                if now < self.retry_after_until[key]:
                    wait_time = self.retry_after_until[key] - now
                    print(f"Waiting for Retry-After: {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                else:
                    # Retry-After period has passed
                    del self.retry_after_until[key]
            
            minute_ago = now - 60
            
            # Remove old entries
            while self.request_times[key] and self.request_times[key][0] < minute_ago:
                self.request_times[key].popleft()
            
            # Check if we need to wait for rate limit
            if len(self.request_times[key]) >= requests_per_minute:
                oldest_request = self.request_times[key][0]
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    print(f"Rate limiting {service} {endpoint or 'default'}: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times[key].append(time.time())
    
    def make_slack_api_call_rate_limited(
        self, 
        call: Callable[..., SlackResponse], 
        max_retries: int = 7
    ) -> Callable[..., SlackResponse]:
        """
        Enhanced decorator that wraps Slack API calls with comprehensive rate limiting and error handling
        Inspired by danswer's implementation but adapted for async usage
        """
        @wraps(call)
        async def rate_limited_call(**kwargs: Any) -> SlackResponse:
            method_name = call.__name__
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Apply rate limiting before making the call
                    await self.wait_if_needed("slack", 0, endpoint=method_name)
                    
                    # Make the API call
                    response = call(**kwargs)
                    
                    # Check for errors in the response
                    response.validate()
                    return response
                    
                except SlackApiError as e:
                    last_exception = e
                    error_code = e.response.get("error", "unknown_error")
                    
                    if error_code == "ratelimited":
                        # Handle rate limiting with Retry-After header
                        retry_after = int(e.response.headers.get("Retry-After", 60))
                        print(f"Slack API rate limited for {method_name}, retrying after {retry_after} seconds")
                        
                        # Set retry-after for this endpoint
                        self.set_retry_after("slack", method_name, retry_after)
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            print(f"Rate limit exceeded for {method_name} after {max_retries} attempts")
                            raise
                    
                    elif error_code in ["already_reacted", "no_reaction"]:
                        # These are acceptable "errors" for reaction operations
                        print(f"Reaction operation result: {error_code}")
                        return e.response
                    
                    elif "status" in e.response and e.response["status"] == 503:
                        # Server unavailable - wait and retry
                        if attempt < max_retries - 1:
                            wait_time = 60  # Wait 1 minute for server issues
                            print(f"Server unavailable (503) for {method_name}, retrying in {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"Server unavailable for {method_name} after {max_retries} attempts")
                            raise
                    
                    elif error_code in ["channel_not_found", "user_not_found", "not_in_channel"]:
                        # These are permanent errors - don't retry
                        print(f"Permanent error for {method_name}: {error_code}")
                        raise
                    
                    else:
                        # Other errors - retry with exponential backoff
                        if attempt < max_retries - 1:
                            wait_time = min(2 ** attempt, 60)  # Exponential backoff, max 60 seconds
                            print(f"Error {error_code} for {method_name}, retrying in {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"Non-recoverable error for {method_name}: {error_code}")
                            raise
                
                except Exception as e:
                    # Non-Slack API errors
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 60)
                        print(f"Unexpected error for {method_name}: {str(e)}, retrying in {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print(f"Unexpected error for {method_name} after {max_retries} attempts: {str(e)}")
                        raise
            
            # If we get here, all retries were exhausted
            msg = f"Max retries ({max_retries}) exceeded for {method_name}"
            if last_exception:
                raise Exception(msg) from last_exception
            else:
                raise Exception(msg)
        
        return rate_limited_call
    
    def make_slack_api_call_logged(
        self, 
        call: Callable[..., SlackResponse]
    ) -> Callable[..., SlackResponse]:
        """Add logging to Slack API calls"""
        @wraps(call)
        async def logged_call(**kwargs: Any) -> SlackResponse:
            method_name = call.__name__
            print(f"Making Slack API call: {method_name}")
            
            try:
                result = await call(**kwargs)
                print(f"Slack API call successful: {method_name}")
                return result
            except Exception as e:
                print(f"Slack API call failed: {method_name} - {str(e)}")
                raise
        
        return logged_call
    
    def make_slack_api_call_paginated(
        self, 
        call: Callable[..., SlackResponse]
    ) -> Callable[..., Any]:
        """
        Enhanced pagination wrapper that handles cursor-based pagination
        Adapted from danswer's implementation for async usage
        """
        @wraps(call)
        async def paginated_call(**kwargs: Any) -> Any:
            cursor: Optional[str] = None
            has_more = True
            page_limit = 1000  # Maximum page size for efficiency
            
            while has_more:
                # Add pagination parameters
                paginated_kwargs = {
                    **kwargs,
                    "limit": page_limit,
                }
                
                if cursor:
                    paginated_kwargs["cursor"] = cursor
                
                # Make the rate-limited API call
                response = await call(**paginated_kwargs)
                
                # Validate response
                response.validate()
                response_data = cast(dict, response.data)
                
                # Yield the current page of results
                yield response_data
                
                # Check for more pages
                metadata = response_data.get("response_metadata", {})
                cursor = metadata.get("next_cursor", "")
                has_more = bool(cursor)
        
        return paginated_call

# Global instance
rate_limiter = EnhancedRateLimiter()
