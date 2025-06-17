"""Environment and directory management handlers for Terminal MCP Server."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvironmentHandlers:
    """Handles environment and directory management MCP tools."""
    
    def __init__(self):
        """Initialize environment handlers."""
        logger.info("EnvironmentHandlers initialized")
    
    async def get_current_directory(self) -> Dict[str, Any]:
        """
        Get the current working directory.
        
        Returns:
            Dict with current directory information
        """
        logger.info("Getting current working directory")
        
        try:
            current_dir = os.getcwd()
            
            result = {
                "success": True,
                "current_directory": current_dir,
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Current directory: {current_dir}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get current directory: {e}")
            return {
                "success": False,
                "error": f"Failed to get current directory: {str(e)}"
            }
    
    async def change_directory(self, path: str) -> Dict[str, Any]:
        """
        Change the current working directory.
        
        Args:
            path: Path to change to
            
        Returns:
            Dict with directory change results
        """
        logger.info(f"Changing directory to: {path}")
        
        try:
            # Validate input
            if path is None:
                return {
                    "success": False,
                    "error": "Path cannot be None"
                }
            
            # Get current directory before changing
            previous_dir = os.getcwd()
            
            # Validate that the path exists
            if not os.path.exists(path):
                return {
                    "success": False,
                    "error": f"Path does not exist: {path}"
                }
            
            # Validate that the path is a directory
            if not os.path.isdir(path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}"
                }
            
            # Change directory
            os.chdir(path)
            
            # Get the resolved path after change
            new_dir = os.path.realpath(path)
            
            result = {
                "success": True,
                "new_directory": new_dir,
                "previous_directory": previous_dir,
                "changed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully changed directory from {previous_dir} to {new_dir}")
            return result
            
        except PermissionError as e:
            logger.error(f"Permission denied changing to directory {path}: {e}")
            return {
                "success": False,
                "error": f"Permission denied: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to change directory to {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to change directory to {path}: {str(e)}"
            }
    
    async def get_environment_variables(self, variables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get environment variables.
        
        Args:
            variables: List of specific variables to get (None for all)
            
        Returns:
            Dict with environment variables
        """
        logger.info(f"Getting environment variables: {variables if variables else 'all'}")
        
        try:
            if variables is None:
                # Get all environment variables
                env_vars = dict(os.environ)
                count = len(env_vars)
                logger.info(f"Retrieved all {count} environment variables")
            else:
                # Get specific environment variables
                env_vars = {}
                for var in variables:
                    if var in os.environ:
                        env_vars[var] = os.environ[var]
                count = len(env_vars)
                logger.info(f"Retrieved {count} of {len(variables)} requested environment variables")
            
            result = {
                "success": True,
                "environment_variables": env_vars,
                "count": count,
                "retrieved_at": datetime.now().isoformat()
            }
            
            if variables is not None:
                result["requested_variables"] = variables
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get environment variables: {e}")
            return {
                "success": False,
                "error": f"Failed to get environment variables: {str(e)}"
            }
    
    async def set_environment_variable(self, name: str, value: str) -> Dict[str, Any]:
        """
        Set an environment variable.
        
        Args:
            name: Variable name
            value: Variable value
            
        Returns:
            Dict with set operation results
        """
        logger.info(f"Setting environment variable: {name}")
        
        try:
            # Validate input
            if name is None:
                return {
                    "success": False,
                    "error": "Variable name cannot be None"
                }
            
            if value is None:
                return {
                    "success": False,
                    "error": "Variable value cannot be None"
                }
            
            # Get previous value if it exists
            previous_value = os.environ.get(name)
            
            # Set the environment variable
            os.environ[name] = value
            
            result = {
                "success": True,
                "variable": name,
                "value": value,
                "previous_value": previous_value,
                "set_at": datetime.now().isoformat()
            }
            
            if previous_value is not None:
                logger.info(f"Updated environment variable {name} (was: {previous_value[:50]}{'...' if len(previous_value) > 50 else ''})")
            else:
                logger.info(f"Set new environment variable {name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to set environment variable {name}: {e}")
            return {
                "success": False,
                "error": f"Failed to set environment variable: {str(e)}"
            }
    
    def register_tools(self, mcp_server):
        """
        Register MCP tools with the FastMCP server.
        
        Args:
            mcp_server: FastMCP server instance
        """
        logger.info("Registering environment management MCP tools...")
        
        @mcp_server.tool()
        async def get_current_directory() -> str:
            """
            Get the current working directory.
            
            Returns:
                JSON string with current directory information
            """
            logger.info("MCP get_current_directory called")
            
            try:
                result = await self.get_current_directory()
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def change_directory(path: str) -> str:
            """
            Change the current working directory.
            
            Args:
                path: Path to change to
                
            Returns:
                JSON string with directory change results
            """
            logger.info(f"MCP change_directory called: {path}")
            
            try:
                result = await self.change_directory(path)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "path": path,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def get_environment_variables(variables: List[str] = None) -> str:
            """
            Get environment variables.
            
            Args:
                variables: List of specific variables to get (None for all)
                
            Returns:
                JSON string with environment variables
            """
            logger.info(f"MCP get_environment_variables called: {variables if variables else 'all'}")
            
            try:
                result = await self.get_environment_variables(variables)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def set_environment_variable(name: str, value: str) -> str:
            """
            Set an environment variable.
            
            Args:
                name: Variable name
                value: Variable value
                
            Returns:
                JSON string with set operation results
            """
            logger.info(f"MCP set_environment_variable called: {name}")
            
            try:
                result = await self.set_environment_variable(name, value)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "name": name,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        logger.info("Environment management MCP tools registered successfully")


# Global instance for MCP tool registration
environment_handlers = EnvironmentHandlers() 