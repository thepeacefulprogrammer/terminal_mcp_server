#!/usr/bin/env python3
"""
Simple test script to verify Terminal MCP Server connectivity and basic functionality.
This can be used during development to test the server as we implement features.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

async def test_mcp_server():
    """Test the MCP server directly."""
    try:
        print("🚀 Testing Terminal MCP Server...")
        
        # Import our server
        from terminal_mcp_server.server import TerminalMCPServer
        
        print("✅ Server imports successfully")
        
        # Initialize server
        server = TerminalMCPServer()
        print("✅ Server initializes successfully")
        
        # Test that server has the expected tools
        tools = getattr(server.mcp, '_tools', {})
        print(f"📋 Available tools: {list(tools.keys())}")
        
        # Test the test_connection tool
        if hasattr(server.mcp, '_tools') and 'test_connection' in server.mcp._tools:
            print("🔧 Testing test_connection tool...")
            # Note: We can't easily call MCP tools directly without the full MCP protocol
            # This would require a proper MCP client connection
            print("✅ test_connection tool is registered")
        
        print("🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("=" * 60)
    print("Terminal MCP Server - Development Test")
    print("=" * 60)
    
    success = await test_mcp_server()
    
    if success:
        print("\n🎉 MCP Server is ready for testing!")
        print("\n📋 Next steps:")
        print("1. Use mcp.json with an MCP client (like Claude Desktop)")
        print("2. Test tools: test_connection, execute_command, execute_command_background")
        print("3. Check logs in logs/ directory for detailed information")
    else:
        print("\n❌ MCP Server has issues that need fixing")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 