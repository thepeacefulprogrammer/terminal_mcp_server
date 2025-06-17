#!/usr/bin/env python3
"""Debug script to test tool registration"""

import sys
import os
sys.path.insert(0, 'src')

from terminal_mcp_server.handlers.python_handlers import PythonHandlers

def main():
    print("Testing PythonHandlers tool registration...")
    
    try:
        handler = PythonHandlers()
        print("✓ PythonHandlers created successfully")
    except Exception as e:
        print(f"✗ Failed to create PythonHandlers: {e}")
        return
    
    class MockMCPServer:
        def __init__(self):
            self.tools = []
            
        def tool(self):
            def decorator(func):
                self.tools.append(func.__name__)
                print(f"✓ Registered tool: {func.__name__}")
                return func
            return decorator
    
    try:
        mock_server = MockMCPServer()
        handler.register_tools(mock_server)
        print(f"\n✓ Total tools registered: {len(mock_server.tools)}")
        print("✓ Registered tools:")
        for tool in mock_server.tools:
            print(f"  - {tool}")
            
        # Check specifically for the streaming script tool
        if "execute_python_script_with_streaming" in mock_server.tools:
            print("\n✓ execute_python_script_with_streaming is registered!")
        else:
            print("\n✗ execute_python_script_with_streaming is NOT registered!")
            
    except Exception as e:
        print(f"✗ Failed during tool registration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 