"""
Main Orchestrator for Slack Chatter Service
Unified entry point that can run different modes:
- MCP Server: Provides search capabilities via MCP protocol
- HTTP MCP Server: Provides MCP capabilities over HTTP for remote access
- Ingestion Worker: Runs background ingestion of Slack messages
- Search Service: Standalone search service (for testing)
"""

import asyncio
import argparse
import sys
import logging
from typing import Optional

from lib.config import config
from search.service import create_search_service
from mcp.server import create_mcp_server, create_mcp_remote_server
# Removed LLM agent import - agents should be on client side


class SlackChatterOrchestrator:
    """Main orchestrator for the Slack Chatter Service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.search_service = None
# Removed search_agent - agents should be on client side
        self.mcp_server = None
    
    async def run_mcp_server(self):
        """Run the MCP server mode"""
        print("🚀 Starting MCP Server Mode")
        print("=" * 60)
        
        try:
            # Initialize search service only
            self.search_service = create_search_service()
            
            # Create MCP server with direct search service (no server-side agent)
            self.mcp_server = create_mcp_server(search_service=self.search_service)
            
            # Run the MCP server
            await self.mcp_server.run()
            
        except Exception as e:
            self.logger.error(f"MCP server failed: {str(e)}")
            sys.exit(1)
    
    async def run_mcp_remote_server(self):
        """Run MCP Streamable HTTP server (March 2025 Standard)"""
        print("🚀 Starting MCP Streamable HTTP Server")
        print("=" * 60)
        print("🔄 Single endpoint supporting GET & POST")
        print("🆔 Session management via headers (mcp-session-id)")
        print("🌐 MCP Streamable HTTP Standard (March 2025)")
        print("=" * 60)
        
        try:
            # Initialize search service only
            print("🔧 Initializing search service...")
            self.search_service = create_search_service()
            print("✅ Search service initialized")
            
            # Import and configure the FastAPI app
            print("📦 Loading FastAPI application...")
            from mcp.fastapi_app import app, set_search_service
            import uvicorn
            
            # Set the search service for the MCP remote server
            print("🔗 Connecting search service to MCP server...")
            set_search_service(self.search_service)
            print("✅ Search service connected")
            
            # Get port from environment or use 5000 for Replit
            import os
            port = int(os.getenv('PORT', 5000))
            
            self.logger.info(f"Starting MCP Remote Protocol server on port {port}...")
            print(f"🔒 OAuth Discovery: http://0.0.0.0:{port}/.well-known/oauth-authorization-server")
            print(f"🔑 Authorization: http://0.0.0.0:{port}/oauth/authorize")
            print(f"🎟️  Token: http://0.0.0.0:{port}/oauth/token")
            print(f"⚡ MCP SSE: http://0.0.0.0:{port}/mcp/sse")
            print(f"📡 MCP Request: http://0.0.0.0:{port}/mcp/request")
            print(f"👤 Session Info: http://0.0.0.0:{port}/mcp/session")
            print(f"❤️  Health Check: http://0.0.0.0:{port}/health")
            print(f"🐛 Debug OAuth: http://0.0.0.0:{port}/debug/oauth-clients")
            print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
            
            # Run the server with uvicorn.run instead of asyncio.run to avoid event loop conflict
            print(f"🚀 Starting uvicorn server on 0.0.0.0:{port}...")
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info",
                access_log=True,
                loop="asyncio"
            )
            
        except ImportError as e:
            self.logger.error(f"Missing dependency: {str(e)}")
            print(f"❌ Missing dependency: {str(e)}")
            print("💡 Try running: python3 -m pip install fastapi uvicorn sse-starlette")
            sys.exit(1)
        except OSError as e:
            if "Address already in use" in str(e):
                self.logger.error(f"Port {port} is already in use")
                print(f"❌ Port {port} is already in use")
                print("💡 Try stopping other services or use a different port")
            else:
                self.logger.error(f"Network error: {str(e)}")
                print(f"❌ Network error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"MCP Remote Protocol server failed: {str(e)}")
            print(f"❌ Server startup failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def run_mcp_remote_server_sync(self):
        """Synchronous wrapper for running MCP Remote Protocol server"""
        print("🚀 Starting MCP Remote Protocol Server")
        print("=" * 60)
        print("🔒 OAuth 2.1 authentication enabled")
        print("⚡ Server-Sent Events (SSE) communication")
        print("🌐 Official MCP Remote Protocol implementation")
        print("=" * 60)
        
        try:
            # Initialize search service only
            print("🔧 Initializing search service...")
            self.search_service = create_search_service()
            print("✅ Search service initialized")
            
            # Import and configure the FastAPI app
            print("📦 Loading FastAPI application...")
            from mcp.fastapi_app import app, set_search_service
            import uvicorn
            
            # Set the search service for the MCP remote server
            print("🔗 Connecting search service to MCP server...")
            set_search_service(self.search_service)
            print("✅ Search service connected")
            
            # Get port from environment or use 5000 for Replit
            import os
            port = int(os.getenv('PORT', 5000))
            
            self.logger.info(f"Starting MCP Remote Protocol server on port {port}...")
            print(f"🔒 OAuth Discovery: http://0.0.0.0:{port}/.well-known/oauth-authorization-server")
            print(f"🔑 Authorization: http://0.0.0.0:{port}/oauth/authorize")
            print(f"🎟️  Token: http://0.0.0.0:{port}/oauth/token")
            print(f"⚡ MCP SSE: http://0.0.0.0:{port}/mcp/sse")
            print(f"📡 MCP Request: http://0.0.0.0:{port}/mcp/request")
            print(f"👤 Session Info: http://0.0.0.0:{port}/mcp/session")
            print(f"❤️  Health Check: http://0.0.0.0:{port}/health")
            print(f"🐛 Debug OAuth: http://0.0.0.0:{port}/debug/oauth-clients")
            print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
            
            # Run the server synchronously (no asyncio.run conflicts)
            print(f"🚀 Starting uvicorn server on 0.0.0.0:{port}...")
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=port,
                log_level="debug",
                access_log=True
            )
            
        except ImportError as e:
            self.logger.error(f"Missing dependency: {str(e)}")
            print(f"❌ Missing dependency: {str(e)}")
            print("💡 Try running: python3 -m pip install fastapi uvicorn sse-starlette")
            sys.exit(1)
        except OSError as e:
            if "Address already in use" in str(e):
                self.logger.error(f"Port {port} is already in use")
                print(f"❌ Port {port} is already in use")
                print("💡 Try stopping other services or use a different port")
            else:
                self.logger.error(f"Network error: {str(e)}")
                print(f"❌ Network error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"MCP Remote Protocol server failed: {str(e)}")
            print(f"❌ Server startup failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    async def run_ingestion_worker(self):
        """Run the ingestion worker mode"""
        print("🚀 Starting Ingestion Worker Mode")
        print("=" * 60)
        
        try:
            # Import here to avoid circular imports
            from ingestion.worker import SlackIngestionWorker
            
            worker = SlackIngestionWorker()
            await worker.start()
            
        except Exception as e:
            self.logger.error(f"Ingestion worker failed: {str(e)}")
            sys.exit(1)
    
    async def run_search_service(self):
        """Run standalone search service (for testing)"""
        print("🚀 Starting Search Service Test Mode")
        print("=" * 60)
        
        try:
            # Initialize search service only
            self.search_service = create_search_service()
            
            # Test the search service
            await self._test_search_service()
            
        except Exception as e:
            self.logger.error(f"Search service test failed: {str(e)}")
            sys.exit(1)
    
    async def _test_search_service(self):
        """Test the search service with sample queries"""
        print("Testing search service...")
        
        # Test health check
        health = await self.search_service.health_check()
        print(f"Health check: {health}")
        
        # Test stats
        stats = await self.search_service.get_stats()
        print(f"Stats: {stats}")
        
        # Test channels
        channels = await self.search_service.get_channels()
        print(f"Channels: {channels}")
        
        # Test direct search (no server-side agent)
        if stats.get("total_vectors", 0) > 0:
            test_queries = [
                "deployment issues",
                "error authentication",
                "how to configure database",
                "urgent production problem"
            ]
            
            for query in test_queries:
                print(f"\nTesting query: '{query}'")
                
                # Perform direct search (no agent enhancement on server)
                results = await self.search_service.search(query=query, top_k=10)
                print(f"Found {len(results)} results")
                
                # Show first result
                if results:
                    first_result = results[0]
                    print(f"  Top result: {first_result.text[:100]}...")
                    print(f"  Channel: #{first_result.channel_name}")
                    print(f"  User: @{first_result.user_name}")
                    print(f"  Score: {first_result.similarity_score:.3f}")
        else:
            print("No vectors found in index. Run ingestion worker first.")
    
    async def run_combined_mode(self):
        """Run both ingestion worker and MCP server together"""
        print("🚀 Starting Combined Mode (Ingestion + MCP Server)")
        print("=" * 60)
        
        try:
            # Start ingestion worker in background
            from ingestion.worker import SlackIngestionWorker
            
            ingestion_worker = SlackIngestionWorker()
            ingestion_task = asyncio.create_task(ingestion_worker.start())
            
            # Give the ingestion worker time to start
            await asyncio.sleep(2)
            
            # Start MCP server
            await self.run_mcp_server()
            
        except Exception as e:
            self.logger.error(f"Combined mode failed: {str(e)}")
            sys.exit(1)


# Removed EnhancedSearchService - agents belong on client side, not server side


def create_argument_parser():
    """Create argument parser for command-line options"""
    parser = argparse.ArgumentParser(
        description="Slack Chatter Service - Unified entry point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mcp                    # Run MCP server (stdio)
  %(prog)s remote                 # Run MCP Remote Protocol server (OAuth 2.1 + SSE)
  %(prog)s ingestion              # Run ingestion worker
  %(prog)s search                 # Test search service
  %(prog)s combined               # Run both ingestion and MCP server
  %(prog)s remote --log-level debug # Run remote server with debug logging
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["mcp", "remote", "ingestion", "search", "combined"],
        help="Mode to run the service in"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    parser.add_argument(
        "--agent-info",
        action="store_true",
        help="Show AI search agent information and exit"
    )
    
    return parser


def setup_logging(log_level: str):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Show agent info if requested
    if args.agent_info:
        print("🤖 AI Search Agent Information")
        print("=" * 40)
        print("Agent Type: LLM-Powered")
        try:
            # Load YAML config directly for agent info (bypass OpenAI client init)
            import yaml
            import os
            yaml_path = os.path.join(os.path.dirname(__file__), "agent_prompt.yaml")
            
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                agent_info = config_data.get("agent", {})
                model_config = config_data.get("model", {})
                cost_info = config_data.get("cost", {})
                
                print(f"Agent: {agent_info.get('name', 'Vector Search Specialist')}")
                print(f"Version: {agent_info.get('version', '1.0.0')}")
                print(f"Model: {model_config.get('name', 'gpt-4o-mini')}")
                print(f"Temperature: {model_config.get('temperature', 0.1)}")
                print(f"Max Tokens: {model_config.get('max_tokens', 4000)}")
                print(f"Cost: ~${cost_info.get('per_query_usd', 0.001)} per query")
                print()
                print("📋 Configuration Source: agent_prompt.yaml")
                print("🎯 Capabilities:")
                print("  🔍 Vector Search Mastery")
                print("  🎯 Advanced Intent Analysis")
                print("  📊 Smart Entity Extraction")
                print("  🧠 Semantic Query Expansion")
                print("  ⚡ Dynamic Parameter Optimization")
                print("  🚨 Priority Intelligence")
                print()
                print("💡 Prompt Engineering:")
                print("  • Edit agent_prompt.yaml to customize behavior")
                print("  • No code changes needed for prompt modifications")
                print("  • Runtime loading of updated prompts")
            else:
                print("❌ agent_prompt.yaml not found")
                print("Model: GPT-4o-mini (default)")
                print("Cost: ~$0.001 per search query")
        except Exception as e:
            print(f"❌ Error loading agent config: {e}")
            print("Model: GPT-4o-mini (default)")
            print("Cost: ~$0.001 per search query")
        print("OpenAI Key: Uses same key as embeddings")
        sys.exit(0)
    
    # Validate configuration if requested
    if args.validate_config:
        try:
            config._validate_config()
            print("✅ Configuration is valid")
            sys.exit(0)
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
    
    # Create orchestrator
    orchestrator = SlackChatterOrchestrator()
    
    # Handle remote mode synchronously (no asyncio.run needed)
    if args.mode == "remote":
        orchestrator.run_mcp_remote_server_sync()
        return
    
    # All other modes run with asyncio
    async def run_async_mode():
        if args.mode == "mcp":
            await orchestrator.run_mcp_server()
        elif args.mode == "ingestion":
            await orchestrator.run_ingestion_worker()
        elif args.mode == "search":
            await orchestrator.run_search_service()
        elif args.mode == "combined":
            await orchestrator.run_combined_mode()
        else:
            print(f"Unknown mode: {args.mode}")
            sys.exit(1)
    
    # Run async modes with asyncio.run
    asyncio.run(run_async_mode())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 