"""
Main entry point for Slack Message Vector Search API
Runs FastAPI server with background worker for message ingestion
"""
import uvicorn
from api_server import app

if __name__ == "__main__":
    # Run FastAPI server with background worker
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5000,
        log_level="info"
    )
