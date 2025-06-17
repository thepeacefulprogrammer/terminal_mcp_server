#!/usr/bin/env python3
"""
MCP Client Verification Tool

This script verifies that all 21 terminal MCP server tools are accessible
from different MCP clients and provides debugging information for client-specific issues.
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# List of all expected MCP tools
EXPECTED_TOOLS = [
    "test_connection",
    "execute_command", 
    "execute_command_background",
    "list_background_processes",
    "get_process_status", 
    "kill_background_process",
    "restart_background_process",
    "get_process_output",
    "execute_python_script",
    "execute_python_code",
    "execute_python_script_with_streaming",
    "execute_python_code_with_streaming",
    "list_virtual_environments",
    "activate_virtual_environment", 
    "create_virtual_environment",
    "install_python_package",
    "install_dependencies",
    "get_current_directory",
    "change_directory",
    "get_environment_variables",
    "set_environment_variable"
]

# Client compatibility requirements
CLIENT_COMPATIBILITY_CHECKLIST = {
    "tool_registration": "All 21 tools must be registered with @mcp_server.tool() decorator",
    "response_format": "All tools must return JSON strings for client compatibility", 
    "error_handling": "All tools must return valid JSON even on errors",
    "parameter_validation": "All tools must validate parameters and provide clear error messages",
    "docstring_format": "All tools must have proper docstrings with Args and Returns sections",
    "async_compatibility": "All tools must be async functions for MCP client compatibility"
}


class MCPClientVerifier:
    """Verifies MCP client compatibility and tool accessibility."""
    
    def __init__(self):
        """Initialize the verifier."""
        self.verification_results = {}
        self.errors = []
        
    async def verify_tool_registration(self) -> Dict[str, Any]:
        """Verify that all tools are properly registered."""
        logger.info("Verifying tool registration...")
        
        try:
            # Import and check handlers
            from terminal_mcp_server.handlers import (
                command_handlers,
                process_handlers,
                python_handlers,
                environment_handlers,
            )
            
            # Create mock server to capture registrations
            registered_tools = []
            
            class MockServer:
                def tool(self):
                    def decorator(func):
                        registered_tools.append(func.__name__)
                        return func
                    return decorator
            
            mock_server = MockServer()
            
            # Register all tools
            command_handlers.register_tools(mock_server)
            process_handlers.register_tools(mock_server)
            python_handlers.register_tools(mock_server)
            environment_handlers.register_tools(mock_server)
            
            # Check registration results
            missing_tools = [tool for tool in EXPECTED_TOOLS[1:] if tool not in registered_tools]  # Skip test_connection
            extra_tools = [tool for tool in registered_tools if tool not in EXPECTED_TOOLS[1:]]
            
            result = {
                "total_registered": len(registered_tools),
                "expected_count": len(EXPECTED_TOOLS) - 1,  # Exclude test_connection from handlers
                "registered_tools": registered_tools,
                "missing_tools": missing_tools,
                "extra_tools": extra_tools,
                "success": len(missing_tools) == 0 and len(registered_tools) == 20
            }
            
            logger.info(f"Tool registration verification: {result['success']}")
            if missing_tools:
                logger.error(f"Missing tools: {missing_tools}")
            if extra_tools:
                logger.warning(f"Extra tools: {extra_tools}")
                
            return result
            
        except Exception as e:
            logger.error(f"Tool registration verification failed: {e}")
            self.errors.append(f"Tool registration error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def verify_server_initialization(self) -> Dict[str, Any]:
        """Verify that the MCP server can be initialized with all tools."""
        logger.info("Verifying server initialization...")
        
        try:
            from unittest.mock import patch, Mock
            
            with patch('terminal_mcp_server.utils.config.load_config') as mock_load_config, \
                 patch('terminal_mcp_server.utils.auth.load_auth_config') as mock_load_auth, \
                 patch('mcp.server.fastmcp.FastMCP') as mock_fastmcp:
                
                # Setup mocks
                mock_load_config.return_value = {
                    "server": {"name": "terminal-mcp-server"},
                    "logging": {"level": "INFO"}
                }
                mock_load_auth.return_value = {}
                
                mock_mcp_instance = Mock()
                registered_tools = []
                
                def tool_decorator():
                    def decorator(func):
                        registered_tools.append(func.__name__)
                        return func
                    return decorator
                
                mock_mcp_instance.tool = tool_decorator
                mock_fastmcp.return_value = mock_mcp_instance
                
                # Import and create server
                from terminal_mcp_server.server import TerminalMCPServer
                server = TerminalMCPServer()
                
                result = {
                    "server_created": server is not None,
                    "total_tools_registered": len(registered_tools),
                    "expected_tools": len(EXPECTED_TOOLS),
                    "test_connection_registered": "test_connection" in registered_tools,
                    "all_tools_registered": len(registered_tools) == len(EXPECTED_TOOLS),
                    "registered_tools": registered_tools,
                    "success": len(registered_tools) == len(EXPECTED_TOOLS)
                }
                
                logger.info(f"Server initialization verification: {result['success']}")
                return result
                
        except Exception as e:
            logger.error(f"Server initialization verification failed: {e}")
            self.errors.append(f"Server initialization error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def verify_tool_docstrings(self) -> Dict[str, Any]:
        """Verify that all tools have proper docstrings for MCP clients."""
        logger.info("Verifying tool docstrings...")
        
        try:
            from terminal_mcp_server.handlers import (
                command_handlers,
                process_handlers,
                python_handlers,
                environment_handlers,
            )
            
            # Create mock server to capture tool functions
            tool_functions = {}
            
            class MockServer:
                def tool(self):
                    def decorator(func):
                        tool_functions[func.__name__] = func
                        return func
                    return decorator
            
            mock_server = MockServer()
            
            # Register all tools
            command_handlers.register_tools(mock_server)
            process_handlers.register_tools(mock_server)
            python_handlers.register_tools(mock_server)
            environment_handlers.register_tools(mock_server)
            
            # Check docstrings
            missing_docstrings = []
            incomplete_docstrings = []
            
            for tool_name, func in tool_functions.items():
                if func.__doc__ is None:
                    missing_docstrings.append(tool_name)
                elif len(func.__doc__.strip()) == 0:
                    missing_docstrings.append(tool_name)
                else:
                    docstring = func.__doc__.lower()
                    if "args:" not in docstring and "returns:" not in docstring:
                        incomplete_docstrings.append(tool_name)
            
            result = {
                "total_tools_checked": len(tool_functions),
                "missing_docstrings": missing_docstrings,
                "incomplete_docstrings": incomplete_docstrings,
                "success": len(missing_docstrings) == 0 and len(incomplete_docstrings) == 0
            }
            
            logger.info(f"Docstring verification: {result['success']}")
            if missing_docstrings:
                logger.error(f"Tools missing docstrings: {missing_docstrings}")
            if incomplete_docstrings:
                logger.warning(f"Tools with incomplete docstrings: {incomplete_docstrings}")
                
            return result
            
        except Exception as e:
            logger.error(f"Docstring verification failed: {e}")
            self.errors.append(f"Docstring verification error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def verify_json_response_format(self) -> Dict[str, Any]:
        """Verify that tools return properly formatted JSON responses."""
        logger.info("Verifying JSON response format...")
        
        try:
            from terminal_mcp_server.handlers import command_handlers
            from unittest.mock import patch
            
            # Create mock server to capture tool functions
            tool_functions = {}
            
            class MockServer:
                def tool(self):
                    def decorator(func):
                        tool_functions[func.__name__] = func
                        return func
                    return decorator
            
            mock_server = MockServer()
            command_handlers.register_tools(mock_server)
            
            # Test execute_command tool response format
            execute_command_func = tool_functions.get("execute_command")
            if execute_command_func is None:
                return {"success": False, "error": "execute_command tool not found"}
            
            # Mock the handler's method to return a proper result
            with patch.object(command_handlers, 'execute_command') as mock_execute:
                from terminal_mcp_server.models.terminal_models import CommandResult
                from datetime import datetime
                
                mock_result = CommandResult(
                    command="echo test",
                    exit_code=0,
                    stdout="test\n",
                    stderr="",
                    execution_time=0.1,
                    started_at=datetime.now(),
                    completed_at=datetime.now()
                )
                mock_execute.return_value = mock_result
                
                # Call the tool function
                result = await execute_command_func("echo test")
                
                # Verify result format
                json_valid = False
                has_required_fields = False
                
                try:
                    parsed = json.loads(result)
                    json_valid = True
                    has_required_fields = all(field in parsed for field in ["command", "exit_code"])
                except json.JSONDecodeError:
                    pass
                
                verification_result = {
                    "tool_tested": "execute_command",
                    "returns_string": isinstance(result, str),
                    "json_valid": json_valid,
                    "has_required_fields": has_required_fields,
                    "success": isinstance(result, str) and json_valid and has_required_fields
                }
                
                logger.info(f"JSON response format verification: {verification_result['success']}")
                return verification_result
                
        except Exception as e:
            logger.error(f"JSON response format verification failed: {e}")
            self.errors.append(f"JSON format verification error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_full_verification(self) -> Dict[str, Any]:
        """Run all verification tests."""
        logger.info("Starting comprehensive MCP client verification...")
        start_time = datetime.now()
        
        # Run all verification tests
        results = {}
        results["tool_registration"] = await self.verify_tool_registration()
        results["server_initialization"] = await self.verify_server_initialization()
        results["tool_docstrings"] = await self.verify_tool_docstrings()
        results["json_response_format"] = await self.verify_json_response_format()
        
        # Calculate overall success
        all_successful = all(result.get("success", False) for result in results.values())
        
        # Generate summary
        end_time = datetime.now()
        summary = {
            "verification_started": start_time.isoformat(),
            "verification_completed": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "total_tests": len(results),
            "successful_tests": sum(1 for result in results.values() if result.get("success", False)),
            "failed_tests": sum(1 for result in results.values() if not result.get("success", True)),
            "overall_success": all_successful,
            "expected_tool_count": len(EXPECTED_TOOLS),
            "errors": self.errors,
            "detailed_results": results
        }
        
        # Log summary
        logger.info(f"Verification completed in {summary['duration_seconds']:.2f} seconds")
        logger.info(f"Tests passed: {summary['successful_tests']}/{summary['total_tests']}")
        logger.info(f"Overall success: {summary['overall_success']}")
        
        if not all_successful:
            logger.error("Some verification tests failed!")
            for test_name, result in results.items():
                if not result.get("success", False):
                    logger.error(f"  {test_name}: {result.get('error', 'Failed')}")
        
        return summary
    
    def generate_client_compatibility_report(self, verification_results: Dict[str, Any]) -> str:
        """Generate a client compatibility report."""
        report = []
        report.append("=" * 80)
        report.append("MCP CLIENT COMPATIBILITY VERIFICATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Expected Tools: {len(EXPECTED_TOOLS)}")
        report.append(f"Overall Status: {'✓ PASS' if verification_results['overall_success'] else '✗ FAIL'}")
        report.append("")
        
        # Test results summary
        report.append("TEST RESULTS SUMMARY:")
        report.append("-" * 40)
        for test_name, result in verification_results["detailed_results"].items():
            status = "✓ PASS" if result.get("success", False) else "✗ FAIL"
            report.append(f"{test_name:30} {status}")
        report.append("")
        
        # Client compatibility checklist
        report.append("CLIENT COMPATIBILITY CHECKLIST:")
        report.append("-" * 40)
        for requirement, description in CLIENT_COMPATIBILITY_CHECKLIST.items():
            report.append(f"□ {requirement}: {description}")
        report.append("")
        
        # Detailed results
        report.append("DETAILED VERIFICATION RESULTS:")
        report.append("-" * 40)
        for test_name, result in verification_results["detailed_results"].items():
            report.append(f"\n{test_name.upper()}:")
            for key, value in result.items():
                if key != "success":
                    report.append(f"  {key}: {value}")
        
        # Errors and recommendations
        if verification_results["errors"]:
            report.append("\nERRORS AND ISSUES:")
            report.append("-" * 40)
            for error in verification_results["errors"]:
                report.append(f"• {error}")
        
        report.append("\nRECOMMENDATIONS:")
        report.append("-" * 40)
        if not verification_results["overall_success"]:
            report.append("• Fix failing verification tests before deploying to production")
            report.append("• Test with multiple MCP client implementations")
            report.append("• Verify tool accessibility through Cursor, Claude Desktop, and other clients")
        else:
            report.append("• All verification tests passed!")
            report.append("• Server is ready for MCP client deployment")
            report.append("• Consider testing with real client implementations for final validation")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """Main function to run MCP client verification."""
    verifier = MCPClientVerifier()
    
    try:
        # Run verification
        results = await verifier.run_full_verification()
        
        # Generate and display report
        report = verifier.generate_client_compatibility_report(results)
        print(report)
        
        # Save report to file
        report_file = Path("mcp_client_verification_report.txt")
        with open(report_file, "w") as f:
            f.write(report)
        
        logger.info(f"Verification report saved to: {report_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results["overall_success"] else 1)
        
    except Exception as e:
        logger.error(f"Verification failed with exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 