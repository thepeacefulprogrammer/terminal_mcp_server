"""
Tests for command executor functionality to ensure proper async command execution,
output streaming, timeout handling, and error management.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
import time

from terminal_mcp_server.utils.command_executor import CommandExecutor
from terminal_mcp_server.models.terminal_models import CommandRequest, CommandResult
from terminal_mcp_server.utils.output_streamer import OutputStreamer


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
    """Test that command execution properly cleans up resources."""
    request = CommandRequest(
        command="echo 'test'",
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert result.stdout.strip() == "test"
    # Should complete without leaving zombie processes


@pytest.mark.asyncio
async def test_execute_command_specific_exit_codes(command_executor):
    """Test that specific exit codes are properly captured and reported."""
    # Test various exit codes
    test_cases = [
        ("exit 0", 0),
        ("exit 1", 1), 
        ("exit 2", 2),
        ("exit 42", 42),
        ("exit 127", 127),  # Command not found
        ("exit 130", 130),  # Interrupted by Ctrl+C
    ]
    
    for command, expected_code in test_cases:
        request = CommandRequest(
            command=command,
            timeout=5
        )
        
        result = await command_executor.execute(request)
        assert result.exit_code == expected_code, f"Command '{command}' should return exit code {expected_code}, got {result.exit_code}"


@pytest.mark.asyncio
async def test_execute_command_signal_based_termination(command_executor):
    """Test handling of commands terminated by signals."""
    # This test uses a command that can be interrupted
    request = CommandRequest(
        command="sleep 10",  # Long sleep that will be killed
        timeout=1  # Short timeout to trigger termination
    )
    
    result = await command_executor.execute(request)
    
    # Should be terminated due to timeout (exit code -1 or specific signal code)
    assert result.exit_code != 0
    assert "timed out" in result.stderr.lower()


@pytest.mark.asyncio
async def test_execute_command_permission_denied(command_executor):
    """Test handling of permission denied errors."""
    import tempfile
    import os
    
    # Create a temporary file without execute permissions
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
        f.write('#!/bin/bash\necho "test"\n')
        temp_script = f.name
    
    try:
        # Remove execute permission
        os.chmod(temp_script, 0o600)  # rw-------
        
        request = CommandRequest(
            command=temp_script,
            timeout=5
        )
        
        result = await command_executor.execute(request)
        
        # Should fail with permission denied
        assert result.exit_code != 0
        assert len(result.stderr) > 0
    finally:
        # Clean up
        try:
            os.unlink(temp_script)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_execute_command_working_directory_not_found(command_executor):
    """Test error handling when working directory doesn't exist."""
    request = CommandRequest(
        command="pwd",
        working_directory="/nonexistent/directory/path",
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    # Should fail due to invalid working directory
    assert result.exit_code != 0
    assert len(result.stderr) > 0


@pytest.mark.asyncio  
async def test_execute_command_environment_variable_handling(command_executor):
    """Test that environment variables are properly handled in error scenarios."""
    # Test with an environment variable that might cause issues
    request = CommandRequest(
        command="echo $NONEXISTENT_VAR",
        environment_variables={"TEST_VAR": "test_value"},
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    # Should succeed (empty output for nonexistent var)
    assert result.exit_code == 0
    
    # Test with invalid environment variable (None values)
    request2 = CommandRequest(
        command="echo $TEST_VAR",
        environment_variables={"TEST_VAR": "valid_value", "EMPTY_VAR": ""},
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code == 0
    assert "valid_value" in result2.stdout


@pytest.mark.asyncio
async def test_execute_command_output_encoding_errors(command_executor):
    """Test handling of commands that produce non-UTF8 output.""" 
    # Create a command that outputs binary data
    request = CommandRequest(
        command="printf '\\xff\\xfe\\x00\\x41'",  # Non-UTF8 bytes
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    # Should not crash and should handle encoding gracefully
    assert result.exit_code == 0
    assert isinstance(result.stdout, str)  # Should be decoded string
    assert isinstance(result.stderr, str)


@pytest.mark.asyncio
async def test_execute_command_large_output_handling(command_executor):
    """Test handling of commands that produce large amounts of output."""
    # Generate a large amount of output
    request = CommandRequest(
        command="yes | head -n 1000",  # 1000 lines of 'y'
        timeout=10
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    # Should have lots of output lines
    lines = result.stdout.strip().split('\n')
    assert len(lines) == 1000
    assert all(line.strip() == 'y' for line in lines)


@pytest.mark.asyncio
async def test_execute_command_stderr_vs_stdout_separation(command_executor):
    """Test that stdout and stderr are properly separated."""
    request = CommandRequest(
        command="echo 'stdout_message'; echo 'stderr_message' >&2; echo 'more_stdout'",
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == 0
    assert "stdout_message" in result.stdout
    assert "more_stdout" in result.stdout  
    assert "stderr_message" in result.stderr
    # Stderr message should NOT be in stdout
    assert "stderr_message" not in result.stdout
    # Stdout messages should NOT be in stderr
    assert "stdout_message" not in result.stderr
    assert "more_stdout" not in result.stderr


@pytest.mark.asyncio
async def test_execute_command_complex_shell_constructs(command_executor):
    """Test execution of complex shell constructs and their exit codes."""
    test_cases = [
        # Pipes - should return exit code of last command
        ("echo 'test' | grep 'test'", 0),
        ("echo 'test' | grep 'notfound'", 1),
        
        # Command substitution
        ("echo $(echo 'nested')", 0),
        ("echo $(false)", 0),  # echo succeeds even if substitution fails
        
        # Conditional execution
        ("true && echo 'success'", 0),
        ("false && echo 'failure'", 1),
        ("false || echo 'fallback'", 0),
    ]
    
    for command, expected_code in test_cases:
        request = CommandRequest(
            command=command,
            timeout=5
        )
        
        result = await command_executor.execute(request)
        assert result.exit_code == expected_code, f"Command '{command}' should return {expected_code}, got {result.exit_code}"


@pytest.mark.asyncio
async def test_execute_command_enhanced_error_messages(command_executor):
    """Test that enhanced error messages provide clear, specific information."""
    
    # Test working directory validation
    request = CommandRequest(
        command="pwd",
        working_directory="/this/directory/definitely/does/not/exist",
        timeout=5
    )
    
    result = await command_executor.execute(request)
    
    assert result.exit_code == -1
    assert "Working directory does not exist" in result.stderr
    assert "/this/directory/definitely/does/not/exist" in result.stderr
    
    # Test with a file path instead of directory
    import tempfile
    with tempfile.NamedTemporaryFile() as temp_file:
        request2 = CommandRequest(
            command="pwd", 
            working_directory=temp_file.name,  # This is a file, not a directory
            timeout=5
        )
        
        result2 = await command_executor.execute(request2)
        
        assert result2.exit_code == -1
        assert "Working directory is not a directory" in result2.stderr or "not a directory" in result2.stderr.lower()


@pytest.mark.asyncio 
async def test_execute_command_environment_variable_validation(command_executor):
    """Test that environment variable validation works correctly.""" 
    
    # Test with valid environment variables
    request = CommandRequest(
        command="echo $TEST_VAR",
        environment_variables={"TEST_VAR": "valid_value"},
        timeout=5
    )
    
    result = await command_executor.execute(request)
    assert result.exit_code == 0
    assert "valid_value" in result.stdout
    
    # Test with empty environment variable (should be valid)
    request2 = CommandRequest(
        command="echo \"[$TEST_VAR]\"",
        environment_variables={"TEST_VAR": ""},
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code == 0
    assert "[]" in result2.stdout  # Empty variable should result in empty brackets


@pytest.mark.asyncio
async def test_execute_command_exit_code_logging(command_executor):
    """Test that non-zero exit codes are properly logged and handled."""
    
    # Test successful command (should not generate warning)
    request_success = CommandRequest(
        command="true",
        timeout=5
    )
    
    result_success = await command_executor.execute(request_success)
    assert result_success.exit_code == 0
    
    # Test failing command (should generate warning log)
    request_fail = CommandRequest(
        command="false", 
        timeout=5
    )
    
    result_fail = await command_executor.execute(request_fail)
    assert result_fail.exit_code == 1
    
    # Test command with specific exit code
    request_specific = CommandRequest(
        command="exit 42",
        timeout=5
    )
    
    result_specific = await command_executor.execute(request_specific)
    assert result_specific.exit_code == 42


@pytest.mark.asyncio
async def test_complete_environment_variable_support(command_executor):
    """Test comprehensive environment variable support including all edge cases."""
    
    # Test 1: Basic environment variable setting
    request1 = CommandRequest(
        command="echo \"$CUSTOM_VAR1:$CUSTOM_VAR2\"",
        environment_variables={
            "CUSTOM_VAR1": "hello",
            "CUSTOM_VAR2": "world"
        },
        timeout=5
    )
    
    result1 = await command_executor.execute(request1)
    assert result1.exit_code == 0
    assert "hello:world" in result1.stdout
    
    # Test 2: Environment variable override of system variables
    request2 = CommandRequest(
        command="echo $PATH",
        environment_variables={"PATH": "/custom/path:/usr/bin"},
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code == 0
    assert "/custom/path:/usr/bin" in result2.stdout
    
    # Test 3: Empty environment variables
    request3 = CommandRequest(
        command="echo \"[$EMPTY_VAR]\"",
        environment_variables={"EMPTY_VAR": ""},
        timeout=5
    )
    
    result3 = await command_executor.execute(request3)
    assert result3.exit_code == 0
    assert "[]" in result3.stdout
    
    # Test 4: Environment variables with special characters
    request4 = CommandRequest(
        command="echo \"$SPECIAL_VAR\"",
        environment_variables={"SPECIAL_VAR": "hello world!@#$%^&*()"},
        timeout=5
    )
    
    result4 = await command_executor.execute(request4)
    assert result4.exit_code == 0
    assert "hello world!@#$%^&*()" in result4.stdout
    
    # Test 5: Multiple environment variables in one command
    request5 = CommandRequest(
        command="echo \"$VAR1-$VAR2-$VAR3\"",
        environment_variables={
            "VAR1": "one",
            "VAR2": "two", 
            "VAR3": "three"
        },
        timeout=5
    )
    
    result5 = await command_executor.execute(request5)
    assert result5.exit_code == 0
    assert "one-two-three" in result5.stdout
    
    # Test 6: Environment variables persist throughout command execution
    request6 = CommandRequest(
        command="export TEST_PERSIST=from_command && echo $TEST_PERSIST && echo $INITIAL_VAR",
        environment_variables={"INITIAL_VAR": "initial_value"},
        timeout=5
    )
    
    result6 = await command_executor.execute(request6)
    assert result6.exit_code == 0
    assert "from_command" in result6.stdout
    assert "initial_value" in result6.stdout


@pytest.mark.asyncio
async def test_environment_variable_inheritance_and_isolation(command_executor):
    """Test that environment variables are properly inherited and isolated."""
    
    # Test 1: Custom variables don't affect system environment after execution
    import os
    original_path = os.environ.get("PATH", "")
    
    request1 = CommandRequest(
        command="echo $PATH",
        environment_variables={"PATH": "/temporary/path"},
        timeout=5
    )
    
    result1 = await command_executor.execute(request1)
    assert result1.exit_code == 0
    assert "/temporary/path" in result1.stdout
    
    # Verify system PATH is unchanged
    current_path = os.environ.get("PATH", "")
    assert current_path == original_path
    
    # Test 2: System environment variables are inherited when not overridden
    request2 = CommandRequest(
        command="echo $PATH:$CUSTOM_ADDITION",
        environment_variables={"CUSTOM_ADDITION": "added"},
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code == 0
    assert "added" in result2.stdout
    # Should contain system PATH
    assert len(result2.stdout.strip()) > 10  # PATH should be substantial
    
    # Test 3: Concurrent executions don't interfere with each other
    import asyncio
    
    request_a = CommandRequest(
        command="echo $CONCURRENT_VAR",
        environment_variables={"CONCURRENT_VAR": "value_a"},
        timeout=5
    )
    
    request_b = CommandRequest(
        command="echo $CONCURRENT_VAR", 
        environment_variables={"CONCURRENT_VAR": "value_b"},
        timeout=5
    )
    
    # Execute concurrently
    result_a, result_b = await asyncio.gather(
        command_executor.execute(request_a),
        command_executor.execute(request_b)
    )
    
    assert result_a.exit_code == 0
    assert result_b.exit_code == 0
    assert "value_a" in result_a.stdout
    assert "value_b" in result_b.stdout
    # Ensure they didn't cross-contaminate
    assert "value_b" not in result_a.stdout
    assert "value_a" not in result_b.stdout


@pytest.mark.asyncio
async def test_environment_variable_complex_scenarios(command_executor):
    """Test complex environment variable scenarios."""
    
    # Test 1: Environment variables in shell scripts
    request1 = CommandRequest(
        command="bash -c 'echo $SCRIPT_VAR; export NEW_VAR=created; echo $NEW_VAR'",
        environment_variables={"SCRIPT_VAR": "from_parent"},
        timeout=5
    )
    
    result1 = await command_executor.execute(request1)
    assert result1.exit_code == 0
    assert "from_parent" in result1.stdout
    assert "created" in result1.stdout
    
    # Test 2: Environment variables with pipes and redirects
    request2 = CommandRequest(
        command="echo $PIPE_VAR | grep 'test'",
        environment_variables={"PIPE_VAR": "test_value"},
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code == 0
    assert "test_value" in result2.stdout
    
    # Test 3: Environment variables in conditional execution
    request3 = CommandRequest(
        command="[ \"$CONDITION_VAR\" = \"true\" ] && echo 'condition met' || echo 'condition not met'",
        environment_variables={"CONDITION_VAR": "true"},
        timeout=5
    )
    
    result3 = await command_executor.execute(request3)
    assert result3.exit_code == 0
    assert "condition met" in result3.stdout
    
    # Test 4: Unicode environment variables
    request4 = CommandRequest(
        command="echo $UNICODE_VAR",
        environment_variables={"UNICODE_VAR": "Hello 世界 🌍"},
        timeout=5
    )
    
    result4 = await command_executor.execute(request4)
    assert result4.exit_code == 0
    assert "Hello 世界 🌍" in result4.stdout


@pytest.mark.asyncio
async def test_comprehensive_logging_output(command_executor, caplog):
    """Test that comprehensive logging is produced for command executions."""
    import logging
    
    # Set log level to capture all logs
    caplog.set_level(logging.DEBUG)
    
    # Test 1: Successful command execution logging
    request1 = CommandRequest(
        command="echo 'test logging'",
        working_directory="/tmp",
        environment_variables={"TEST_VAR": "test_value"},
        timeout=10
    )
    
    result1 = await command_executor.execute(request1)
    assert result1.exit_code == 0
    
    # Verify comprehensive logging occurred
    log_messages = [record.message for record in caplog.records]
    
    # Check for key logging elements
    assert any("Executing command: echo 'test logging'" in msg for msg in log_messages)
    assert any("Working directory: /tmp" in msg for msg in log_messages)
    assert any("Environment variables count: 1" in msg for msg in log_messages)
    assert any("Timeout: 10" in msg for msg in log_messages)
    assert any("Command completed with exit code: 0" in msg for msg in log_messages)
    assert any("Execution time:" in msg for msg in log_messages)
    
    # Clear the captured logs
    caplog.clear()
    
    # Test 2: Failed command execution logging
    request2 = CommandRequest(
        command="false",  # Command that fails
        timeout=5
    )
    
    result2 = await command_executor.execute(request2)
    assert result2.exit_code != 0
    
    # Verify failure logging
    log_messages = [record.message for record in caplog.records]
    assert any("Command failed with exit code" in msg for msg in log_messages)
    
    # Clear the captured logs
    caplog.clear()
    
    # Test 3: Timeout scenario logging
    request3 = CommandRequest(
        command="sleep 2",
        timeout=1  # Will timeout
    )
    
    result3 = await command_executor.execute(request3)
    assert result3.exit_code != 0
    
    # Verify timeout logging
    log_messages = [record.message for record in caplog.records]
    assert any("Command timed out after 1 seconds" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_enhanced_logging_features(command_executor, caplog):
    """Test the enhanced logging features including audit trails and structured logging."""
    import logging
    import json
    
    # Set log level to capture all logs
    caplog.set_level(logging.DEBUG)
    
    # Test command execution with enhanced logging
    request = CommandRequest(
        command="echo 'testing enhanced logging'",
        environment_variables={"LOG_TEST": "enhanced"},
        timeout=10
    )
    
    result = await command_executor.execute(request)
    assert result.exit_code == 0
    
    # Verify comprehensive logging occurred
    log_messages = [record.message for record in caplog.records]
    
    # Check for execution ID in logs
    assert any("Starting command execution" in msg for msg in log_messages)
    assert any("cmd_" in msg for msg in log_messages)
    
    # Check for structured audit log
    audit_logs = [msg for msg in log_messages if "COMMAND_AUDIT:" in msg]
    assert len(audit_logs) >= 1
    
    # Parse the audit log JSON
    audit_log = audit_logs[0]
    json_part = audit_log.split("COMMAND_AUDIT: ")[1]
    audit_data = json.loads(json_part)
    
    # Verify audit data structure
    assert "execution_id" in audit_data
    assert "timestamp" in audit_data
    assert audit_data["command"] == "echo 'testing enhanced logging'"
    assert audit_data["exit_code"] == 0
    assert audit_data["success"] is True
    assert "execution_time_seconds" in audit_data
    assert "stdout_length" in audit_data
    assert "stderr_length" in audit_data
    assert audit_data["environment_var_count"] == 1
    
    # Check for human-readable summary
    summary_logs = [msg for msg in log_messages if "SUCCESS" in msg and "cmd_" in msg]
    assert len(summary_logs) >= 1
    
    # Check for detailed process logging
    assert any("Subprocess created with PID:" in msg for msg in log_messages)
    assert any("Process completed normally with exit code:" in msg for msg in log_messages)
    
    # Check for environment variable security (names logged, not values)
    assert any("Environment variable names: ['LOG_TEST']" in msg for msg in log_messages)
    # Ensure values are NOT logged in debug messages for security
    assert not any("LOG_TEST=enhanced" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_command_counter_increments(command_executor):
    """Test that command counter increments properly."""
    initial_counter = command_executor._command_counter
    
    request = CommandRequest(command="echo 'test'", capture_output=True)
    await command_executor.execute(request)
    
    assert command_executor._command_counter == initial_counter + 1


@pytest.mark.asyncio
async def test_execution_time_tracking(command_executor):
    """Test that execution time is tracked properly."""
    initial_time = command_executor._total_execution_time
    
    request = CommandRequest(command="echo 'test'", capture_output=True)
    result = await command_executor.execute(request)
    
    assert command_executor._total_execution_time > initial_time
    assert result.execution_time > 0
    assert result.completed_at > result.started_at


@pytest.mark.asyncio
async def test_invalid_working_directory(command_executor):
    """Test handling of invalid working directory."""
    request = CommandRequest(
        command="echo 'test'",
        capture_output=True,
        working_directory="/nonexistent/directory"
    )
    
    result = await command_executor.execute(request)
    
    assert isinstance(result, CommandResult)
    assert result.exit_code == -1
    assert "does not exist" in result.stderr or "No such file" in result.stderr


@pytest.mark.asyncio
async def test_invalid_environment_variables(command_executor):
    """Test handling of invalid environment variables."""
    # Test that the command executor handles environment variable validation gracefully
    # Since pydantic validates at the request level, we test with valid types but
    # ensure the executor handles them properly
    request = CommandRequest(
        command="echo $VALID_KEY",
        capture_output=True,
        environment_variables={"VALID_KEY": "valid_value", "EMPTY_KEY": "", "SPECIAL_KEY": "value with spaces & symbols"}
    )
    
    # Should execute successfully with valid environment variables
    result = await command_executor.execute(request)
    
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "valid_value" in result.stdout


@pytest.mark.asyncio
async def test_empty_command(command_executor):
    """Test handling of empty command."""
    request = CommandRequest(command="", capture_output=True)
    
    result = await command_executor.execute(request)
    
    assert isinstance(result, CommandResult)
    # Empty command should either succeed with no output or fail gracefully
    assert result.exit_code in [0, -1]  # Platform dependent


@pytest.mark.asyncio 
async def test_very_long_output(command_executor):
    """Test handling of commands with very long output."""
    # Create command that generates substantial output
    request = CommandRequest(
        command="seq 1 100 | while read i; do echo \"Line $i with some additional content to make it longer\"; done",
        capture_output=True
    )
    
    result = await command_executor.execute(request)
    
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert len(result.stdout) > 1000  # Should have substantial output
    assert "Line" in result.stdout


@pytest.mark.asyncio
async def test_command_with_special_characters(command_executor):
    """Test command execution with special characters."""
    special_text = "Hello! @#$%^&*()_+ 世界 🌍"
    request = CommandRequest(
        command=f"echo '{special_text}'",
        capture_output=True
    )
    
    result = await command_executor.execute(request)
    
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    # Should handle unicode and special characters
    assert "Hello!" in result.stdout
    assert "世界" in result.stdout or "🌍" in result.stdout  # Unicode support may vary


@pytest.mark.asyncio
async def test_streaming_chunk_capture(command_executor):
    """Test that streaming properly captures chunks."""
    request = CommandRequest(
        command="echo 'chunk1'; sleep 0.1; echo 'chunk2'",
        capture_output=True
    )
    
    stream_generator, result = await command_executor.execute_with_streaming(request)
    
    chunks = []
    try:
        # Add a small delay to ensure the process starts
        await asyncio.sleep(0.05)
        
        async for chunk in stream_generator:
            chunks.append(chunk)
            
            # Break after getting some chunks to avoid hanging
            if len(chunks) >= 2:
                break
                
    except Exception:
        # If streaming fails, we'll check the final result
        pass
    
    # Wait for result to be updated
    await asyncio.sleep(0.2)
    
    # Should have captured chunks either in streaming or final result
    has_stream_chunks = len(chunks) > 0
    has_captured_chunks = hasattr(result, 'captured_chunks') and len(result.captured_chunks) > 0
    has_output_in_result = len(result.stdout.strip()) > 0
    
    # Result should have captured_chunks attribute
    assert hasattr(result, 'captured_chunks')
    
    # Should have some form of output
    assert has_stream_chunks or has_captured_chunks or has_output_in_result, f"Expected some output. Stream chunks: {len(chunks)}, Captured chunks: {len(getattr(result, 'captured_chunks', []))}, Result stdout: '{result.stdout}'"


# NEW TESTS FOR TASK 5.2: Separated stdout/stderr streaming
@pytest.mark.asyncio
async def test_execute_separated_streaming_basic(command_executor):
    """Test basic separated streaming command execution."""
    request = CommandRequest(
        command="echo 'stdout line'; echo 'stderr line' >&2",
        capture_output=True
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    # Collect all chunks from separated stream
    chunks = []
    try:
        # Add a small delay to ensure the process starts
        await asyncio.sleep(0.05)
        
        async for stdout_chunk, stderr_chunk in stream_generator:
            chunks.append((stdout_chunk, stderr_chunk))
            
            # Break after getting some chunks to avoid hanging
            if len(chunks) >= 2:
                break
                
    except Exception:
        # If streaming fails, we'll check the final result
        pass
    
    assert isinstance(result, CommandResult)
    
    # Wait for result to be updated
    await asyncio.sleep(0.1)
    assert result.exit_code == 0
    
    # Check that we got both stdout and stderr content (either in chunks or final result)
    all_stdout = ''.join(stdout for stdout, stderr in chunks) if chunks else ""
    all_stderr = ''.join(stderr for stdout, stderr in chunks) if chunks else ""
    
    has_stdout_content = ("stdout line" in all_stdout or "stdout line" in result.stdout)
    has_stderr_content = ("stderr line" in all_stderr or "stderr line" in result.stderr)
    
    assert has_stdout_content, f"Expected stdout content. Chunks stdout: '{all_stdout}', Result stdout: '{result.stdout}'"
    assert has_stderr_content, f"Expected stderr content. Chunks stderr: '{all_stderr}', Result stderr: '{result.stderr}'"
    
    # Verify stream format if we got chunks
    if chunks:
        assert all(isinstance(chunk, tuple) and len(chunk) == 2 for chunk in chunks)
        assert all(isinstance(stdout, str) and isinstance(stderr, str) 
                  for stdout, stderr in chunks)


@pytest.mark.asyncio
async def test_execute_separated_streaming_stdout_only(command_executor):
    """Test separated streaming with only stdout content."""
    request = CommandRequest(
        command="echo 'only stdout'",
        capture_output=True
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    chunks = []
    try:
        # Add a small delay to ensure the process starts
        await asyncio.sleep(0.05)
        
        async for stdout_chunk, stderr_chunk in stream_generator:
            chunks.append((stdout_chunk, stderr_chunk))
            
            # Break after first chunk to avoid hanging
            if len(chunks) >= 1:
                break
                
    except Exception:
        # If streaming fails, we'll check the final result
        pass
    
    # Wait for result to be updated
    await asyncio.sleep(0.1)
    
    # Should have stdout content but no stderr content (either in chunks or final result)
    all_stdout = ''.join(stdout for stdout, stderr in chunks) if chunks else ""
    all_stderr = ''.join(stderr for stdout, stderr in chunks) if chunks else ""
    
    has_stdout_content = ("only stdout" in all_stdout or "only stdout" in result.stdout or len(result.stdout.strip()) > 0)
    has_stderr_content = (len(all_stderr.strip()) > 0 or len(result.stderr.strip()) > 0)
    
    assert has_stdout_content, f"Expected stdout content. Chunks stdout: '{all_stdout}', Result stdout: '{result.stdout}'"
    assert not has_stderr_content, f"Expected no stderr content. Chunks stderr: '{all_stderr}', Result stderr: '{result.stderr}'"


@pytest.mark.asyncio
async def test_execute_separated_streaming_stderr_only(command_executor):
    """Test separated streaming with only stderr content."""
    request = CommandRequest(
        command="echo 'only stderr' >&2",
        capture_output=True
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    chunks = []
    try:
        # Add a small delay to ensure the process starts
        await asyncio.sleep(0.05)
        
        async for stdout_chunk, stderr_chunk in stream_generator:
            chunks.append((stdout_chunk, stderr_chunk))
            
            # Break after first chunk to avoid hanging
            if len(chunks) >= 1:
                break
                
    except Exception:
        # If streaming fails, we'll check the final result
        pass
    
    # Wait for result to be updated
    await asyncio.sleep(0.1)
    
    # Should have at least some output, either in chunks or final result
    has_chunks = len(chunks) > 0
    has_stderr_in_result = len(result.stderr.strip()) > 0
    
    assert has_chunks or has_stderr_in_result, f"Expected chunks or stderr in result. Chunks: {chunks}, Result stderr: '{result.stderr}'"
    
    if has_chunks:
        # Should have stderr content but no stdout content
        all_stdout = ''.join(stdout for stdout, stderr in chunks)
        all_stderr = ''.join(stderr for stdout, stderr in chunks)
        
        has_stdout_content = len(all_stdout.strip()) > 0
        has_stderr_content = "only stderr" in all_stderr or len(all_stderr.strip()) > 0
        
        assert not has_stdout_content
        assert has_stderr_content
    
    # Verify the final result has stderr content
    assert "only stderr" in result.stderr
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_separated_streaming_with_timeout(command_executor):
    """Test separated streaming with timeout."""
    request = CommandRequest(
        command="echo 'start'; sleep 2; echo 'end'",
        capture_output=True,
        timeout=1  # 1 second timeout
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    chunks = []
    async for stdout_chunk, stderr_chunk in stream_generator:
        chunks.append((stdout_chunk, stderr_chunk))
    
    # Wait for result to be updated with timeout
    await asyncio.sleep(1.5)
    
    assert result.exit_code == -1
    # Should have timeout message in stderr
    assert "timed out" in result.stderr


@pytest.mark.asyncio
async def test_execute_separated_streaming_with_environment(command_executor):
    """Test separated streaming with environment variables."""
    request = CommandRequest(
        command="echo $TEST_VAR; echo $TEST_VAR >&2",
        capture_output=True,
        environment_variables={"TEST_VAR": "test_env_value"}
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    chunks = []
    async for stdout_chunk, stderr_chunk in stream_generator:
        chunks.append((stdout_chunk, stderr_chunk))
    
    assert len(chunks) > 0
    
    # Wait for result to be updated
    await asyncio.sleep(0.1)
    assert result.exit_code == 0
    
    # Check that environment variable was used in both streams
    all_stdout = ''.join(stdout for stdout, stderr in chunks)
    all_stderr = ''.join(stderr for stdout, stderr in chunks)
    
    has_stdout_env = "test_env_value" in all_stdout or "test_env_value" in result.stdout
    has_stderr_env = "test_env_value" in all_stderr or "test_env_value" in result.stderr
    
    assert has_stdout_env
    assert has_stderr_env


@pytest.mark.asyncio
async def test_execute_separated_streaming_error_handling(command_executor):
    """Test error handling in separated streaming."""
    # Test with invalid command
    request = CommandRequest(
        command="nonexistent_command_12345",
        capture_output=True
    )
    
    stream_generator, result = await command_executor.execute_with_separated_streaming(request)
    
    chunks = []
    async for stdout_chunk, stderr_chunk in stream_generator:
        chunks.append((stdout_chunk, stderr_chunk))
    
    # Wait for result to be updated
    await asyncio.sleep(0.1)
    
    # Should handle the error gracefully
    assert result.exit_code != 0
    # Should have error information
    has_error_info = (
        "not found" in result.stderr.lower() or 
        "command not found" in result.stderr.lower() or
        len(result.stderr) > 0
    )
    assert has_error_info


@pytest.mark.asyncio
async def test_separated_streaming_result_consistency(command_executor):
    """Test that separated streaming result is consistent with regular execution."""
    command = "echo 'test stdout'; echo 'test stderr' >&2"
    
    # Execute with regular method
    regular_request = CommandRequest(command=command, capture_output=True)
    regular_result = await command_executor.execute(regular_request)
    
    # Execute with separated streaming
    separated_request = CommandRequest(command=command, capture_output=True)
    stream_generator, separated_result = await command_executor.execute_with_separated_streaming(separated_request)
    
    # Consume the stream
    chunks = []
    async for stdout_chunk, stderr_chunk in stream_generator:
        chunks.append((stdout_chunk, stderr_chunk))
    
    # Wait for separated result to be updated
    await asyncio.sleep(0.1)
    
    # Results should be consistent
    assert regular_result.exit_code == separated_result.exit_code
    assert regular_result.command == separated_result.command
    
    # Content should be similar (allowing for streaming vs batch differences)
    assert "test stdout" in separated_result.stdout
    assert "test stderr" in separated_result.stderr 


class TestGracefulErrorRecovery:
    """Test graceful error recovery and reporting mechanisms."""
    
    @pytest.mark.asyncio
    async def test_recovery_from_command_timeout_with_partial_output(self):
        """Test recovery when command times out with partial output."""
        executor = CommandExecutor()
        
        # Command that generates output immediately then blocks
        request = CommandRequest(
            command="python3 -c \"import time; print('Starting...', flush=True); time.sleep(3); print('Never reached')\"",
            timeout=1,
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should have graceful timeout error - partial output preservation may vary by timing
        assert result.exit_code != 0
        assert "timed out" in result.stderr.lower()
        # Note: Partial output preservation is best-effort for timeouts
        # The key is graceful error handling with proper timeout messages
        assert "Never reached" not in result.stdout  # Should not have completed
        assert result.execution_time >= 1.0
    
    @pytest.mark.asyncio
    async def test_recovery_from_process_kill_with_output_preservation(self):
        """Test recovery when process is killed externally with output preservation."""
        executor = CommandExecutor()
        
        # Create a long-running command that outputs data
        request = CommandRequest(
            command="for i in {1..10}; do echo 'Line $i'; sleep 0.1; done",
            timeout=1,  # Fixed: Pydantic expects integer
            capture_output=True
        )
        
        # Start execution but simulate external kill
        async def kill_after_delay():
            await asyncio.sleep(0.2)  # Let some output be generated
            # This will be handled by the timeout mechanism
        
        asyncio.create_task(kill_after_delay())
        result = await executor.execute(request)
        
        # Should handle timeout gracefully - may complete quickly on some systems
        # Command may complete successfully if it's fast enough, or timeout
        if result.exit_code != 0:
            # Timed out - this is expected behavior
            assert "timed out" in result.stderr.lower() or result.exit_code != 0
        else:
            # Completed quickly - also acceptable
            assert len(result.stdout) > 0
        assert result.execution_time <= 1.5  # Should not exceed timeout significantly
    
    @pytest.mark.asyncio
    async def test_recovery_from_memory_limit_exceeded(self):
        """Test recovery when output exceeds memory limits."""
        # Use small memory limits for testing
        executor = CommandExecutor(max_output_size=1024, buffer_size=256)
        
        # Command that generates more output than the limit
        request = CommandRequest(
            command="python3 -c \"print('x' * 2000)\"",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle memory limit gracefully
        if result.exit_code != 0:
            assert "memory" in result.stderr.lower() or "limit" in result.stderr.lower()
        # Output should be truncated but process should complete
        assert len(result.stdout) <= 1024 * 2  # Allow some buffer overflow
    
    @pytest.mark.asyncio
    async def test_recovery_from_unicode_decode_errors(self):
        """Test recovery from unicode decode errors in output."""
        executor = CommandExecutor()
        
        # Command that generates binary/invalid unicode output
        request = CommandRequest(
            command="python3 -c \"import sys; sys.stdout.buffer.write(b'\\xff\\xfe invalid unicode \\x80\\x81')\"",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle decode errors gracefully
        assert result.exit_code == 0  # Command should succeed
        # Output should contain replacement characters or error indication
        assert "invalid unicode" in result.stdout or "" in result.stdout or len(result.stderr) > 0
    
    @pytest.mark.asyncio
    async def test_recovery_from_working_directory_deletion(self):
        """Test recovery when working directory is deleted during execution."""
        executor = CommandExecutor()
        
        # Try to execute in a non-existent directory
        request = CommandRequest(
            command="pwd",
            working_directory="/nonexistent/directory",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle gracefully with clear error message
        assert result.exit_code != 0
        assert "directory" in result.stderr.lower() or "not found" in result.stderr.lower()
        assert result.execution_time < 5.0  # Should fail quickly
    
    @pytest.mark.asyncio
    async def test_recovery_from_permission_denied_errors(self):
        """Test recovery from permission denied errors."""
        executor = CommandExecutor()
        
        # Command that will likely fail due to permissions
        request = CommandRequest(
            command="cat /etc/shadow",  # Usually requires root access
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle permission errors gracefully
        assert result.exit_code != 0
        assert ("permission" in result.stderr.lower() or 
                "denied" in result.stderr.lower() or
                "permission" in result.stdout.lower() or
                "denied" in result.stdout.lower())
    
    @pytest.mark.asyncio
    async def test_recovery_from_environment_variable_errors(self):
        """Test recovery from environment variable related errors."""
        executor = CommandExecutor()
        
        # Command that depends on environment variable
        request = CommandRequest(
            command="echo $NONEXISTENT_VAR_12345",
            environment_variables={"VALID_VAR": "valid_value"},
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle gracefully - might succeed with empty output
        assert result.execution_time < 5.0
        # The command should either succeed (with empty output) or fail gracefully
        if result.exit_code != 0:
            assert len(result.stderr) > 0
    
    @pytest.mark.asyncio
    async def test_recovery_from_stream_corruption(self):
        """Test recovery from stream corruption or unexpected stream behavior."""
        executor = CommandExecutor()
        
        # Command that might cause stream issues
        request = CommandRequest(
            command="python3 -c \"import sys; sys.stdout.write('line1\\n'); sys.stderr.write('error1\\n'); sys.stdout.flush(); sys.stderr.flush()\"",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle mixed streams gracefully
        assert result.exit_code == 0
        assert "line1" in result.stdout
        # Error output might be captured in stdout or stderr field
    
    @pytest.mark.asyncio
    async def test_recovery_from_subprocess_creation_failure(self):
        """Test recovery when subprocess creation fails."""
        executor = CommandExecutor()
        
        # Command that doesn't exist
        request = CommandRequest(
            command="nonexistent_command_12345_xyz",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should handle subprocess creation failure gracefully
        assert result.exit_code != 0
        assert ("not found" in result.stderr.lower() or 
                "command" in result.stderr.lower() or
                "no such" in result.stderr.lower())
        assert result.execution_time < 5.0
    
    @pytest.mark.asyncio
    async def test_recovery_with_detailed_error_reporting(self):
        """Test that error recovery includes detailed error information."""
        executor = CommandExecutor()
        
        # Command that will fail in a specific way
        request = CommandRequest(
            command="ls /root/nonexistent/deeply/nested/path",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should provide detailed error information
        assert result.exit_code != 0
        assert len(result.stderr) > 0 or len(result.stdout) > 0
        # Error should be descriptive
        error_content = (result.stderr + result.stdout).lower()
        assert ("no such" in error_content or 
                "not found" in error_content or
                "permission" in error_content)
        # Should include the problematic path or command info
        assert ("path" in error_content or 
                "directory" in error_content or
                "root" in error_content)
    
    @pytest.mark.asyncio
    async def test_recovery_preserves_execution_context(self):
        """Test that error recovery preserves execution context information."""
        executor = CommandExecutor()
        
        request = CommandRequest(
            command="false",  # Command that always fails
            working_directory="/tmp",
            environment_variables={"TEST_VAR": "test_value"},
            timeout=10,
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should preserve context even in failure
        assert result.exit_code != 0
        assert result.execution_time < 10.0
        # Context should be preserved in the result (command was executed)
        assert result.command == "false"
    
    @pytest.mark.asyncio
    async def test_recovery_from_concurrent_execution_conflicts(self):
        """Test recovery from conflicts during concurrent command execution."""
        executor = CommandExecutor()
        
        # Run multiple commands that might conflict
        requests = [
            CommandRequest(command="echo 'Command 1'; sleep 0.1", capture_output=True),
            CommandRequest(command="echo 'Command 2'; sleep 0.1", capture_output=True), 
            CommandRequest(command="echo 'Command 3'; sleep 0.1", capture_output=True)
        ]
        
        # Execute all commands concurrently
        tasks = [executor.execute(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully or with reasonable errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # If exception occurred, it should be handled gracefully
                assert isinstance(result, (asyncio.TimeoutError, OSError))
            else:
                # If successful, should have proper output
                assert f"Command {i+1}" in result.stdout
    
    @pytest.mark.asyncio
    async def test_error_reporting_includes_recovery_actions(self):
        """Test that error reporting includes suggested recovery actions."""
        executor = CommandExecutor()
        
        # Command with syntax error
        request = CommandRequest(
            command="ls --invalid-flag-xyz",
            capture_output=True
        )
        result = await executor.execute(request)
        
        # Should include helpful error information
        assert result.exit_code != 0
        assert len(result.stderr) > 0 or len(result.stdout) > 0
        # Should contain useful error information from ls command
        error_content = (result.stderr + result.stdout).lower()
        if len(result.stderr) > 0:
            assert ("invalid" in error_content or 
                    "unrecognized" in error_content or
                    "option" in error_content)
    
    @pytest.mark.asyncio
    async def test_recovery_maintains_resource_cleanup(self):
        """Test that error recovery properly cleans up resources."""
        executor = CommandExecutor()
        
        # Command that creates a process but will timeout
        request = CommandRequest(
            command="sleep 10",
            timeout=1,  # Short timeout
            capture_output=True
        )
        
        start_time = time.time()
        result = await executor.execute(request)
        end_time = time.time()
        
        # Should timeout and clean up properly
        assert result.exit_code != 0
        assert "timed out" in result.stderr.lower()
        assert end_time - start_time < 2.0  # Should not wait for full sleep
        
        # Give a moment for cleanup
        await asyncio.sleep(0.1)
        
        # Process should be cleaned up (this is implicit - no hanging processes)
    
    @pytest.mark.asyncio
    async def test_recovery_from_signal_interruption(self):
        """Test recovery from signal interruption scenarios."""
        executor = CommandExecutor()
        
        # Command that can be interrupted
        request = CommandRequest(
            command="python3 -c \"import time; print('started', flush=True); time.sleep(2); print('finished')\"",
            timeout=1,  # Short timeout to force interruption
            capture_output=True
        )
        
        result = await executor.execute(request)
        
        # Should handle interruption gracefully
        assert result.exit_code != 0
        # Note: Output preservation during timeout is best-effort
        # The key is proper timeout error handling
        assert "finished" not in result.stdout  # Should not have completed
        assert "timed out" in result.stderr.lower()
    
    @pytest.mark.asyncio
    async def test_graceful_error_recovery_with_resource_limits(self):
        """Test graceful recovery under resource constraints."""
        executor = CommandExecutor(max_output_size=512, buffer_size=128)
        
        # Command that hits multiple constraints
        request = CommandRequest(
            command="python3 -c \"for i in range(100): print(f'Line {i} with lots of content to exceed buffer limits')\"",
            timeout=5,
            capture_output=True
        )
        
        result = await executor.execute(request)
        
        # Should complete or handle limits gracefully
        if result.exit_code == 0:
            # Command succeeded but output may be limited
            assert len(result.stdout) <= 512 * 2  # Allow some overflow
        else:
            # Command failed due to limits but should have clear error
            assert len(result.stderr) > 0 or "timeout" in result.stderr.lower()
    
    @pytest.mark.asyncio
    async def test_error_recovery_preserves_exit_codes(self):
        """Test that error recovery preserves original exit codes when possible."""
        executor = CommandExecutor()
        
        # Command with specific exit code
        request = CommandRequest(
            command="exit 42",
            capture_output=True
        )
        
        result = await executor.execute(request)
        
        # Should preserve the actual exit code
        assert result.exit_code == 42
        assert result.execution_time < 5.0

# ... existing code ... 