"""
Test working directory behavior for Terminal MCP Server.

This test module verifies that commands execute from the project directory
instead of the user's home directory by default.
"""

import pytest
import os
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Import the handlers we need to test
from terminal_mcp_server.handlers.command_handlers import CommandHandlers
from terminal_mcp_server.handlers.environment_handlers import EnvironmentHandlers
from terminal_mcp_server.handlers.python_handlers import PythonHandlers


class TestWorkingDirectory:
    """Test that commands execute from the correct working directory."""

    @pytest.mark.asyncio
    async def test_execute_command_uses_project_directory(self):
        """Test that execute_command runs from project directory by default."""
        handlers = CommandHandlers()
        
        # Mock the command executor to capture working_directory parameter
        with patch.object(handlers, 'command_executor') as mock_executor:
            from terminal_mcp_server.models.terminal_models import CommandResult
            from datetime import datetime
            now = datetime.now()
            mock_result = CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/home/randy/workspace/personal/terminal_mcp_server",
                stderr="",
                execution_time=0.1,
                started_at=now,
                completed_at=now
            )
            mock_executor.execute = AsyncMock(return_value=mock_result)
            
            # Execute a simple command
            result = await handlers.execute_command("pwd")
            
            # Verify the command executor was called with a CommandRequest
            mock_executor.execute.assert_called_once()
            call_args = mock_executor.execute.call_args
            
            # Get the CommandRequest object that was passed
            command_request = call_args[0][0] if call_args[0] else None
            assert command_request is not None
            
            # Check if a default working directory was set 
            # (This test will help us understand current behavior)
            working_dir = command_request.working_directory
            print(f"Current working_directory passed to command_executor: {working_dir}")
            
            # Now verify that the working directory is the project directory
            assert working_dir is not None
            assert working_dir.endswith('terminal_mcp_server')
            assert 'workspace/personal/terminal_mcp_server' in working_dir
            assert command_request.command == "pwd"

    @pytest.mark.asyncio
    async def test_get_current_directory_returns_project_directory(self):
        """Test that get_current_directory returns project directory by default."""
        handlers = EnvironmentHandlers()
        
        # Test the handler method directly
        result = await handlers.get_current_directory()
        
        # Should return the project directory
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "current_directory" in result
        
        current_dir = result["current_directory"]
        # Current directory should be the project directory
        assert current_dir.endswith('terminal_mcp_server')
        assert 'workspace/personal/terminal_mcp_server' in current_dir

    @pytest.mark.asyncio
    async def test_python_execution_uses_project_directory(self):
        """Test that Python code execution uses project directory by default."""
        handlers = PythonHandlers()
        
        # Mock the command executor to capture working_directory parameter
        with patch.object(handlers, 'command_executor') as mock_executor:
            from terminal_mcp_server.models.terminal_models import CommandResult
            from datetime import datetime
            now = datetime.now()
            mock_result = CommandResult(
                command="python -c import os; print(os.getcwd())",
                exit_code=0,
                stdout="import os; print(os.getcwd())",
                stderr="",
                execution_time=0.1,
                started_at=now,
                completed_at=now
            )
            mock_executor.execute = AsyncMock(return_value=mock_result)
            
            # Execute Python code
            result = await handlers.execute_python_code("import os; print(os.getcwd())")
            
            # Verify the command executor was called with CommandRequest
            mock_executor.execute.assert_called_once()
            call_args = mock_executor.execute.call_args
            
            # Get the CommandRequest object
            command_request = call_args[0][0] if call_args[0] else None
            assert command_request is not None
            
            working_dir = command_request.working_directory
            print(f"Python working_directory passed to command_executor: {working_dir}")
            
            # Verify that the working directory is the project directory
            assert working_dir is not None
            assert working_dir.endswith('terminal_mcp_server')

    @pytest.mark.asyncio
    async def test_command_with_explicit_working_directory_override(self):
        """Test that explicitly provided working_directory parameter is respected."""
        handlers = CommandHandlers()
        
        # Mock the command executor
        with patch.object(handlers, 'command_executor') as mock_executor:
            from terminal_mcp_server.models.terminal_models import CommandResult
            from datetime import datetime
            now = datetime.now()
            mock_result = CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/tmp",
                stderr="",
                execution_time=0.1,
                started_at=now,
                completed_at=now
            )
            mock_executor.execute = AsyncMock(return_value=mock_result)
            
            # Execute command with explicit working directory
            custom_dir = "/tmp"
            result = await handlers.execute_command("pwd", working_directory=custom_dir)
            
            # Verify the explicit directory was used
            call_args = mock_executor.execute.call_args
            command_request = call_args[0][0] if call_args[0] else None
            assert command_request is not None
            working_dir = command_request.working_directory
            assert working_dir == custom_dir

    def test_project_directory_detection(self):
        """Test that we can correctly identify the project directory."""
        # This test ensures our logic for finding the project directory works
        
        # The project directory should contain these key files
        expected_files = ['pyproject.toml', 'README.md', 'src/terminal_mcp_server']
        
        # Get current working directory (should be project dir when tests run)
        current_dir = Path.cwd()
        
        # Verify we're in the right place
        for expected_file in expected_files:
            file_path = current_dir / expected_file
            assert file_path.exists(), f"Expected file {expected_file} not found in {current_dir}"
        
        # This should be our project directory
        assert current_dir.name == 'terminal_mcp_server' 