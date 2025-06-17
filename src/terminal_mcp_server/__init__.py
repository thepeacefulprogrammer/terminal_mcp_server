"""
Terminal MCP Server Package

A comprehensive terminal command execution server for Model Context Protocol (MCP) clients.
Enables AI agents to execute terminal commands, manage processes, and run Python scripts.
"""

__version__ = "0.1.0"
__author__ = "Randy Herritt"
__email__ = "randy.herritt@gmail.com"

from .server import TerminalMCPServer

__all__ = ["TerminalMCPServer"]
