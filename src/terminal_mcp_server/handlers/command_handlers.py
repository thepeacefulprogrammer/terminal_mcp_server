"""
Command execution handlers for Terminal MCP Server.

This module provides MCP tools for executing terminal commands with real-time output streaming,
timeout support, and comprehensive error handling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from ..utils.command_executor import CommandExecutor
from ..models.terminal_models import CommandRequest, CommandResult

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handles terminal command execution MCP tools."""
    
    def __init__(self):
        """Initialize command handlers."""
        self.command_executor = CommandExecutor()
        logger.info("CommandHandlers initialized")
    
    async def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> CommandResult:
        """
        Execute a terminal command with optional parameters.
        
        Args:
            command: The command to execute
            working_directory: Directory to run the command in
            environment_variables: Environment variables to set
            timeout: Command timeout in seconds
            capture_output: Whether to capture command output
            
        Returns:
            CommandResult with execution details
        """
        logger.info(f"Executing command: {command}")
        
        request = CommandRequest(
            command=command,
            working_directory=working_directory,
            environment_variables=environment_variables or {},
            timeout=timeout,
            capture_output=capture_output
        )
        
        try:
            result = await self.command_executor.execute(request)
            logger.info(f"Command completed with exit code: {result.exit_code}")
            return result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise
    
    def register_tools(self, mcp_server):
        """
        Register MCP tools with the FastMCP server.
        
        Args:
            mcp_server: FastMCP server instance
        """
        logger.info("Registering command execution MCP tools...")
        
        @mcp_server.tool()
        async def execute_command(
            command: str,
            working_directory: str = None,
            timeout: int = None,
        ) -> str:
            """
            Execute a terminal command.

            Args:
                command: The command to execute
                working_directory: Directory to run the command in  
                timeout: Command timeout in seconds

            Returns:
                JSON string with the command result
            """
            logger.info(f"MCP execute_command called: {command}")
            
            try:
                # Use the handler's execute_command method
                result = await self.execute_command(
                    command=command,
                    working_directory=working_directory,
                    timeout=timeout,
                    capture_output=True
                )
                
                # Convert result to JSON for MCP response
                result_dict = {
                    "command": result.command,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time,
                    "started_at": result.started_at.isoformat(),
                    "completed_at": result.completed_at.isoformat()
                }
                
                return json.dumps(result_dict, indent=2)
                
            except Exception as e:
                error_result = {
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command execution failed: {str(e)}",
                    "execution_time": 0,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        logger.info("Command execution MCP tools registered successfully")


# Global instance for MCP tool registration
command_handlers = CommandHandlers() 