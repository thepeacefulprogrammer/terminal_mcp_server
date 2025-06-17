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