"""
Tests for process manager functionality to ensure proper background process
tracking, lifecycle management, and resource cleanup.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import signal
import os

from terminal_mcp_server.utils.process_manager import ProcessManager
from terminal_mcp_server.models.terminal_models import ProcessInfo, ProcessStatus


@pytest.fixture
def process_manager():
    """Create a ProcessManager instance for testing."""
    return ProcessManager()


@pytest.mark.asyncio
async def test_process_manager_initialization(process_manager):
    """Test that ProcessManager initializes properly."""
    assert process_manager is not None
    assert hasattr(process_manager, 'processes')
    assert isinstance(process_manager.processes, dict)
    assert len(process_manager.processes) == 0
    assert hasattr(process_manager, 'start_process')
    assert hasattr(process_manager, 'list_processes')
    assert hasattr(process_manager, 'get_process_status')
    assert hasattr(process_manager, 'kill_process')


@pytest.mark.asyncio
async def test_start_background_process_basic(process_manager):
    """Test starting a basic background process."""
    command = "sleep 10"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        process_info = await process_manager.start_process(command)
        
        assert isinstance(process_info, ProcessInfo)
        assert process_info.command == command
        assert process_info.status == ProcessStatus.RUNNING
        assert process_info.pid == 12345
        assert isinstance(process_info.started_at, datetime)
        assert process_info.process_id.startswith('proc_')


@pytest.mark.asyncio
async def test_start_process_with_working_directory(process_manager):
    """Test starting a process with a specific working directory."""
    command = "pwd"
    working_dir = "/tmp"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12346
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        process_info = await process_manager.start_process(
            command=command,
            working_directory=working_dir
        )
        
        assert process_info.working_directory == working_dir
        assert process_info.command == command
        
        # Verify subprocess was called with correct working directory
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs['cwd'] == working_dir


@pytest.mark.asyncio
async def test_start_process_with_environment_variables(process_manager):
    """Test starting a process with custom environment variables."""
    command = "echo $TEST_VAR"
    env_vars = {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12347
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        process_info = await process_manager.start_process(
            command=command,
            environment_variables=env_vars
        )
        
        assert process_info.environment_variables == env_vars
        
        # Verify subprocess was called with environment variables
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert 'env' in call_kwargs
        for key, value in env_vars.items():
            assert call_kwargs['env'][key] == value


@pytest.mark.asyncio
async def test_list_processes_empty(process_manager):
    """Test listing processes when none are running."""
    processes = await process_manager.list_processes()
    assert isinstance(processes, list)
    assert len(processes) == 0


@pytest.mark.asyncio
async def test_list_processes_with_multiple(process_manager):
    """Test listing multiple running processes."""
    commands = ["sleep 10", "sleep 20", "sleep 30"]
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_processes = []
        for i, command in enumerate(commands):
            mock_process = Mock()
            mock_process.pid = 12350 + i
            mock_process.returncode = None
            mock_processes.append(mock_process)
        
        mock_subprocess.side_effect = mock_processes
        
        # Start multiple processes
        started_processes = []
        for command in commands:
            process_info = await process_manager.start_process(command)
            started_processes.append(process_info)
        
        # List processes
        listed_processes = await process_manager.list_processes()
        
        assert len(listed_processes) == len(commands)
        for process_info in started_processes:
            assert any(p.process_id == process_info.process_id for p in listed_processes)


@pytest.mark.asyncio
async def test_get_process_status_existing(process_manager):
    """Test getting status of an existing process."""
    command = "sleep 5"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess, \
         patch('os.kill') as mock_kill:
        
        mock_process = Mock()
        mock_process.pid = 12351
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Mock os.kill to simulate process still running
        mock_kill.return_value = None  # No exception = process exists
        
        # Start process
        process_info = await process_manager.start_process(command)
        process_id = process_info.process_id
        
        # Get status
        status_info = await process_manager.get_process_status(process_id)
        
        assert status_info.process_id == process_id
        assert status_info.status == ProcessStatus.RUNNING


@pytest.mark.asyncio
async def test_get_process_status_nonexistent(process_manager):
    """Test getting status of a non-existent process."""
    with pytest.raises(ValueError) as exc_info:
        await process_manager.get_process_status("nonexistent_proc")
    
    assert "Process nonexistent_proc not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kill_process_existing(process_manager):
    """Test killing an existing process."""
    command = "sleep 60"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess, \
         patch('os.killpg') as mock_killpg, \
         patch('os.getpgid') as mock_getpgid:
        
        mock_process = Mock()
        mock_process.pid = 12352
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        mock_getpgid.return_value = 12352
        
        process_info = await process_manager.start_process(command)
        process_id = process_info.process_id
        
        result = await process_manager.kill_process(process_id)
        
        assert result is True
        updated_info = await process_manager.get_process_status(process_id)
        assert updated_info.status == ProcessStatus.KILLED


@pytest.mark.asyncio
async def test_kill_process_nonexistent(process_manager):
    """Test killing a non-existent process."""
    result = await process_manager.kill_process("nonexistent_proc")
    assert result is False


@pytest.mark.asyncio
async def test_process_status_transitions(process_manager):
    """Test that process status transitions correctly."""
    command = "echo 'test'"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12353
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Start process (should be RUNNING)
        process_info = await process_manager.start_process(command)
        assert process_info.status == ProcessStatus.RUNNING
        
        # Simulate process completion
        mock_process.returncode = 0
        await process_manager.update_process_status(process_info.process_id)
        
        updated_info = await process_manager.get_process_status(process_info.process_id)
        assert updated_info.status == ProcessStatus.COMPLETED


@pytest.mark.asyncio
async def test_process_cleanup_on_completion(process_manager):
    """Test that completed processes are cleaned up properly."""
    command = "echo 'quick command'"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12354
        mock_process.returncode = 0  # Process completes immediately
        mock_subprocess.return_value = mock_process
        
        # Start process
        process_info = await process_manager.start_process(command)
        
        # Simulate cleanup after completion
        await process_manager.cleanup_completed_processes()
        
        # Verify process is still tracked but can be cleaned up after max_age_hours
        remaining_processes = await process_manager.list_processes()
        if remaining_processes:
            for proc in remaining_processes:
                if proc.process_id == process_info.process_id:
                    assert proc.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.KILLED]


@pytest.mark.asyncio
async def test_concurrent_process_management(process_manager):
    """Test managing multiple processes concurrently."""
    commands = [f"sleep {i}" for i in range(1, 4)]  # Reduced for faster tests
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess, \
         patch('os.killpg') as mock_killpg, \
         patch('os.getpgid') as mock_getpgid:
        
        mock_processes = []
        for i, command in enumerate(commands):
            mock_process = Mock()
            mock_process.pid = 12360 + i
            mock_process.returncode = None
            mock_processes.append(mock_process)
        
        mock_subprocess.side_effect = mock_processes
        mock_getpgid.side_effect = lambda pid: pid
        
        # Start all processes concurrently
        tasks = [process_manager.start_process(cmd) for cmd in commands]
        started_processes = await asyncio.gather(*tasks)
        
        assert len(started_processes) == len(commands)
        
        # Verify all processes are tracked
        all_processes = await process_manager.list_processes()
        assert len(all_processes) == len(commands)
        
        # Kill all processes
        kill_tasks = [process_manager.kill_process(proc.process_id) for proc in started_processes]
        kill_results = await asyncio.gather(*kill_tasks)
        
        assert all(kill_results)  # All kills should succeed


@pytest.mark.asyncio
async def test_process_output_capture(process_manager):
    """Test capturing output from background processes."""
    command = "echo 'test output'"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = Mock()
        mock_process.pid = 12365
        mock_process.returncode = 0
        
        # Mock process.communicate() correctly
        async def mock_communicate():
            return (b"test output\n", b"")
        
        mock_process.communicate = mock_communicate
        mock_subprocess.return_value = mock_process
        
        # Start process with output capture
        process_info = await process_manager.start_process(command, capture_output=True)
        
        # Give a small delay for output capture to complete
        await asyncio.sleep(0.1)
        
        # Get output
        output = await process_manager.get_process_output(process_info.process_id)
        
        assert "test output" in output['stdout']
        assert output['stderr'] == ""


@pytest.mark.asyncio
async def test_process_restart_functionality(process_manager):
    """Test restarting a killed process."""
    command = "sleep 10"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess, \
         patch('os.killpg') as mock_killpg, \
         patch('os.getpgid') as mock_getpgid:
        
        mock_process1 = Mock()
        mock_process1.pid = 12370
        mock_process1.returncode = None
        
        mock_process2 = Mock()
        mock_process2.pid = 12371
        mock_process2.returncode = None
        
        mock_subprocess.side_effect = [mock_process1, mock_process2]
        mock_getpgid.side_effect = lambda pid: pid
        
        # Start process
        process_info = await process_manager.start_process(command)
        original_id = process_info.process_id
        
        # Kill process
        await process_manager.kill_process(original_id)
        
        # Restart process
        restarted_info = await process_manager.restart_process(original_id)
        
        assert restarted_info.command == command
        assert restarted_info.status == ProcessStatus.RUNNING
        assert restarted_info.process_id != original_id  # Should get new ID
        assert restarted_info.pid == 12371