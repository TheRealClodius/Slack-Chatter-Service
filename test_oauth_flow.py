#!/usr/bin/env python3
"""
OAuth 2.1 Flow Test Script
Tests the complete OAuth 2.1 authentication flow for MCP Remote Protocol
"""

import requests
import secrets
import hashlib
import base64
import json
from urllib.parse import urlencode, parse_qs, urlparse

class MCPOAuthTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.client_id = "mcp-slack-chatter-client"
        self.client_secret = "mcp_client_secret_12345"
        self.redirect_uri = "http://localhost:3000/callback"
        self.access_token = None
        self.refresh_token = None
        self.code_verifier = None
    
    def test_discovery(self):
        """Test OAuth 2.1 discovery endpoint"""
        print("🔍 Testing OAuth 2.1 Discovery...")
        
        try:
            response = requests.get(f"{self.base_url}/.well-known/oauth-authorization-server")
            response.raise_for_status()
            
            discovery = response.json()
            print("✅ Discovery successful!")
            print(f"   Authorization endpoint: {discovery.get('authorization_endpoint')}")
            print(f"   Token endpoint: {discovery.get('token_endpoint')}")
            print(f"   Supported scopes: {discovery.get('scopes_supported')}")
            return True
            
        except Exception as e:
            print(f"❌ Discovery failed: {e}")
            return False
    
    def get_client_info(self):
        """Get OAuth client information from debug endpoint"""
        print("🔧 Getting client information...")
        
        try:
            response = requests.get(f"{self.base_url}/debug/oauth-client-info")
            response.raise_for_status()
            
            client_info = response.json()
            print("✅ Client info retrieved!")
            return client_info
            
        except Exception as e:
            print(f"❌ Failed to get client info: {e}")
            return None
    
    def generate_pkce(self):
        """Generate PKCE code verifier and challenge"""
        print("🔐 Generating PKCE values...")
        
        # Generate code verifier
        self.code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        print(f"✅ PKCE generated!")
        print(f"   Code verifier: {self.code_verifier[:20]}...")
        print(f"   Code challenge: {code_challenge[:20]}...")
        
        return self.code_verifier, code_challenge
    
    def get_authorization_url(self):
        """Generate authorization URL"""
        print("🔗 Generating authorization URL...")
        
        code_verifier, code_challenge = self.generate_pkce()
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "mcp:search mcp:channels mcp:stats",
            "state": secrets.token_urlsafe(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{self.base_url}/oauth/authorize?{urlencode(params)}"
        print(f"✅ Authorization URL generated!")
        print(f"   URL: {auth_url}")
        
        return auth_url
    
    def simulate_authorization(self):
        """Simulate the authorization step by making a direct request"""
        print("🤖 Simulating authorization flow...")
        
        code_verifier, code_challenge = self.generate_pkce()
        
        # Make authorization request
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "mcp:search mcp:channels mcp:stats",
            "state": "test_state_123",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        try:
            response = requests.get(f"{self.base_url}/oauth/authorize", 
                                  params=params, allow_redirects=False)
            
            if response.status_code == 302:
                # Extract authorization code from redirect
                location = response.headers.get('Location')
                parsed_url = urlparse(location)
                query_params = parse_qs(parsed_url.query)
                
                if 'code' in query_params:
                    auth_code = query_params['code'][0]
                    print(f"✅ Authorization code received: {auth_code[:20]}...")
                    return auth_code
                else:
                    print(f"❌ No authorization code in redirect: {location}")
                    return None
            else:
                print(f"❌ Unexpected response status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Authorization failed: {e}")
            return None
    
    def exchange_code_for_tokens(self, authorization_code):
        """Exchange authorization code for access tokens"""
        print("🎟️  Exchanging code for tokens...")
        
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": self.code_verifier
        }
        
        try:
            response = requests.post(f"{self.base_url}/oauth/token", data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            
            print("✅ Tokens obtained!")
            print(f"   Access token: {self.access_token[:20]}...")
            print(f"   Refresh token: {self.refresh_token[:20]}...")
            print(f"   Expires in: {token_data['expires_in']} seconds")
            print(f"   Scope: {token_data['scope']}")
            
            return token_data
            
        except Exception as e:
            print(f"❌ Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return None
    
    def test_mcp_request(self):
        """Test MCP request with OAuth token"""
        print("🔍 Testing MCP request...")
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        try:
            response = requests.post(f"{self.base_url}/mcp", 
                                   headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            print("✅ MCP request successful!")
            
            if 'result' in result and 'tools' in result['result']:
                tools = result['result']['tools']
                print(f"   Available tools: {len(tools)}")
                for tool in tools[:3]:  # Show first 3 tools
                    print(f"   - {tool.get('name', 'Unknown')}")
                if len(tools) > 3:
                    print(f"   - ... and {len(tools) - 3} more")
            
            return True
            
        except Exception as e:
            print(f"❌ MCP request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return False
    
    def test_token_introspection(self):
        """Test token introspection"""
        print("🔍 Testing token introspection...")
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        data = {
            "token": self.access_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(f"{self.base_url}/oauth/introspect", data=data)
            response.raise_for_status()
            
            result = response.json()
            print("✅ Token introspection successful!")
            print(f"   Active: {result.get('active')}")
            print(f"   Client ID: {result.get('client_id')}")
            print(f"   Scope: {result.get('scope')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Token introspection failed: {e}")
            return False
    
    def run_complete_test(self):
        """Run the complete OAuth 2.1 flow test"""
        print("🚀 Starting OAuth 2.1 Flow Test")
        print("=" * 50)
        
        # Step 1: Test discovery
        if not self.test_discovery():
            return False
        
        print()
        
        # Step 2: Get client info
        client_info = self.get_client_info()
        if not client_info:
            return False
        
        print()
        
        # Step 3: Simulate authorization
        auth_code = self.simulate_authorization()
        if not auth_code:
            return False
        
        print()
        
        # Step 4: Exchange code for tokens
        tokens = self.exchange_code_for_tokens(auth_code)
        if not tokens:
            return False
        
        print()
        
        # Step 5: Test MCP request
        if not self.test_mcp_request():
            return False
        
        print()
        
        # Step 6: Test token introspection
        if not self.test_token_introspection():
            return False
        
        print()
        print("🎉 OAuth 2.1 Flow Test COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("✅ All OAuth 2.1 endpoints working correctly")
        print("✅ Token exchange working")
        print("✅ MCP authentication working")
        print("✅ Ready for client integration!")
        
        return True

if __name__ == "__main__":
    tester = MCPOAuthTester()
    success = tester.run_complete_test()
    
    if not success:
        print("❌ Test failed!")
        exit(1)
    else:
        print("✅ All tests passed!")
        exit(0)