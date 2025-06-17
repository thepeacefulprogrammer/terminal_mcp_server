"""Python script execution handlers for Terminal MCP Server."""

import logging

logger = logging.getLogger(__name__)


class PythonHandlers:
    """Handles Python script execution and virtual environment MCP tools."""
    
    def __init__(self):
        """Initialize Python handlers."""
        logger.info("PythonHandlers initialized")


# Global instance for MCP tool registration
python_handlers = PythonHandlers() 