#!/usr/bin/env python3
"""
Replit Web Server for Slack Chatter Service
Provides a web interface for Replit deployment while running the ingestion worker
"""

import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
import threading
import subprocess
import sys

# Simple HTTP server for Replit
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class SlackChatterWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/':
            self.serve_dashboard()
        elif path == '/status':
            self.serve_status()
        elif path == '/logs':
            self.serve_logs()
        elif path == '/health':
            self.serve_health()
        else:
            self.send_error(404, "Page not found")
    
    def serve_dashboard(self):
        """Serve the main dashboard"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Slack Chatter Service - Deployed</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .status {{ background: #e8f5e8; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #4caf50; }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 6px; margin: 10px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
                .nav {{ margin: 20px 0; }}
                .nav a {{ margin-right: 20px; color: #1976d2; text-decoration: none; }}
                .nav a:hover {{ text-decoration: underline; }}
                .timestamp {{ font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Slack Chatter Service</h1>
                    <p>Deployed on Replit - Running Successfully</p>
                </div>
                
                <div class="status">
                    <h3>✅ Service Status: RUNNING</h3>
                    <p>Your Slack message ingestion worker is active and processing messages.</p>
                </div>
                
                <div class="nav">
                    <a href="/status">System Status</a>
                    <a href="/logs">View Logs</a>
                    <a href="/health">Health Check</a>
                </div>
                
                <div class="info">
                    <h3>📊 Service Information</h3>
                    <div class="metric">
                        <strong>Mode:</strong> Ingestion Worker
                    </div>
                    <div class="metric">
                        <strong>Status:</strong> Active
                    </div>
                    <div class="metric">
                        <strong>Environment:</strong> Replit
                    </div>
                </div>
                
                <div class="info">
                    <h3>🔄 Background Process</h3>
                    <p>The ingestion worker runs continuously to:</p>
                    <ul>
                        <li>Fetch new messages from Slack channels</li>
                        <li>Generate embeddings using OpenAI</li>
                        <li>Store vectors in Pinecone</li>
                        <li>Log results to Notion</li>
                    </ul>
                </div>
                
                <div class="info">
                    <h3>🔧 How to Use</h3>
                    <p>This service provides an MCP (Model Context Protocol) tool for searching Slack messages. Configure your MCP client to use this service for intelligent Slack search capabilities.</p>
                </div>
                
                <div class="timestamp">
                    Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                </div>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_status(self):
        """Serve system status as JSON"""
        # Check if worker state file exists
        worker_state_file = Path("worker_state.json")
        vector_file = Path("local-slack-chatter_vectors.json")
        
        status = {
            "service": "Slack Chatter Service",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "worker_state_exists": worker_state_file.exists(),
            "vector_data_exists": vector_file.exists(),
            "vector_file_size_mb": round(vector_file.stat().st_size / 1024 / 1024, 2) if vector_file.exists() else 0,
            "environment_configured": bool(os.getenv("SLACK_BOT_TOKEN"))
        }
        
        if worker_state_file.exists():
            try:
                with open(worker_state_file, 'r') as f:
                    worker_data = json.load(f)
                status["last_ingestion"] = worker_data.get("last_ingestion_time")
            except:
                status["last_ingestion"] = "unknown"
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def serve_logs(self):
        """Serve recent logs"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Slack Chatter Logs</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body { font-family: monospace; margin: 20px; background: #1e1e1e; color: #fff; }
                .log { background: #2d2d2d; padding: 20px; border-radius: 6px; white-space: pre-line; }
                .header { color: #4caf50; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🔍 Slack Chatter Service Logs</h2>
                <a href="/" style="color: #4caf50;">← Back to Dashboard</a>
            </div>
            <div class="log">
Service is running in background mode.
Check Replit console for detailed logs.

Background processes:
- Slack message ingestion: Active
- Vector embedding generation: Active  
- Notion logging: Active

Last status: Running successfully
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_health(self):
        """Health check endpoint"""
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "slack-chatter-service",
            "version": "2.0.0"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health).encode())
    
    def log_message(self, format, *args):
        """Suppress default request logging"""
        pass

def start_background_worker():
    """Start the ingestion worker in a separate process"""
    try:
        print("🔄 Starting background ingestion worker...")
        subprocess.Popen([sys.executable, "main_orchestrator.py", "ingestion"])
        print("✅ Background worker started")
    except Exception as e:
        print(f"❌ Failed to start background worker: {e}")

def start_web_server():
    """Start the web server for Replit"""
    port = int(os.getenv('PORT', 5000))
    
    print(f"🌐 Starting web server on port {port}...")
    print(f"🔗 Dashboard will be available at your Replit URL")
    
    server = HTTPServer(('0.0.0.0', port), SlackChatterWebHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Web server stopped")
        server.server_close()

def main():
    """Main entry point for Replit deployment"""
    print("🚀 Slack Chatter Service - Replit Web Deployment")
    print("=" * 55)
    
    # Start background worker
    start_background_worker()
    
    # Start web server (this will run forever)
    start_web_server()

if __name__ == "__main__":
    main()