"""Tests for Terminal MCP Server models."""

import pytest
from datetime import datetime

from terminal_mcp_server.models.terminal_models import (
    CommandRequest,
    CommandResult,
    ProcessInfo,
    ProcessStatus,
)


def test_command_request_creation():
    """Test CommandRequest model creation."""
    request = CommandRequest(
        command="echo hello",
        working_directory="/tmp",
        environment_variables={"TEST": "value"},
        timeout=30,
        capture_output=True
    )
    
    assert request.command == "echo hello"
    assert request.working_directory == "/tmp"
    assert request.environment_variables == {"TEST": "value"}
    assert request.timeout == 30
    assert request.capture_output is True


def test_command_result_creation():
    """Test CommandResult model creation."""
    started_at = datetime.now()
    completed_at = datetime.now()
    
    result = CommandResult(
        command="echo hello",
        exit_code=0,
        stdout="hello\n",
        stderr="",
        execution_time=0.1,
        started_at=started_at,
        completed_at=completed_at
    )
    
    assert result.command == "echo hello"
    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""
    assert result.execution_time == 0.1
    assert result.started_at == started_at
    assert result.completed_at == completed_at


def test_process_status_enum():
    """Test ProcessStatus enum values."""
    assert ProcessStatus.RUNNING == "running"
    assert ProcessStatus.COMPLETED == "completed"
    assert ProcessStatus.FAILED == "failed"
    assert ProcessStatus.KILLED == "killed"
    assert ProcessStatus.UNKNOWN == "unknown"


def test_process_info_creation():
    """Test ProcessInfo model creation."""
    started_at = datetime.now()
    
    process_info = ProcessInfo(
        pid=12345,
        process_id="proc_1",
        command="long_running_command",
        status=ProcessStatus.RUNNING,
        started_at=started_at,
        working_directory="/tmp",
        environment_variables={"ENV": "test"}
    )
    
    assert process_info.pid == 12345
    assert process_info.process_id == "proc_1"
    assert process_info.command == "long_running_command"
    assert process_info.status == ProcessStatus.RUNNING
    assert process_info.started_at == started_at
    assert process_info.working_directory == "/tmp"
    assert process_info.environment_variables == {"ENV": "test"} 