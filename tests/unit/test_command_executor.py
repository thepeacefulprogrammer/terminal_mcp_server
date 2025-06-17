"""
Tests for command executor functionality to ensure proper async command execution,
output streaming, timeout handling, and error management.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path

from terminal_mcp_server.utils.command_executor import CommandExecutor
from terminal_mcp_server.models.terminal_models import CommandRequest, CommandResult


@pytest.fixture
def command_executor():
    """Create a CommandExecutor instance for testing."""
    return CommandExecutor()


@pytest.fixture
def simple_command_request():
    """Create a simple command request for testing."""
    return CommandRequest(
        command="echo 'hello world'",
        working_directory="/tmp",
        timeout=30
    )


@pytest.fixture
def long_running_command_request():
    """Create a long-running command request for testing."""
    return CommandRequest(
        command="sleep 0.1",  # Much faster for testing
        timeout=2
    )


@pytest.mark.asyncio
async def test_command_executor_initialization(command_executor):
    """Test that CommandExecutor initializes properly."""
    assert command_executor is not None
    assert hasattr(command_executor, 'execute')
    assert callable(command_executor.execute)


@pytest.mark.asyncio
async def test_execute_simple_command(command_executor, simple_command_request):
    """Test executing a simple command successfully."""
    result = await command_executor.execute(simple_command_request)
    
    assert isinstance(result, CommandResult)
    assert result.command == "echo 'hello world'"
    assert result.exit_code == 0
    assert "hello world" in result.stdout
    assert result.stderr == ""
    assert result.execution_time > 0
    assert isinstance(result.started_at, datetime)
    assert isinstance(result.completed_at, datetime)
    assert result.completed_at > result.started_at


@pytest.mark.asyncio
async def test_execute_command_with_working_directory(command_executor):
    """Test executing a command with a specific working directory."""
    # Create a temporary directory for testing
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        request = CommandRequest(
            command="pwd",
            working_directory=temp_dir,
            timeout=10
        )
        
        result = await command_executor.execute(request)
        
        assert result.exit_code == 0
        assert temp_dir in result.stdout.strip()


@pytest.mark.asyncio
async def test_execute_command_with_environment_variables(command_executor):
    """Test executing a command with custom environment variables."""
    request = CommandRequest(
        command="echo $TEST_VAR",
        environment_variables={"TEST_VAR": "test_value"},
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "test_value" in result.stdout


@pytest.mark.asyncio
async def test_execute_command_with_timeout(command_executor):
    """Test that commands respect timeout limits."""
    request = CommandRequest(
        command="sleep 2",
        timeout=1  # 1 second timeout for a 2 second command
    )
    
    result = await command_executor.execute(request)
    
    # Should either timeout or be killed
    assert result.exit_code != 0
    assert result.execution_time < 2  # Should not run for full 2 seconds (allows timeout overhead)


@pytest.mark.asyncio
async def test_execute_failing_command(command_executor):
    """Test executing a command that fails."""
    request = CommandRequest(
        command="false",  # Command that always fails
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code != 0
    assert result.command == "false"
    assert isinstance(result.started_at, datetime)
    assert isinstance(result.completed_at, datetime)


@pytest.mark.asyncio
async def test_execute_invalid_command(command_executor):
    """Test executing an invalid/non-existent command."""
    request = CommandRequest(
        command="nonexistent_command_12345",
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code != 0
    assert len(result.stderr) > 0  # Should have error message


@pytest.mark.asyncio
async def test_execute_command_with_stderr(command_executor):
    """Test executing a command that produces stderr output."""
    request = CommandRequest(
        command="echo 'error message' >&2",
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "error message" in result.stderr
    assert result.stdout == ""


@pytest.mark.asyncio
async def test_execute_command_captures_both_stdout_and_stderr(command_executor):
    """Test that commands capture both stdout and stderr."""
    request = CommandRequest(
        command="echo 'stdout'; echo 'stderr' >&2",
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "stdout" in result.stdout
    assert "stderr" in result.stderr


@pytest.mark.asyncio
async def test_execute_command_no_capture_output(command_executor):
    """Test executing a command with output capture disabled."""
    request = CommandRequest(
        command="echo 'hello world'",
        capture_output=False,
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    # When capture_output is False, stdout/stderr should be empty or minimal
    assert result.stdout == "" or result.stderr == ""


@pytest.mark.asyncio
async def test_command_execution_timing(command_executor):
    """Test that execution timing is accurate."""
    request = CommandRequest(
        command="sleep 0.1",
        timeout=2
    )
    
    start_time = datetime.now()
    result = await command_executor.execute(request)
    end_time = datetime.now()
    
    assert result.exit_code == 0
    assert result.execution_time >= 0.1  # Should take at least 0.1 seconds
    assert result.execution_time <= 0.5  # Should not take much more than 0.1 seconds
    
    # Check that timing fields are reasonable
    total_time = (end_time - start_time).total_seconds()
    assert abs(result.execution_time - total_time) < 0.5  # Should be close


@pytest.mark.asyncio
async def test_concurrent_command_execution(command_executor):
    """Test that multiple commands can be executed concurrently."""
    requests = [
        CommandRequest(command="echo 'command1'", timeout=10),
        CommandRequest(command="echo 'command2'", timeout=10),
        CommandRequest(command="echo 'command3'", timeout=10),
    ]
    
    # Execute all commands concurrently
    results = await asyncio.gather(*[
        command_executor.execute(req) for req in requests
    ])
    
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result.exit_code == 0
        assert f"command{i+1}" in result.stdout


@pytest.mark.asyncio
async def test_execute_command_with_special_characters(command_executor):
    """Test executing commands with special characters."""
    request = CommandRequest(
        command="echo 'Hello & World | Test > Output'",
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "Hello & World | Test > Output" in result.stdout


@pytest.mark.asyncio
async def test_execute_command_with_unicode(command_executor):
    """Test executing commands with unicode characters."""
    request = CommandRequest(
        command="echo '🚀 Unicode test 中文 🎯'",
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "🚀 Unicode test 中文 🎯" in result.stdout


@pytest.mark.asyncio
async def test_execute_command_resource_cleanup(command_executor):
    """Test that resources are properly cleaned up after command execution."""
    request = CommandRequest(
        command="echo 'test'",
        timeout=10
    )
    
    # Execute multiple commands to ensure no resource leaks
    for _ in range(10):
        result = await command_executor.execute(request)
        assert result.exit_code == 0
    
    # This test mainly ensures no exceptions are raised
    # and that the system doesn't run out of resources 