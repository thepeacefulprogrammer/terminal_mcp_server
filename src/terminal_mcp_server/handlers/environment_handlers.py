"""Environment and directory management handlers for Terminal MCP Server."""

import logging

logger = logging.getLogger(__name__)


class EnvironmentHandlers:
    """Handles environment and directory management MCP tools."""
    
    def __init__(self):
        """Initialize environment handlers."""
        logger.info("EnvironmentHandlers initialized")


# Global instance for MCP tool registration
environment_handlers = EnvironmentHandlers() 