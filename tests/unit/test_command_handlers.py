"""
Unit tests for command execution handlers.

Tests the CommandHandlers class that provides MCP tools for executing terminal commands.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from src.terminal_mcp_server.handlers.command_handlers import CommandHandlers
from src.terminal_mcp_server.models.terminal_models import CommandRequest, CommandResult


class TestCommandHandlers:
    """Test cases for CommandHandlers class."""
    
    @pytest.fixture
    def command_handlers(self):
        """Create CommandHandlers instance for testing."""
        return CommandHandlers()
    
    @pytest.fixture
    def sample_command_result(self):
        """Sample CommandResult for testing."""
        started_at = datetime.now()
        return CommandResult(
            command="echo 'test'",
            exit_code=0,
            stdout="test\n",
            stderr="",
            execution_time=0.1,
            started_at=started_at,
            completed_at=started_at
        )
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server for testing tool registration."""
        mock_server = Mock()
        mock_server.tool = Mock()
        return mock_server
    
    def test_init(self, command_handlers):
        """Test that CommandHandlers initializes correctly."""
        assert command_handlers is not None
        assert hasattr(command_handlers, 'command_executor')
        assert command_handlers.command_executor is not None
    
    @pytest.mark.asyncio
    async def test_execute_command_basic(self, command_handlers, sample_command_result):
        """Test basic command execution."""
        # Mock the command executor
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            result = await command_handlers.execute_command("echo 'test'")
            
            # Verify the executor was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0][0]  # First positional argument (CommandRequest)
            
            assert isinstance(call_args, CommandRequest)
            assert call_args.command == "echo 'test'"
            # Working directory should now be set to project directory by default
            assert call_args.working_directory is not None
            assert call_args.working_directory.endswith('terminal_mcp_server')
            assert call_args.environment_variables == {}
            assert call_args.timeout is None
            assert call_args.capture_output is True
            
            # Verify the result
            assert result == sample_command_result
    
    @pytest.mark.asyncio
    async def test_execute_command_with_working_directory(self, command_handlers, sample_command_result):
        """Test command execution with working directory."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                "pwd", 
                working_directory="/tmp"
            )
            
            call_args = mock_execute.call_args[0][0]
            assert call_args.working_directory == "/tmp"
    
    @pytest.mark.asyncio
    async def test_execute_command_with_environment_variables(self, command_handlers, sample_command_result):
        """Test command execution with environment variables."""
        env_vars = {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
        
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                "env", 
                environment_variables=env_vars
            )
            
            call_args = mock_execute.call_args[0][0]
            assert call_args.environment_variables == env_vars
    
    @pytest.mark.asyncio
    async def test_execute_command_with_timeout(self, command_handlers, sample_command_result):
        """Test command execution with timeout."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                        "sleep 0.1",
        timeout=5
            )
            
            call_args = mock_execute.call_args[0][0]
            assert call_args.timeout == 5
    
    @pytest.mark.asyncio
    async def test_execute_command_without_output_capture(self, command_handlers, sample_command_result):
        """Test command execution without output capture."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                "echo 'test'", 
                capture_output=False
            )
            
            call_args = mock_execute.call_args[0][0]
            assert call_args.capture_output is False
    
    @pytest.mark.asyncio
    async def test_execute_command_with_all_parameters(self, command_handlers, sample_command_result):
        """Test command execution with all parameters specified."""
        env_vars = {"TEST_VAR": "test_value"}
        
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                command="echo $TEST_VAR",
                working_directory="/tmp",
                environment_variables=env_vars,
                timeout=5,
                capture_output=True
            )
            
            call_args = mock_execute.call_args[0][0]
            assert call_args.command == "echo $TEST_VAR"
            assert call_args.working_directory == "/tmp"
            assert call_args.environment_variables == env_vars
            assert call_args.timeout == 5
            assert call_args.capture_output is True
    
    @pytest.mark.asyncio
    async def test_execute_command_executor_exception(self, command_handlers):
        """Test command execution when executor raises exception."""
        error_message = "Command execution failed"
        
        with patch.object(command_handlers.command_executor, 'execute', side_effect=Exception(error_message)) as mock_execute:
            with pytest.raises(Exception) as exc_info:
                await command_handlers.execute_command("failing_command")
            
            assert str(exc_info.value) == error_message
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_logs_execution(self, command_handlers, sample_command_result):
        """Test that command execution is properly logged."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result):
            with patch('src.terminal_mcp_server.handlers.command_handlers.logger') as mock_logger:
                await command_handlers.execute_command("echo 'test'")
                
                # Verify logging calls
                mock_logger.info.assert_any_call("Executing command: echo 'test'")
                mock_logger.info.assert_any_call("Command completed with exit code: 0")
    
    @pytest.mark.asyncio
    async def test_execute_command_logs_error(self, command_handlers):
        """Test that command execution errors are properly logged."""
        error_message = "Command execution failed"
        
        with patch.object(command_handlers.command_executor, 'execute', side_effect=Exception(error_message)):
            with patch('src.terminal_mcp_server.handlers.command_handlers.logger') as mock_logger:
                with pytest.raises(Exception):
                    await command_handlers.execute_command("failing_command")
                
                # Verify error logging
                mock_logger.error.assert_called_with(f"Command execution failed: {error_message}")
    
    def test_global_instance_exists(self):
        """Test that the global command_handlers instance exists."""
        from src.terminal_mcp_server.handlers.command_handlers import command_handlers
        
        assert command_handlers is not None
        assert isinstance(command_handlers, CommandHandlers)
    
    @pytest.mark.asyncio
    async def test_execute_command_creates_correct_request_object(self, command_handlers, sample_command_result):
        """Test that execute_command creates CommandRequest with correct field types."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                command="test_command",
                working_directory="/test/dir",
                environment_variables={"VAR1": "value1"},
                timeout=5,
                capture_output=False
            )
            
            # Get the CommandRequest object that was passed
            request = mock_execute.call_args[0][0]
            
            # Verify all fields are set correctly and have correct types
            assert isinstance(request, CommandRequest)
            assert isinstance(request.command, str)
            assert isinstance(request.working_directory, str) or request.working_directory is None
            assert isinstance(request.environment_variables, dict)
            assert isinstance(request.timeout, int) or request.timeout is None
            assert isinstance(request.capture_output, bool)
    
    @pytest.mark.asyncio
    async def test_execute_command_handles_none_environment_variables(self, command_handlers, sample_command_result):
        """Test that None environment_variables defaults to empty dict."""
        with patch.object(command_handlers.command_executor, 'execute', return_value=sample_command_result) as mock_execute:
            await command_handlers.execute_command(
                command="test_command",
                environment_variables=None
            )
            
            request = mock_execute.call_args[0][0]
            assert request.environment_variables == {}
    
    def test_register_tools(self, command_handlers, mock_mcp_server):
        """Test that register_tools method exists and can be called."""
        # Test that the method exists
        assert hasattr(command_handlers, 'register_tools')
        assert callable(command_handlers.register_tools)
        
        # Test that it can be called without error
        command_handlers.register_tools(mock_mcp_server)
        
        # Verify that the tool decorator was called
        mock_mcp_server.tool.assert_called()
    
    def test_register_tools_logs_registration(self, command_handlers, mock_mcp_server):
        """Test that register_tools logs the registration process."""
        with patch('src.terminal_mcp_server.handlers.command_handlers.logger') as mock_logger:
            command_handlers.register_tools(mock_mcp_server)
            
            # Verify logging calls
            mock_logger.info.assert_any_call("Registering command execution MCP tools...")
            mock_logger.info.assert_any_call("Command execution MCP tools registered successfully")
    
    @pytest.mark.asyncio
    async def test_mcp_tool_execution_success(self, command_handlers, sample_command_result):
        """Test the MCP tool wrapper handles successful execution."""
        # Create a mock server and capture the registered tool function
        mock_server = Mock()
        registered_tool_func = None
        
        def capture_tool_func(func):
            nonlocal registered_tool_func
            registered_tool_func = func
            return func
        
        mock_server.tool.return_value = capture_tool_func
        
        # Register the tools
        command_handlers.register_tools(mock_server)
        
        # Mock the handler's execute_command method
        with patch.object(command_handlers, 'execute_command', return_value=sample_command_result) as mock_execute:
            # Call the registered MCP tool
            result = await registered_tool_func("echo 'test'", "/tmp", 30)
            
            # Verify the handler was called correctly
            mock_execute.assert_called_once_with(
                command="echo 'test'",
                working_directory="/tmp",
                timeout=30,  # This test passes 30 as the timeout parameter
                capture_output=True
            )
            
            # Verify the result is JSON
            result_dict = json.loads(result)
            assert result_dict["command"] == "echo 'test'"
            assert result_dict["exit_code"] == 0
            assert result_dict["stdout"] == "test\n"
            assert result_dict["stderr"] == ""
    
    @pytest.mark.asyncio
    async def test_mcp_tool_execution_error(self, command_handlers):
        """Test the MCP tool wrapper handles execution errors."""
        # Create a mock server and capture the registered tool function
        mock_server = Mock()
        registered_tool_func = None
        
        def capture_tool_func(func):
            nonlocal registered_tool_func
            registered_tool_func = func
            return func
        
        mock_server.tool.return_value = capture_tool_func
        
        # Register the tools
        command_handlers.register_tools(mock_server)
        
        # Mock the handler's execute_command method to raise an exception
        error_message = "Test execution error"
        with patch.object(command_handlers, 'execute_command', side_effect=Exception(error_message)):
            # Call the registered MCP tool
            result = await registered_tool_func("failing_command")
            
            # Verify the error result is JSON
            result_dict = json.loads(result)
            assert result_dict["command"] == "failing_command"
            assert result_dict["exit_code"] == -1
            assert result_dict["stdout"] == ""
            assert error_message in result_dict["stderr"]
            assert result_dict["error"] == error_message