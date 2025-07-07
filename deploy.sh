#!/bin/bash

# Slack Chatter Service - Quick Deployment Script

set -e

echo "🚀 Slack Chatter Service Deployment"
echo "=================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your credentials:"
    echo ""
    echo "SLACK_BOT_TOKEN=xoxb-your-token-here"
    echo "SLACK_CHANNELS=C1234567890,C0987654321"
    echo "OPENAI_API_KEY=sk-your-key-here"
    echo "PINECONE_API_KEY=your-key-here"
    echo "PINECONE_ENVIRONMENT=your-env-here"
    echo "PINECONE_INDEX_NAME=slack-messages"
    echo "NOTION_INTEGRATION_SECRET=secret_your-secret-here"
    echo "NOTION_DATABASE_ID=your-database-id-here"
    echo ""
    echo "See DEPLOYMENT_GUIDE.md for more details."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Found .env file"
echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Ask for deployment type
echo "Choose deployment option:"
echo "1. Local development (stops on exit)"
echo "2. Production deployment (runs in background)"
echo ""
read -p "Enter choice (1-2): " choice

case $choice in
    1)
        echo "🔧 Starting local development deployment..."
        docker-compose up --build
        ;;
    2)
        echo "🚀 Starting production deployment..."
        docker-compose up -d --build
        
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        echo "📊 Check status:"
        echo "  docker-compose ps"
        echo ""
        echo "📝 View logs:"
        echo "  docker-compose logs -f slack-ingestion-worker"
        echo ""
        echo "🛑 Stop deployment:"
        echo "  docker-compose down"
        echo ""
        echo "🔄 Restart deployment:"
        echo "  docker-compose restart"
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac 