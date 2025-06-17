"""Background process management handlers for Terminal MCP Server."""

import logging

logger = logging.getLogger(__name__)


class ProcessHandlers:
    """Handles background process management MCP tools."""
    
    def __init__(self):
        """Initialize process handlers."""
        logger.info("ProcessHandlers initialized")


# Global instance for MCP tool registration  
process_handlers = ProcessHandlers()
