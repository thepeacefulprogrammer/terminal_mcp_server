"""
Command execution handlers for Terminal MCP Server.

This module provides MCP tools for executing terminal commands with real-time output streaming,
timeout support, and comprehensive error handling.
"""

import asyncio
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


# Global instance for MCP tool registration
command_handlers = CommandHandlers() 