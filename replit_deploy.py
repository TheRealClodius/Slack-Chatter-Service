#!/usr/bin/env python3
"""
Replit Deployment Script for Slack Chatter Service
This file makes it easy to deploy the ingestion worker on Replit
"""

import subprocess
import sys
import os
from pathlib import Path

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_CHANNELS", 
        "OPENAI_API_KEY",
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT",
        "NOTION_INTEGRATION_SECRET",
        "NOTION_DATABASE_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Add these in the Replit Secrets tab (🔒 icon)")
        return False
    
    print("✅ All environment variables configured!")
    return True

def install_dependencies():
    """Install dependencies if needed"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_ingestion_worker():
    """Start the ingestion worker"""
    print("🚀 Starting Slack Chatter Ingestion Worker...")
    print("=" * 60)
    print("🔄 This will run continuously to keep embeddings fresh")
    print("📊 Check logs below for ingestion progress")
    print("🛑 Press Ctrl+C to stop (but keep Always On enabled!)")
    print("=" * 60)
    
    try:
        subprocess.run([sys.executable, "main_orchestrator.py", "ingestion"])
    except KeyboardInterrupt:
        print("\n🛑 Ingestion worker stopped")
    except Exception as e:
        print(f"❌ Error running ingestion worker: {e}")

def main():
    """Main deployment function"""
    print("🚀 Slack Chatter Service - Replit Deployment")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("main_orchestrator.py").exists():
        print("❌ main_orchestrator.py not found!")
        print("Make sure you're running this from the project root directory")
        return
    
    # Check environment variables
    if not check_environment():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Start the worker
    start_ingestion_worker()

if __name__ == "__main__":
    main() 