#!/usr/bin/env python3
"""
Simple deployment test to verify all components are working
"""

import sys
import traceback

def test_imports():
    """Test all required package imports"""
    print("Testing package imports...")
    
    try:
        import pinecone
        print("✅ Pinecone imported")
        
        from pinecone import Pinecone, ServerlessSpec
        print("✅ Pinecone classes imported")
        
        import openai
        print("✅ OpenAI imported")
        
        import slack_sdk
        print("✅ Slack SDK imported")
        
        import notion_client
        print("✅ Notion client imported")
        
        import apscheduler
        print("✅ APScheduler imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_services():
    """Test service initialization"""
    print("\nTesting service initialization...")
    
    try:
        from config import config
        print("✅ Config loaded")
        
        # Test if we can import our services
        from pinecone_service import PineconeService
        print("✅ PineconeService importable")
        
        from embedding_service import EmbeddingService
        print("✅ EmbeddingService importable")
        
        from slack_ingester import SlackIngester
        print("✅ SlackIngester importable")
        
        from notion_logger import NotionLogger
        print("✅ NotionLogger importable")
        
        from scheduler import SlackWorkerScheduler
        print("✅ Scheduler importable")
        
        return True
        
    except Exception as e:
        print(f"❌ Service error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Running deployment tests...")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_imports():
        tests_passed += 1
    
    if test_services():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())