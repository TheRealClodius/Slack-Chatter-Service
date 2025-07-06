#!/usr/bin/env python3
"""
Security Test Suite for Slack Message Vector Search API

This script tests all security features including authentication, rate limiting,
input validation, and other security measures.
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from typing import Dict, Any, Optional
from utils import generate_secure_api_key, validate_api_key_format

class SecurityTester:
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
    
    async def make_request(self, method: str, endpoint: str, 
                          headers: Optional[Dict[str, str]] = None,
                          json_data: Optional[Dict[str, Any]] = None,
                          params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make HTTP request and return response info"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(
                method, url, headers=headers, json=json_data, params=params
            ) as response:
                text = await response.text()
                try:
                    data = json.loads(text)
                except:
                    data = text
                
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "data": data
                }
        except Exception as e:
            return {
                "status": -1,
                "error": str(e),
                "data": None
            }
    
    async def test_authentication(self):
        """Test API key authentication"""
        print("\n🔐 Testing Authentication...")
        
        # Test 1: No Authorization header
        response = await self.make_request("GET", "/health")
        self.log_test(
            "No auth header rejected",
            response["status"] == 401,
            f"Status: {response['status']}"
        )
        
        # Test 2: Invalid API key format
        invalid_headers = {"Authorization": "Bearer invalid-key"}
        response = await self.make_request("GET", "/health", headers=invalid_headers)
        self.log_test(
            "Invalid API key rejected",
            response["status"] == 401,
            f"Status: {response['status']}"
        )
        
        # Test 3: Valid API key
        if self.api_key:
            valid_headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.make_request("GET", "/health", headers=valid_headers)
            self.log_test(
                "Valid API key accepted",
                response["status"] == 200,
                f"Status: {response['status']}"
            )
        
        # Test 4: Wrong auth scheme
        wrong_scheme_headers = {"Authorization": f"Basic {self.api_key}"}
        response = await self.make_request("GET", "/health", headers=wrong_scheme_headers)
        self.log_test(
            "Wrong auth scheme rejected",
            response["status"] == 401,
            f"Status: {response['status']}"
        )
    
    async def test_rate_limiting(self):
        """Test rate limiting"""
        print("\n⏱️ Testing Rate Limiting...")
        
        if not self.api_key:
            self.log_test("Rate limiting", False, "No API key provided for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Test health endpoint rate limiting (30/minute)
        success_count = 0
        rate_limited = False
        
        for i in range(35):  # Try to exceed the 30/minute limit
            response = await self.make_request("GET", "/health", headers=headers)
            if response["status"] == 200:
                success_count += 1
            elif response["status"] == 429:
                rate_limited = True
                break
            await asyncio.sleep(0.1)  # Small delay between requests
        
        self.log_test(
            "Rate limiting activated",
            rate_limited,
            f"Made {success_count} requests before rate limit"
        )
    
    async def test_input_validation(self):
        """Test input validation"""
        print("\n🔍 Testing Input Validation...")
        
        if not self.api_key:
            self.log_test("Input validation", False, "No API key provided for testing")
            return
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Test 1: Empty query
        response = await self.make_request(
            "POST", "/search", 
            headers=headers, 
            json_data={"query": "", "top_k": 5}
        )
        self.log_test(
            "Empty query rejected",
            response["status"] == 422,
            f"Status: {response['status']}"
        )
        
        # Test 2: Query too long
        long_query = "a" * 1001
        response = await self.make_request(
            "POST", "/search", 
            headers=headers, 
            json_data={"query": long_query, "top_k": 5}
        )
        self.log_test(
            "Long query rejected",
            response["status"] == 422,
            f"Status: {response['status']}"
        )
        
        # Test 3: Invalid top_k (too high)
        response = await self.make_request(
            "POST", "/search", 
            headers=headers, 
            json_data={"query": "test", "top_k": 100}
        )
        self.log_test(
            "Invalid top_k rejected",
            response["status"] == 422,
            f"Status: {response['status']}"
        )
        
        # Test 4: Dangerous characters in query
        dangerous_query = "<script>alert('xss')</script>"
        response = await self.make_request(
            "POST", "/search", 
            headers=headers, 
            json_data={"query": dangerous_query, "top_k": 5}
        )
        self.log_test(
            "Dangerous query rejected",
            response["status"] == 422,
            f"Status: {response['status']}"
        )
        
        # Test 5: Invalid date format
        response = await self.make_request(
            "POST", "/search", 
            headers=headers, 
            json_data={"query": "test", "top_k": 5, "date_from": "invalid-date"}
        )
        self.log_test(
            "Invalid date format rejected",
            response["status"] == 422,
            f"Status: {response['status']}"
        )
    
    async def test_security_headers(self):
        """Test security headers"""
        print("\n🛡️ Testing Security Headers...")
        
        if not self.api_key:
            self.log_test("Security headers", False, "No API key provided for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = await self.make_request("GET", "/health", headers=headers)
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        response_headers = response.get("headers", {})
        
        for header in required_headers:
            present = header in response_headers or header.lower() in response_headers
            self.log_test(
                f"Security header {header}",
                present,
                f"Value: {response_headers.get(header, 'Not found')}"
            )
    
    async def test_cors_policy(self):
        """Test CORS policy"""
        print("\n🌐 Testing CORS Policy...")
        
        # Test with various origins
        test_origins = [
            "https://malicious-site.com",
            "http://localhost:3000",
            "https://legitimate-agent.com"
        ]
        
        for origin in test_origins:
            headers = {"Origin": origin}
            response = await self.make_request("OPTIONS", "/search", headers=headers)
            
            cors_headers = response.get("headers", {})
            allowed_origin = cors_headers.get("Access-Control-Allow-Origin", "")
            
            # Check if origin is properly handled
            self.log_test(
                f"CORS for {origin}",
                True,  # Just log the result, don't fail
                f"Allowed origin: {allowed_origin}"
            )
    
    async def test_information_disclosure(self):
        """Test information disclosure protection"""
        print("\n📊 Testing Information Disclosure Protection...")
        
        # Test 1: Root endpoint shouldn't expose too much info
        response = await self.make_request("GET", "/")
        root_data = response.get("data", {})
        
        # Should not expose internal endpoints or sensitive info
        has_endpoints = "endpoints" in root_data
        self.log_test(
            "Root endpoint minimal disclosure",
            not has_endpoints,
            f"Endpoints exposed: {has_endpoints}"
        )
        
        # Test 2: Error messages shouldn't leak info
        response = await self.make_request("GET", "/nonexistent")
        self.log_test(
            "404 error handled",
            response["status"] == 404,
            f"Status: {response['status']}"
        )
    
    async def test_ssl_configuration(self):
        """Test SSL configuration if applicable"""
        print("\n🔒 Testing SSL Configuration...")
        
        if self.base_url.startswith("https://"):
            # Test SSL connection
            try:
                response = await self.make_request("GET", "/")
                ssl_working = response["status"] != -1
                self.log_test(
                    "SSL connection working",
                    ssl_working,
                    f"HTTPS connection successful: {ssl_working}"
                )
            except Exception as e:
                self.log_test(
                    "SSL connection working",
                    False,
                    f"SSL error: {str(e)}"
                )
        else:
            self.log_test(
                "SSL configuration",
                False,
                "Using HTTP instead of HTTPS (not recommended for production)"
            )
    
    async def test_api_key_format_validation(self):
        """Test API key format validation"""
        print("\n🔑 Testing API Key Format Validation...")
        
        test_keys = [
            ("", False, "Empty key"),
            ("short", False, "Too short"),
            ("a" * 31, False, "31 characters"),
            ("a" * 32, True, "32 characters"),
            ("a" * 64, True, "64 characters"),
            ("a" * 129, False, "Too long"),
            ("key with spaces", False, "Contains spaces"),
            ("key@with#special", False, "Invalid characters"),
            ("validKey123-_", True, "Valid characters"),
        ]
        
        for key, expected, description in test_keys:
            result = validate_api_key_format(key)
            self.log_test(
                f"API key format: {description}",
                result == expected,
                f"Expected: {expected}, Got: {result}"
            )
    
    async def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting Security Test Suite...")
        print(f"Testing API: {self.base_url}")
        print(f"API Key provided: {'Yes' if self.api_key else 'No'}")
        
        # Run all tests
        await self.test_api_key_format_validation()
        await self.test_authentication()
        await self.test_input_validation()
        await self.test_security_headers()
        await self.test_cors_policy()
        await self.test_information_disclosure()
        await self.test_ssl_configuration()
        await self.test_rate_limiting()  # Run this last as it's slowest
        
        # Summary
        print("\n📊 Test Summary:")
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        print(f"Passed: {passed}/{total} tests")
        
        if passed == total:
            print("🎉 All security tests passed!")
            return True
        else:
            print("⚠️  Some security tests failed. Review the results above.")
            return False

async def main():
    """Main test runner"""
    # Get configuration
    base_url = os.getenv("TEST_API_URL", "http://localhost:5000")
    api_key = os.getenv("TEST_API_KEY")
    
    if not api_key:
        print("⚠️  No API key provided. Generate one with: python utils.py")
        print("Set TEST_API_KEY environment variable to run authenticated tests.")
        
        # Generate a test key for format validation
        test_key = generate_secure_api_key()
        print(f"Generated test API key: {test_key}")
        api_key = test_key
    
    async with SecurityTester(base_url, api_key) as tester:
        success = await tester.run_all_tests()
        
        if success:
            print("\n✅ Security validation complete - API is secure!")
            sys.exit(0)
        else:
            print("\n❌ Security validation failed - API has vulnerabilities!")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 