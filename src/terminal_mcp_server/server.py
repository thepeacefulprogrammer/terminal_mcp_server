#!/usr/bin/env python3
"""
Terminal MCP Server using FastMCP

This server provides comprehensive terminal command execution capabilities for MCP clients.
It enables AI agents to execute terminal commands, manage processes, and run Python scripts.
"""

import argparse
import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Configure file logging first
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"mcp_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Setup both file and console logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr),  # Log to stderr, not stdout
    ],
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("=" * 60)
logger.info("TERMINAL MCP SERVER STARTUP")
logger.info("=" * 60)
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Project root: {project_root}")
logger.info(f"Log file: {log_file}")
logger.info("Environment variables:")
for key, value in os.environ.items():
    if "PYTHON" in key.upper() or "PATH" in key.upper() or "MCP" in key.upper():
        logger.info(
            f"  {key}: {value[:50]}..." if len(value) > 50 else f"  {key}: {value}"
        )

try:
    from mcp.server.fastmcp import FastMCP

    logger.info("Successfully imported FastMCP")
except ImportError as e:
    logger.error(f"Failed to import FastMCP: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    logger.info("Successfully imported dotenv")
except ImportError as e:
    logger.error(f"Failed to import dotenv: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Import our modules
try:
    from terminal_mcp_server.utils.auth import load_auth_config
    from terminal_mcp_server.utils.config import load_config

    logger.info("Successfully imported utility modules")
except ImportError as e:
    logger.error(f"Failed to import utility modules: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

try:
    from terminal_mcp_server.handlers import (
        command_handlers,
        process_handlers,
        python_handlers,
        environment_handlers,
    )

    logger.info("Successfully imported terminal handlers")
except ImportError as e:
    logger.error(f"Failed to import terminal handlers: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")


class TerminalMCPServer:
    """Terminal MCP Server using FastMCP."""

    def __init__(self, config_path: str = None):
        logger.info("Initializing TerminalMCPServer...")

        try:
            self.config = load_config(config_path)
            logger.info(f"Configuration loaded: {self.config}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            self._setup_logging()
            logger.info("Logging setup complete")
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            # Initialize FastMCP Server
            server_name = self.config.get("server", {}).get("name", "terminal-mcp-server")
            self.mcp = FastMCP(server_name)
            logger.info("FastMCP server created successfully")
        except Exception as e:
            logger.error(f"Failed to create FastMCP server: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            # Initialize components that can be done synchronously
            self._init_sync_components()
            logger.info("Sync components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sync components: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            # Register tools
            self._register_tools()
            logger.info("Tools registered successfully")
        except Exception as e:
            logger.error(f"Failed to register tools: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        logger.info("TerminalMCPServer initialization complete")

    def _setup_logging(self):
        """Setup logging based on configuration."""
        log_config = self.config.get("logging", {})
        level = getattr(logging, log_config.get("level", "INFO"))

        logging.getLogger().setLevel(level)
        logger.info("Terminal MCP Server logging initialized")

    def _init_sync_components(self):
        """Initialize components that can be done synchronously."""
        logger.info("Initializing Terminal MCP Server components...")

        # Initialize auth config
        try:
            self.auth_config = load_auth_config()
            logger.info("Auth configuration loaded")
        except Exception as e:
            logger.warning(f"Auth configuration not loaded: {e}")
            self.auth_config = {}

        # Initialize any synchronous components here
        # For example, database connections, file system setup, etc.
        logger.info("Sync components initialization complete")

    async def _ensure_async_initialized(self):
        """Ensure async components are initialized."""
        if not hasattr(self, "_async_initialized"):
            logger.info("Initializing async components...")

            # Initialize any async components here
            # For example, async database connections, external API clients, etc.

            self._async_initialized = True
            logger.info("Async components initialized")

    def _register_tools(self):
        """Register all MCP tools."""
        logger.info("Registering MCP tools...")

        # Test connection tool
        @self.mcp.tool()
        async def test_connection(message: str = "No message provided") -> str:
            """Test the MCP server connection."""
            logger.info(f"test_connection called with message: {message}")
            await self._ensure_async_initialized()

            return f"Terminal MCP Server is running! Message: {message}"

        # Terminal command execution tool (placeholder)
        @self.mcp.tool()
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
            logger.info(f"execute_command called: command={command}")
            await self._ensure_async_initialized()

            # Placeholder implementation - will be implemented in later tasks
            return f"Command '{command}' executed successfully (placeholder)"

        # Background process management tool (placeholder)
        @self.mcp.tool()
        async def start_background_process(
            command: str,
            working_directory: str = None,
        ) -> str:
            """
            Start a background process.

            Args:
                command: The command to run in background
                working_directory: Directory to run the command in

            Returns:
                JSON string with the process information
            """
            logger.info(f"start_background_process called: command={command}")
            await self._ensure_async_initialized()

            # Placeholder implementation - will be implemented in later tasks
            return f"Background process '{command}' started successfully (placeholder)"

        logger.info("MCP tools registered successfully")

    def run(self):
        """Run the MCP server."""
        logger.info("Starting Terminal MCP Server...")
        self.mcp.run()


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Terminal MCP Server")
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to configuration file",
    )

    args = parser.parse_args()

    try:
        server = TerminalMCPServer(config_path=args.config)
        server.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
