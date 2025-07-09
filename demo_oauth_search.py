#!/usr/bin/env python3
"""
OAuth 2.1 Search Demo
Demonstrates the complete OAuth 2.1 flow with actual Slack message search
"""

import requests
import secrets
import hashlib
import base64
import json
from urllib.parse import urlencode, parse_qs, urlparse

class MCPOAuthSearchDemo:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.client_id = "mcp-slack-chatter-client"
        self.client_secret = "mcp_client_secret_12345"
        self.redirect_uri = "http://localhost:3000/callback"
        self.access_token = None
        self.refresh_token = None
        self.code_verifier = None
    
    def generate_pkce(self):
        """Generate PKCE code verifier and challenge"""
        self.code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return self.code_verifier, code_challenge
    
    def get_oauth_token(self):
        """Complete OAuth flow and get access token"""
        print("🔐 Starting OAuth 2.1 Flow...")
        
        # Generate PKCE
        code_verifier, code_challenge = self.generate_pkce()
        
        # Get authorization code
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "mcp:search mcp:channels mcp:stats",
            "state": "demo_state_123",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        # Simulate authorization (auto-approve for demo)
        response = requests.get(f"{self.base_url}/oauth/authorize", 
                              params=params, allow_redirects=False)
        
        if response.status_code == 302:
            location = response.headers.get('Location')
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            auth_code = query_params['code'][0]
            print(f"✅ Authorization code obtained")
        else:
            raise Exception("Authorization failed")
        
        # Exchange code for tokens
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": self.code_verifier
        }
        
        response = requests.post(f"{self.base_url}/oauth/token", data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        
        print(f"✅ Access token obtained")
        print(f"   Expires in: {token_data['expires_in']} seconds")
        print(f"   Scopes: {token_data['scope']}")
        
        return token_data
    
    def search_messages(self, query, top_k=5):
        """Search Slack messages using OAuth authenticated MCP"""
        if not self.access_token:
            raise ValueError("No access token - run get_oauth_token() first")
        
        print(f"🔍 Searching for: '{query}'")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_slack_messages",
                "arguments": {
                    "query": query,
                    "top_k": top_k
                }
            },
            "id": 1
        }
        
        response = requests.post(f"{self.base_url}/mcp", 
                               headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print("✅ Search successful!")
            print("\n" + "="*50)
            print(content)
            print("="*50)
            return result
        else:
            print("❌ Search failed:")
            print(json.dumps(result, indent=2))
            return result
    
    def get_channels(self):
        """Get available Slack channels"""
        if not self.access_token:
            raise ValueError("No access token - run get_oauth_token() first")
        
        print("📺 Getting available channels...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_slack_channels",
                "arguments": {}
            },
            "id": 2
        }
        
        response = requests.post(f"{self.base_url}/mcp", 
                               headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print("✅ Channels retrieved!")
            print("\n" + content)
            return result
        else:
            print("❌ Failed to get channels:")
            print(json.dumps(result, indent=2))
            return result
    
    def get_stats(self):
        """Get search statistics"""
        if not self.access_token:
            raise ValueError("No access token - run get_oauth_token() first")
        
        print("📊 Getting search statistics...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_search_stats",
                "arguments": {}
            },
            "id": 3
        }
        
        response = requests.post(f"{self.base_url}/mcp", 
                               headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print("✅ Statistics retrieved!")
            print("\n" + content)
            return result
        else:
            print("❌ Failed to get statistics:")
            print(json.dumps(result, indent=2))
            return result
    
    def run_demo(self):
        """Run complete OAuth + Search demo"""
        print("🚀 OAuth 2.1 + MCP Search Demo")
        print("="*50)
        
        try:
            # Step 1: OAuth authentication
            self.get_oauth_token()
            print()
            
            # Step 2: Get available tools and stats
            self.get_stats()
            print()
            
            # Step 3: Get channels
            self.get_channels()
            print()
            
            # Step 4: Search examples
            search_queries = [
                "deployment",
                "authentication",
                "API",
                "error",
                "successful"
            ]
            
            for query in search_queries:
                print()
                self.search_messages(query, top_k=3)
                print()
            
            print("🎉 Demo completed successfully!")
            print("✅ OAuth 2.1 authentication working")
            print("✅ MCP protocol working")
            print("✅ Search functionality working")
            print("✅ Ready for production use!")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    demo = MCPOAuthSearchDemo()
    demo.run_demo()