#!/usr/bin/env python3
"""
Test script to verify our MCP server is working locally
and provide the correct remote connection details
"""

import requests
import json
import os

def test_mcp_server():
    print("Testing MCP Server Authentication")
    print("=" * 50)
    
    # Current API key from logs
    api_key = "mcp_key_6HyB54aY8oWoSADOOldYWo5sXMuZxK5DhYtraJMEqFU"
    
    # Test local server
    local_url = "http://localhost:5000"
    
    try:
        print(f"Testing local server at {local_url}")
        
        # Test root endpoint
        response = requests.get(f"{local_url}/", timeout=5)
        print(f"Root endpoint: {response.status_code}")
        
        if response.status_code == 200:
            # Test MCP authentication
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            init_request = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'initialize',
                'params': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {},
                    'clientInfo': {
                        'name': 'local-test-client',
                        'version': '1.0.0'
                    }
                }
            }
            
            response = requests.post(f"{local_url}/mcp", json=init_request, headers=headers, timeout=5)
            print(f"MCP initialize: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'session_info' in result:
                    session_id = result['session_info']['session_id']
                    print(f"✅ Authentication SUCCESS")
                    print(f"Session ID: {session_id}")
                    
                    # Test tools/list
                    headers['Mcp-Session-Id'] = session_id
                    tools_request = {
                        'jsonrpc': '2.0',
                        'id': 2,
                        'method': 'tools/list',
                        'params': {}
                    }
                    
                    response = requests.post(f"{local_url}/mcp", json=tools_request, headers=headers, timeout=5)
                    if response.status_code == 200:
                        tools_result = response.json()
                        if 'result' in tools_result and 'tools' in tools_result['result']:
                            tools = tools_result['result']['tools']
                            print(f"Available tools: {len(tools)}")
                            for tool in tools:
                                print(f"  - {tool['name']}")
                else:
                    print("❌ No session info in response")
                    print(f"Response: {response.text}")
            else:
                print("❌ MCP authentication failed")
                print(f"Response: {response.text}")
        else:
            print(f"❌ Server not responding: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    print("\n" + "=" * 50)
    print("DEPLOYMENT INFORMATION")
    print("=" * 50)
    
    # Get replit environment info
    repl_slug = os.environ.get('REPL_SLUG', 'unknown-repl')
    repl_owner = os.environ.get('REPL_OWNER', 'unknown-owner')
    
    print(f"Current Replit App: {repl_slug}")
    print(f"Owner: {repl_owner}")
    print(f"Expected URL: https://{repl_slug}.{repl_owner}.replit.app")
    print(f"MCP Endpoint: https://{repl_slug}.{repl_owner}.replit.app/mcp")
    print(f"API Key: {api_key}")
    
    print("\n❌ WRONG URL: https://slack-chronicler-andreiclodius.replit.app")
    print("✅ CORRECT URL: Use the Expected URL above")

if __name__ == "__main__":
    test_mcp_server()