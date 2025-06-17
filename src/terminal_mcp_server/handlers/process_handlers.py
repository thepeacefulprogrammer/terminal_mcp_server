"""Background process management handlers for Terminal MCP Server."""

import json
import logging
from typing import Dict, Any, Optional, List

from ..utils.process_manager import ProcessManager
from ..models.terminal_models import ProcessInfo, ProcessStatus

logger = logging.getLogger(__name__)


class ProcessHandlers:
    """Handles background process management MCP tools."""
    
    def __init__(self):
        """Initialize process handlers."""
        self.process_manager = ProcessManager()
        logger.info("ProcessHandlers initialized")
    
    async def execute_command_background(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command in the background and return process information.
        
        Args:
            command: The command to execute
            working_directory: Directory to run the command in
            environment_variables: Environment variables to set
            
        Returns:
            Dict with process information
        """
        logger.info(f"Starting background process: {command}")
        
        try:
            process_info = await self.process_manager.start_process(
                command=command,
                working_directory=working_directory,
                environment_variables=environment_variables,
                capture_output=True
            )
            
            result = {
                "process_id": process_info.process_id,
                "pid": process_info.pid,
                "command": process_info.command,
                "status": process_info.status.value,
                "started_at": process_info.started_at.isoformat(),
                "working_directory": process_info.working_directory,
                "environment_variables": process_info.environment_variables
            }
            
            logger.info(f"Background process started: {process_info.process_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to start background process: {e}")
            raise
    
    async def list_background_processes(self) -> List[Dict[str, Any]]:
        """
        List all background processes.
        
        Returns:
            List of process information dictionaries
        """
        logger.info("Listing background processes")
        
        try:
            processes = await self.process_manager.list_processes()
            
            result = []
            for process in processes:
                process_dict = {
                    "process_id": process.process_id,
                    "pid": process.pid,
                    "command": process.command,
                    "status": process.status.value,
                    "started_at": process.started_at.isoformat(),
                    "working_directory": process.working_directory,
                    "environment_variables": process.environment_variables
                }
                result.append(process_dict)
            
            logger.info(f"Listed {len(result)} background processes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list background processes: {e}")
            raise
    
    async def get_process_status(self, process_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific process.
        
        Args:
            process_id: The process ID to check
            
        Returns:
            Dict with process status information
        """
        logger.info(f"Getting status for process: {process_id}")
        
        try:
            process_info = await self.process_manager.get_process_status(process_id)
            
            result = {
                "process_id": process_info.process_id,
                "pid": process_info.pid,
                "command": process_info.command,
                "status": process_info.status.value,
                "started_at": process_info.started_at.isoformat(),
                "working_directory": process_info.working_directory,
                "environment_variables": process_info.environment_variables
            }
            
            logger.info(f"Process {process_id} status: {process_info.status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get process status for {process_id}: {e}")
            raise
    
    async def kill_background_process(self, process_id: str) -> Dict[str, Any]:
        """
        Kill a background process.
        
        Args:
            process_id: The process ID to kill
            
        Returns:
            Dict with kill operation result
        """
        logger.info(f"Killing background process: {process_id}")
        
        try:
            success = await self.process_manager.kill_process(process_id)
            
            if success:
                message = f"Successfully killed process {process_id}"
                logger.info(message)
                return {
                    "success": True,
                    "process_id": process_id,
                    "message": message
                }
            else:
                message = f"Failed to kill process {process_id} (process not found or already dead)"
                logger.warning(message)
                return {
                    "success": False,
                    "process_id": process_id,
                    "message": message
                }
                
        except Exception as e:
            logger.error(f"Error killing process {process_id}: {e}")
            return {
                "success": False,
                "process_id": process_id,
                "error": str(e)
            }
    
    async def restart_background_process(self, process_id: str) -> Dict[str, Any]:
        """
        Restart a background process.
        
        Args:
            process_id: The process ID to restart
            
        Returns:
            Dict with restart operation result
        """
        logger.info(f"Restarting background process: {process_id}")
        
        try:
            new_process = await self.process_manager.restart_process(process_id)
            
            result = {
                "success": True,
                "original_process_id": process_id,
                "new_process_id": new_process.process_id,
                "pid": new_process.pid,
                "command": new_process.command,
                "status": new_process.status.value,
                "started_at": new_process.started_at.isoformat(),
                "working_directory": new_process.working_directory,
                "environment_variables": new_process.environment_variables
            }
            
            logger.info(f"Process {process_id} restarted as {new_process.process_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to restart process {process_id}: {e}")
            return {
                "success": False,
                "original_process_id": process_id,
                "error": str(e)
            }
    
    async def get_process_output(self, process_id: str) -> Dict[str, Any]:
        """
        Get the captured output from a background process.
        
        Args:
            process_id: The process ID to get output from
            
        Returns:
            Dict with process output
        """
        logger.info(f"Getting output for process: {process_id}")
        
        try:
            output = await self.process_manager.get_process_output(process_id)
            
            result = {
                "process_id": process_id,
                "stdout": output["stdout"],
                "stderr": output["stderr"],
                "success": True
            }
            
            logger.info(f"Retrieved output for process {process_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get output for process {process_id}: {e}")
            return {
                "process_id": process_id,
                "success": False,
                "error": str(e)
            }
    
    def register_tools(self, mcp_server):
        """
        Register MCP tools with the FastMCP server.
        
        Args:
            mcp_server: FastMCP server instance
        """
        logger.info("Registering background process management MCP tools...")
        
        @mcp_server.tool()
        async def execute_command_background(
            command: str,
            working_directory: str = None,
            environment_variables: Dict[str, str] = None,
        ) -> str:
            """
            Execute a command in the background.

            Args:
                command: The command to execute
                working_directory: Directory to run the command in
                environment_variables: Environment variables to set

            Returns:
                JSON string with the process information
            """
            logger.info(f"MCP execute_command_background called: {command}")
            
            try:
                result = await self.execute_command_background(
                    command=command,
                    working_directory=working_directory,
                    environment_variables=environment_variables
                )
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "command": command,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def list_background_processes() -> str:
            """
            List all background processes.

            Returns:
                JSON string with the list of processes
            """
            logger.info("MCP list_background_processes called")
            
            try:
                result = await self.list_background_processes()
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def get_process_status(process_id: str) -> str:
            """
            Get the status of a background process.

            Args:
                process_id: The process ID to check

            Returns:
                JSON string with the process status
            """
            logger.info(f"MCP get_process_status called: {process_id}")
            
            try:
                result = await self.get_process_status(process_id)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "process_id": process_id,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def kill_background_process(process_id: str) -> str:
            """
            Kill a background process.

            Args:
                process_id: The process ID to kill

            Returns:
                JSON string with the kill operation result
            """
            logger.info(f"MCP kill_background_process called: {process_id}")
            
            try:
                result = await self.kill_background_process(process_id)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "process_id": process_id,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def restart_background_process(process_id: str) -> str:
            """
            Restart a background process.

            Args:
                process_id: The process ID to restart

            Returns:
                JSON string with the restart operation result
            """
            logger.info(f"MCP restart_background_process called: {process_id}")
            
            try:
                result = await self.restart_background_process(process_id)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "process_id": process_id,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def get_process_output(process_id: str) -> str:
            """
            Get the output from a background process.

            Args:
                process_id: The process ID to get output from

            Returns:
                JSON string with the process output
            """
            logger.info(f"MCP get_process_output called: {process_id}")
            
            try:
                result = await self.get_process_output(process_id)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "process_id": process_id,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        logger.info("Background process management MCP tools registered successfully")


# Global instance for MCP tool registration  
process_handlers = ProcessHandlers()
