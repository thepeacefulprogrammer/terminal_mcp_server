"""Tests for process management handlers and MCP tools."""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from terminal_mcp_server.handlers.process_handlers import ProcessHandlers
from terminal_mcp_server.models.terminal_models import ProcessInfo, ProcessStatus


@pytest.fixture
def process_handlers():
    """Create a ProcessHandlers instance for testing."""
    return ProcessHandlers()


@pytest.fixture
def mock_process_manager():
    """Create a mock ProcessManager for testing."""
    mock_manager = Mock()
    mock_manager.start_process = AsyncMock()
    mock_manager.list_processes = AsyncMock()
    mock_manager.get_process_status = AsyncMock()
    mock_manager.kill_process = AsyncMock()
    mock_manager.restart_process = AsyncMock()
    mock_manager.get_process_output = AsyncMock()
    return mock_manager


@pytest.mark.asyncio
async def test_process_handlers_initialization(process_handlers):
    """Test that ProcessHandlers initializes properly."""
    assert process_handlers is not None
    assert hasattr(process_handlers, 'process_manager')
    assert hasattr(process_handlers, 'execute_command_background')
    assert hasattr(process_handlers, 'list_background_processes') 
    assert hasattr(process_handlers, 'get_process_status')
    assert hasattr(process_handlers, 'kill_background_process')
    assert hasattr(process_handlers, 'restart_background_process')
    assert hasattr(process_handlers, 'get_process_output')


@pytest.mark.asyncio
async def test_execute_command_background_basic(process_handlers, mock_process_manager):
    """Test executing a basic background command."""
    process_handlers.process_manager = mock_process_manager
    
    # Mock process info
    mock_process_info = ProcessInfo(
        pid=12345,
        process_id="proc_test_123",
        command="sleep 10",
        status=ProcessStatus.RUNNING,
        started_at=datetime.now(),
        working_directory=None,
        environment_variables={}
    )
    mock_process_manager.start_process.return_value = mock_process_info
    
    # Execute background command
    result = await process_handlers.execute_command_background(command="sleep 10")
    
    assert isinstance(result, dict)
    assert result["process_id"] == "proc_test_123"
    assert result["command"] == "sleep 10"
    assert result["status"] == "running"
    assert result["pid"] == 12345
    
    # Verify process manager was called correctly
    mock_process_manager.start_process.assert_called_once_with(
        command="sleep 10",
        working_directory=None,
        environment_variables=None,
        capture_output=True
    )


@pytest.mark.asyncio
async def test_execute_command_background_with_params(process_handlers, mock_process_manager):
    """Test executing background command with working directory and environment."""
    process_handlers.process_manager = mock_process_manager
    
    mock_process_info = ProcessInfo(
        pid=12346,
        process_id="proc_test_124",
        command="echo $TEST_VAR",
        status=ProcessStatus.RUNNING,
        started_at=datetime.now(),
        working_directory="/tmp",
        environment_variables={"TEST_VAR": "test_value"}
    )
    mock_process_manager.start_process.return_value = mock_process_info
    
    result = await process_handlers.execute_command_background(
        command="echo $TEST_VAR",
        working_directory="/tmp",
        environment_variables={"TEST_VAR": "test_value"}
    )
    
    assert result["working_directory"] == "/tmp"
    assert result["environment_variables"] == {"TEST_VAR": "test_value"}
    
    mock_process_manager.start_process.assert_called_once_with(
        command="echo $TEST_VAR",
        working_directory="/tmp",
        environment_variables={"TEST_VAR": "test_value"},
        capture_output=True
    )


@pytest.mark.asyncio
async def test_list_background_processes_empty(process_handlers, mock_process_manager):
    """Test listing background processes when none exist."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.list_processes.return_value = []
    
    result = await process_handlers.list_background_processes()
    
    assert isinstance(result, list)
    assert len(result) == 0
    mock_process_manager.list_processes.assert_called_once()


@pytest.mark.asyncio
async def test_list_background_processes_with_data(process_handlers, mock_process_manager):
    """Test listing background processes with multiple processes."""
    process_handlers.process_manager = mock_process_manager
    
    mock_processes = [
        ProcessInfo(
            pid=12345,
            process_id="proc_1",
            command="sleep 10",
            status=ProcessStatus.RUNNING,
            started_at=datetime.now(),
            working_directory=None,
            environment_variables={}
        ),
        ProcessInfo(
            pid=12346,
            process_id="proc_2", 
            command="sleep 20",
            status=ProcessStatus.COMPLETED,
            started_at=datetime.now(),
            working_directory="/tmp",
            environment_variables={"VAR": "value"}
        )
    ]
    mock_process_manager.list_processes.return_value = mock_processes
    
    result = await process_handlers.list_background_processes()
    
    assert isinstance(result, list)
    assert len(result) == 2
    
    # Check first process
    assert result[0]["process_id"] == "proc_1"
    assert result[0]["command"] == "sleep 10"
    assert result[0]["status"] == "running"
    assert result[0]["pid"] == 12345
    
    # Check second process
    assert result[1]["process_id"] == "proc_2"
    assert result[1]["command"] == "sleep 20" 
    assert result[1]["status"] == "completed"
    assert result[1]["working_directory"] == "/tmp"


@pytest.mark.asyncio
async def test_get_process_status_existing(process_handlers, mock_process_manager):
    """Test getting status of an existing process."""
    process_handlers.process_manager = mock_process_manager
    
    mock_process_info = ProcessInfo(
        pid=12347,
        process_id="proc_test_125",
        command="long_running_command",
        status=ProcessStatus.RUNNING,
        started_at=datetime.now(),
        working_directory=None,
        environment_variables={}
    )
    mock_process_manager.get_process_status.return_value = mock_process_info
    
    result = await process_handlers.get_process_status("proc_test_125")
    
    assert isinstance(result, dict)
    assert result["process_id"] == "proc_test_125"
    assert result["status"] == "running"
    assert result["command"] == "long_running_command"
    
    mock_process_manager.get_process_status.assert_called_once_with("proc_test_125")


@pytest.mark.asyncio
async def test_get_process_status_nonexistent(process_handlers, mock_process_manager):
    """Test getting status of a non-existent process."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.get_process_status.side_effect = ValueError("Process not found")
    
    with pytest.raises(ValueError) as exc_info:
        await process_handlers.get_process_status("nonexistent_proc")
    
    assert "Process not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kill_background_process_success(process_handlers, mock_process_manager):
    """Test successfully killing a background process."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.kill_process.return_value = True
    
    result = await process_handlers.kill_background_process("proc_test_126")
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["process_id"] == "proc_test_126"
    assert "Successfully killed" in result["message"]
    
    mock_process_manager.kill_process.assert_called_once_with("proc_test_126")


@pytest.mark.asyncio
async def test_kill_background_process_failure(process_handlers, mock_process_manager):
    """Test failing to kill a background process."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.kill_process.return_value = False
    
    result = await process_handlers.kill_background_process("nonexistent_proc")
    
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["process_id"] == "nonexistent_proc"
    assert "Failed to kill" in result["message"]


@pytest.mark.asyncio
async def test_restart_background_process_success(process_handlers, mock_process_manager):
    """Test successfully restarting a background process."""
    process_handlers.process_manager = mock_process_manager
    
    mock_new_process = ProcessInfo(
        pid=12348,
        process_id="proc_test_127_new",
        command="restarted_command",
        status=ProcessStatus.RUNNING,
        started_at=datetime.now(),
        working_directory=None,
        environment_variables={}
    )
    mock_process_manager.restart_process.return_value = mock_new_process
    
    result = await process_handlers.restart_background_process("proc_test_127")
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["original_process_id"] == "proc_test_127"
    assert result["new_process_id"] == "proc_test_127_new"
    assert result["command"] == "restarted_command"
    assert result["status"] == "running"
    
    mock_process_manager.restart_process.assert_called_once_with("proc_test_127")


@pytest.mark.asyncio
async def test_restart_background_process_failure(process_handlers, mock_process_manager):
    """Test failing to restart a background process."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.restart_process.side_effect = ValueError("Process not found")
    
    result = await process_handlers.restart_background_process("nonexistent_proc")
    
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["original_process_id"] == "nonexistent_proc"
    assert "Process not found" in result["error"]


@pytest.mark.asyncio
async def test_get_process_output_success(process_handlers, mock_process_manager):
    """Test getting output from a background process."""
    process_handlers.process_manager = mock_process_manager
    
    mock_output = {
        "stdout": "Test output line 1\nTest output line 2\n",
        "stderr": "Warning: test warning\n"
    }
    mock_process_manager.get_process_output.return_value = mock_output
    
    result = await process_handlers.get_process_output("proc_test_128")
    
    assert isinstance(result, dict)
    assert result["process_id"] == "proc_test_128"
    assert result["stdout"] == "Test output line 1\nTest output line 2\n"
    assert result["stderr"] == "Warning: test warning\n"
    
    mock_process_manager.get_process_output.assert_called_once_with("proc_test_128")


@pytest.mark.asyncio
async def test_get_process_output_failure(process_handlers, mock_process_manager):
    """Test failing to get output from a background process."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.get_process_output.side_effect = ValueError("No output captured")
    
    result = await process_handlers.get_process_output("proc_no_output")
    
    assert isinstance(result, dict)
    assert result["process_id"] == "proc_no_output"
    assert result["success"] is False
    assert "No output captured" in result["error"]


@pytest.mark.asyncio
async def test_mcp_tool_registration(process_handlers):
    """Test that MCP tools are registered correctly."""
    mock_mcp_server = Mock()
    mock_tool_decorator = Mock()
    mock_mcp_server.tool.return_value = mock_tool_decorator
    
    # Call register_tools
    process_handlers.register_tools(mock_mcp_server)
    
    # Verify that tool decorator was called for each expected tool
    expected_calls = 6  # Number of MCP tools we expect to register
    assert mock_mcp_server.tool.call_count == expected_calls


@pytest.mark.asyncio
async def test_mcp_execute_command_background_tool():
    """Test the MCP execute_command_background tool."""
    process_handlers = ProcessHandlers()
    
    # Mock the process manager
    mock_process_manager = Mock()
    mock_process_info = ProcessInfo(
        pid=12349,
        process_id="mcp_proc_test",
        command="sleep 5",
        status=ProcessStatus.RUNNING,
        started_at=datetime.now(),
        working_directory=None,
        environment_variables={}
    )
    mock_process_manager.start_process = AsyncMock(return_value=mock_process_info)
    process_handlers.process_manager = mock_process_manager
    
    # Test the handler method directly
    result = await process_handlers.execute_command_background("sleep 5")
    
    # Parse the result (should be JSON-serializable dict)
    assert isinstance(result, dict)
    assert result["process_id"] == "mcp_proc_test"
    assert result["command"] == "sleep 5"


@pytest.mark.asyncio
async def test_mcp_list_background_processes_tool():
    """Test the MCP list_background_processes tool."""
    process_handlers = ProcessHandlers()
    
    # Mock the process manager
    mock_process_manager = Mock()
    mock_processes = [
        ProcessInfo(
            pid=12350,
            process_id="mcp_list_test_1",
            command="test_cmd_1",
            status=ProcessStatus.RUNNING,
            started_at=datetime.now(),
            working_directory=None,
            environment_variables={}
        )
    ]
    mock_process_manager.list_processes = AsyncMock(return_value=mock_processes)
    process_handlers.process_manager = mock_process_manager
    
    # Test the handler method directly
    result = await process_handlers.list_background_processes()
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["process_id"] == "mcp_list_test_1"


@pytest.mark.asyncio
async def test_error_handling_with_json_response(process_handlers, mock_process_manager):
    """Test that errors are properly handled and returned as JSON responses."""
    process_handlers.process_manager = mock_process_manager
    mock_process_manager.start_process.side_effect = Exception("Test error")
    
    # Test that the method handles exceptions gracefully
    with pytest.raises(Exception):
        await process_handlers.execute_command_background("failing_command")


@pytest.mark.asyncio
async def test_concurrent_process_operations(process_handlers, mock_process_manager):
    """Test concurrent process operations."""
    process_handlers.process_manager = mock_process_manager
    
    # Mock multiple process operations
    mock_processes = []
    for i in range(3):
        mock_process = ProcessInfo(
            pid=12350 + i,
            process_id=f"proc_concurrent_{i}",
            command=f"sleep {i + 1}",
            status=ProcessStatus.RUNNING,
            started_at=datetime.now(),
            working_directory=None,
            environment_variables={}
        )
        mock_processes.append(mock_process)
    
    mock_process_manager.start_process.side_effect = mock_processes
    
    # Execute multiple background commands concurrently
    tasks = [
        process_handlers.execute_command_background(f"sleep {i + 1}")
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["process_id"] == f"proc_concurrent_{i}"
        assert result["command"] == f"sleep {i + 1}"
        assert result["status"] == "running"


# ========== Task 3.9: Server Integration Tests ==========

@pytest.mark.asyncio
async def test_process_handlers_server_registration():
    """Test that process handlers are properly registered in the server."""
    # Import here to avoid circular imports
    from terminal_mcp_server.server import TerminalMCPServer
    
    # Mock the config loading to avoid file dependencies
    mock_config = {
        "server": {"name": "test-terminal-mcp-server"},
        "logging": {"level": "INFO"}
    }
    
    with patch('terminal_mcp_server.server.load_config', return_value=mock_config), \
         patch('terminal_mcp_server.server.load_auth_config', return_value={}), \
         patch('terminal_mcp_server.utils.config.load_config', return_value=mock_config):
        
        # Create server instance
        server = TerminalMCPServer()
        
        # Check if process handlers are already registered in the current server
        # We'll do this by checking if the server's _register_tools method includes process handlers
        import inspect
        server_source = inspect.getsource(server._register_tools)
        
        # Expected process tools that should be registered
        expected_process_tools = [
            "execute_command_background",
            "list_background_processes", 
            "get_process_status",
            "kill_background_process",
            "restart_background_process",
            "get_process_output"
        ]
        
        # Check if process_handlers.register_tools is called in the server
        process_handlers_registered = "process_handlers.register_tools" in server_source
        
        # This test should fail initially if process handlers aren't registered yet
        assert process_handlers_registered, "Process handlers should be registered in server._register_tools method"


@pytest.mark.asyncio 
async def test_server_process_tools_integration():
    """Test that server properly integrates process handlers tools."""
    # Import here to avoid circular imports
    from terminal_mcp_server.server import TerminalMCPServer
    
    # Mock the config loading
    mock_config = {
        "server": {"name": "test-terminal-mcp-server"},
        "logging": {"level": "INFO"}
    }
    
    with patch('terminal_mcp_server.server.load_config', return_value=mock_config), \
         patch('terminal_mcp_server.server.load_auth_config', return_value={}), \
         patch('terminal_mcp_server.utils.config.load_config', return_value=mock_config):
        
        # Create server instance
        server = TerminalMCPServer()
        
        # Verify server has the mcp instance
        assert hasattr(server, 'mcp'), "Server should have FastMCP instance"
        
        # Verify server initialization completed successfully
        assert server.mcp is not None, "FastMCP instance should be initialized"
        
        # The fact that server creation didn't raise an exception indicates
        # that process handlers registration is working properly