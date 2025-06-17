#!/usr/bin/env python3
"""Test script to debug streaming tool registration issues"""

import sys
import os
import traceback
sys.path.insert(0, 'src')

from terminal_mcp_server.handlers.python_handlers import PythonHandlers

def main():
    print("Testing streaming tool registration in detail...")
    
    try:
        handler = PythonHandlers()
        print("✓ PythonHandlers created successfully")
    except Exception as e:
        print(f"✗ Failed to create PythonHandlers: {e}")
        traceback.print_exc()
        return
    
    class MockMCPServer:
        def __init__(self):
            self.tools = {}
            
        def tool(self):
            def decorator(func):
                tool_name = func.__name__
                print(f"  Attempting to register: {tool_name}")
                try:
                    # Store the function
                    self.tools[tool_name] = func
                    print(f"  ✓ Successfully registered: {tool_name}")
                    return func
                except Exception as e:
                    print(f"  ✗ Failed to register {tool_name}: {e}")
                    traceback.print_exc()
                    return func
            return decorator
    
    try:
        mock_server = MockMCPServer()
        print("\nStarting tool registration...")
        handler.register_tools(mock_server)
        
        print(f"\n✓ Total tools registered: {len(mock_server.tools)}")
        print("✓ Registered tools:")
        for tool_name in mock_server.tools.keys():
            print(f"  - {tool_name}")
            
        # Test specifically for the streaming script tool
        if "execute_python_script_with_streaming" in mock_server.tools:
            print("\n✓ execute_python_script_with_streaming is registered!")
            
            # Try to call the tool function to see if it works
            print("Testing the tool function...")
            tool_func = mock_server.tools["execute_python_script_with_streaming"]
            try:
                # This should fail because we need async context, but we can see if there are other errors
                print("Tool function signature:", tool_func.__code__.co_varnames[:tool_func.__code__.co_argcount])
                print("Tool function annotations:", getattr(tool_func, '__annotations__', {}))
                print("✓ Tool function is callable")
            except Exception as e:
                print(f"✗ Tool function has issues: {e}")
                traceback.print_exc()
        else:
            print("\n✗ execute_python_script_with_streaming is NOT registered!")
            
    except Exception as e:
        print(f"✗ Failed during tool registration: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 