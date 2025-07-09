#!/usr/bin/env python3
"""
Script to recreate Pinecone index for Slack Chatter Service
This will delete the existing index and create a new one with the correct specifications
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import config

async def recreate_pinecone_index():
    """Delete and recreate the Pinecone index"""
    
    print("🔄 Recreating Pinecone Index for Slack Chatter Service")
    print("=" * 60)
    
    try:
        from pinecone import Pinecone
        
        # Initialize Pinecone
        pc = Pinecone(api_key=config.pinecone_api_key)
        
        # Current index name
        current_index = config.pinecone_index_name
        print(f"Current index: {current_index}")
        
        # Check if index exists
        existing_indexes = [index.name for index in pc.list_indexes()]
        print(f"Existing indexes: {existing_indexes}")
        
        if current_index in existing_indexes:
            print(f"⚠️  Deleting existing index: {current_index}")
            pc.delete_index(current_index)
            print("✅ Index deleted successfully")
            
            # Wait for deletion to complete
            print("⏳ Waiting for deletion to complete...")
            import time
            time.sleep(10)
        else:
            print(f"ℹ️  Index {current_index} doesn't exist, creating new one")
        
        # Create new index with correct specifications
        print(f"🚀 Creating new index: {current_index}")
        print(f"📐 Dimensions: {config.embedding_dimensions}")
        print(f"🌍 Environment: {config.pinecone_environment}")
        
        pc.create_index(
            name=current_index,
            dimension=config.embedding_dimensions,  # 768 for text-embedding-3-small
            metric='cosine',  # Best for text embeddings
            spec={
                'serverless': {
                    'cloud': 'gcp',
                    'region': config.pinecone_environment  # europe-west4
                }
            }
        )
        
        print("✅ New index created successfully!")
        
        # Verify the new index
        print("🔍 Verifying new index...")
        time.sleep(5)  # Wait for index to be ready
        
        index_info = pc.describe_index(current_index)
        print(f"✅ Index verification:")
        print(f"   Name: {index_info.name}")
        print(f"   Dimension: {index_info.dimension}")
        print(f"   Metric: {index_info.metric}")
        print(f"   Status: {index_info.status.state}")
        
        # Test connection
        index = pc.Index(current_index)
        stats = index.describe_index_stats()
        print(f"   Vector count: {stats.total_vector_count}")
        print(f"   Index fullness: {stats.index_fullness}")
        
        print("🎉 Index recreation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error recreating index: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main entry point"""
    print("Current configuration:")
    print(f"  Index name: {config.pinecone_index_name}")
    print(f"  Environment: {config.pinecone_environment}")
    print(f"  Embedding dimensions: {config.embedding_dimensions}")
    print()
    
    # Confirm with user (for interactive use)
    if len(sys.argv) < 2 or sys.argv[1] != "--force":
        response = input("⚠️  This will DELETE the existing index. Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    success = await recreate_pinecone_index()
    
    if success:
        print("\n🚀 Ready to start ingesting Slack messages!")
        print("   Run: python main_orchestrator.py ingestion")
    else:
        print("\n❌ Index recreation failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())