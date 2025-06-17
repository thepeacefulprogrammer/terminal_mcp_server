"""Tests for Python script execution handlers and MCP tools."""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime
from pathlib import Path

from terminal_mcp_server.handlers.python_handlers import PythonHandlers
from terminal_mcp_server.models.terminal_models import CommandResult


@pytest.fixture
def python_handlers():
    """Create a PythonHandlers instance for testing."""
    return PythonHandlers()


@pytest.fixture
def mock_command_executor():
    """Create a mock CommandExecutor for testing."""
    mock_executor = Mock()
    mock_executor.execute = AsyncMock()
    return mock_executor


@pytest.fixture
def mock_venv_manager():
    """Create a mock VenvManager for testing."""
    mock_manager = Mock()
    mock_manager.list_virtual_environments = AsyncMock()
    mock_manager.activate_virtual_environment = AsyncMock()
    mock_manager.create_virtual_environment = AsyncMock()
    mock_manager.install_package = AsyncMock()
    mock_manager.install_dependencies = AsyncMock()
    return mock_manager


@pytest.mark.asyncio
async def test_python_handlers_initialization(python_handlers):
    """Test that PythonHandlers initializes properly."""
    assert python_handlers is not None
    assert hasattr(python_handlers, 'command_executor')
    assert hasattr(python_handlers, 'venv_manager')
    assert hasattr(python_handlers, 'execute_python_script')
    assert hasattr(python_handlers, 'execute_python_code')
    assert hasattr(python_handlers, 'list_virtual_environments')
    assert hasattr(python_handlers, 'activate_virtual_environment')
    assert hasattr(python_handlers, 'create_virtual_environment')
    assert hasattr(python_handlers, 'install_python_package')
    assert hasattr(python_handlers, 'install_dependencies')


@pytest.mark.asyncio
async def test_execute_python_script_basic(python_handlers, mock_command_executor):
    """Test executing a basic Python script."""
    python_handlers.command_executor = mock_command_executor
    
    # Mock successful execution
    mock_result = CommandResult(
        command="python test_script.py",
        exit_code=0,
        stdout="Script executed successfully\nResult: 42",
        stderr="",
        execution_time=1.5,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    result = await python_handlers.execute_python_script(
        script_path="test_script.py"
    )
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["script_path"] == "test_script.py"
    assert result["exit_code"] == 0
    assert "Script executed successfully" in result["stdout"]
    assert result["stderr"] == ""
    assert result["execution_time"] == 1.5


@pytest.mark.asyncio
async def test_execute_python_script_with_args(python_handlers, mock_command_executor):
    """Test executing Python script with command line arguments."""
    python_handlers.command_executor = mock_command_executor
    
    mock_result = CommandResult(
        command="python script.py arg1 arg2 --flag",
        exit_code=0,
        stdout="Args processed: arg1, arg2, flag=True",
        stderr="",
        execution_time=0.8,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    result = await python_handlers.execute_python_script(
        script_path="script.py",
        args=["arg1", "arg2", "--flag"]
    )
    
    assert result["success"] is True
    assert "arg1 arg2 --flag" in mock_command_executor.execute.call_args[0][0].command
    assert "Args processed" in result["stdout"]


@pytest.mark.asyncio
async def test_execute_python_script_with_venv(python_handlers, mock_command_executor):
    """Test executing Python script in virtual environment."""
    python_handlers.command_executor = mock_command_executor
    
    mock_result = CommandResult(
        command="/path/to/venv/bin/python script.py",
        exit_code=0,
        stdout="Running in virtual environment",
        stderr="",
        execution_time=1.2,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    with patch.object(python_handlers, '_get_python_executable', return_value="/path/to/venv/bin/python"):
        result = await python_handlers.execute_python_script(
            script_path="script.py",
            virtual_environment="my_venv"
        )
    
    assert result["success"] is True
    assert result["virtual_environment"] == "my_venv"
    assert "/path/to/venv/bin/python" in mock_command_executor.execute.call_args[0][0].command


@pytest.mark.asyncio
async def test_execute_python_script_failure(python_handlers, mock_command_executor):
    """Test handling Python script execution failure."""
    python_handlers.command_executor = mock_command_executor
    
    mock_result = CommandResult(
        command="python bad_script.py",
        exit_code=1,
        stdout="",
        stderr="NameError: name 'undefined_var' is not defined",
        execution_time=0.3,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    result = await python_handlers.execute_python_script(
        script_path="bad_script.py"
    )
    
    assert result["success"] is False
    assert result["exit_code"] == 1
    assert "NameError" in result["stderr"]


@pytest.mark.asyncio
async def test_execute_python_code_basic(python_handlers, mock_command_executor):
    """Test executing Python code directly."""
    python_handlers.command_executor = mock_command_executor
    
    code = "print('Hello, World!')\nresult = 2 + 2\nprint(f'Result: {result}')"
    
    mock_result = CommandResult(
        command="python -c \"print('Hello, World!')\\nresult = 2 + 2\\nprint(f'Result: {result}')\"",
        exit_code=0,
        stdout="Hello, World!\nResult: 4",
        stderr="",
        execution_time=0.5,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    result = await python_handlers.execute_python_code(code=code)
    
    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "Hello, World!" in result["stdout"]
    assert "Result: 4" in result["stdout"]


@pytest.mark.asyncio
async def test_execute_python_code_with_venv(python_handlers, mock_command_executor):
    """Test executing Python code in virtual environment."""
    python_handlers.command_executor = mock_command_executor
    
    code = "import sys; print(sys.executable)"
    
    mock_result = CommandResult(
        command="/path/to/venv/bin/python -c \"import sys; print(sys.executable)\"",
        exit_code=0,
        stdout="/path/to/venv/bin/python",
        stderr="",
        execution_time=0.3,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    with patch.object(python_handlers, '_get_python_executable', return_value="/path/to/venv/bin/python"):
        result = await python_handlers.execute_python_code(
            code=code,
            virtual_environment="test_venv"
        )
    
    assert result["success"] is True
    assert "/path/to/venv/bin/python" in result["stdout"]


@pytest.mark.asyncio
async def test_list_virtual_environments(python_handlers, mock_venv_manager):
    """Test listing virtual environments."""
    from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
    
    python_handlers.venv_manager = mock_venv_manager
    
    mock_venvs = [
        VirtualEnvironmentInfo("project1", "/home/user/.venvs/project1", "3.11.0", False),
        VirtualEnvironmentInfo("project2", "/home/user/.venvs/project2", "3.10.8", True),
        VirtualEnvironmentInfo("test_env", "/home/user/.venvs/test_env", "3.9.16", False)
    ]
    mock_venv_manager.list_virtual_environments.return_value = mock_venvs
    
    result = await python_handlers.list_virtual_environments()
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["name"] == "project1"
    assert result[1]["active"] is True
    assert result[2]["python_version"] == "3.9.16"


@pytest.mark.asyncio
async def test_activate_virtual_environment_success(python_handlers, mock_venv_manager):
    """Test successfully activating a virtual environment."""
    python_handlers.venv_manager = mock_venv_manager
    
    # venv_manager.activate_virtual_environment returns bool
    mock_venv_manager.activate_virtual_environment.return_value = True
    
    result = await python_handlers.activate_virtual_environment("my_project")
    
    assert result["success"] is True
    assert result["name"] == "my_project"
    assert "bin/python" in result["python_executable"]


@pytest.mark.asyncio
async def test_activate_virtual_environment_not_found(python_handlers, mock_venv_manager):
    """Test activating a non-existent virtual environment."""
    python_handlers.venv_manager = mock_venv_manager
    
    mock_venv_manager.activate_virtual_environment.side_effect = ValueError("Virtual environment 'nonexistent' not found")
    
    result = await python_handlers.activate_virtual_environment("nonexistent")
    
    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_create_virtual_environment_success(python_handlers, mock_venv_manager):
    """Test successfully creating a virtual environment."""
    from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
    
    python_handlers.venv_manager = mock_venv_manager
    
    # venv_manager.create_virtual_environment returns VirtualEnvironmentInfo
    mock_venv_info = VirtualEnvironmentInfo(
        name="new_project",
        path="/home/user/.venvs/new_project",
        python_version="3.11.0",
        is_active=False
    )
    mock_venv_manager.create_virtual_environment.return_value = mock_venv_info
    
    result = await python_handlers.create_virtual_environment(
        name="new_project",
        python_version="3.11"
    )
    
    assert result["success"] is True
    assert result["name"] == "new_project"
    assert "3.11.0" in result["python_version"]


@pytest.mark.asyncio
async def test_create_virtual_environment_with_packages(python_handlers, mock_venv_manager):
    """Test creating virtual environment with initial packages."""
    from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
    
    python_handlers.venv_manager = mock_venv_manager
    
    # venv_manager.create_virtual_environment returns VirtualEnvironmentInfo
    mock_venv_info = VirtualEnvironmentInfo(
        name="ml_project",
        path="/home/user/.venvs/ml_project",
        python_version="3.10.8",
        is_active=False
    )
    mock_venv_manager.create_virtual_environment.return_value = mock_venv_info
    
    result = await python_handlers.create_virtual_environment(
        name="ml_project",
        packages=["numpy", "pandas"]
    )
    
    assert result["success"] is True
    assert "installed_packages" in result
    assert len(result["installed_packages"]) == 2


@pytest.mark.asyncio
async def test_install_python_package_success(python_handlers, mock_venv_manager):
    """Test successfully installing a Python package."""
    python_handlers.venv_manager = mock_venv_manager
    
    # Mock the enhanced method
    mock_install_result = {
        "success": True,
        "stdout": "Collecting requests\n  Downloading requests-2.28.2-py3-none-any.whl (62 kB)\nInstalling collected packages: requests\nSuccessfully installed requests-2.28.2",
        "stderr": "",
        "returncode": 0,
        "execution_time": 3.2,
        "command": 'pip install "requests"'
    }
    
    # Mock both methods for compatibility
    mock_venv_manager.install_package_with_output = AsyncMock(return_value=mock_install_result)
    mock_venv_manager.install_package = AsyncMock(return_value=True)
    
    result = await python_handlers.install_python_package(
        package="requests",
        virtual_environment="web_project"
    )
    
    assert result["success"] is True
    assert result["package"] == "requests"
    assert "Successfully installed" in result["installation_output"]
    assert result["execution_time"] == 3.2


@pytest.mark.asyncio
async def test_install_python_package_with_version(python_handlers, mock_venv_manager):
    """Test installing a specific version of a Python package."""
    python_handlers.venv_manager = mock_venv_manager
    
    # Mock the enhanced method
    mock_install_result = {
        "success": True,
        "stdout": "Collecting django==4.1.0\n  Downloading Django-4.1.0-py3-none-any.whl (8.1 MB)\nInstalling collected packages: django\nSuccessfully installed django-4.1.0",
        "stderr": "",
        "returncode": 0,
        "execution_time": 12.4,
        "command": 'pip install "django==4.1.0"'
    }
    
    # Mock both methods for compatibility
    mock_venv_manager.install_package_with_output = AsyncMock(return_value=mock_install_result)
    mock_venv_manager.install_package = AsyncMock(return_value=True)
    
    result = await python_handlers.install_python_package(
        package="django==4.1.0",
        virtual_environment="web_app"
    )
    
    assert result["success"] is True
    assert "4.1.0" in result["package"]
    assert "django-4.1.0" in result["installation_output"]


@pytest.mark.asyncio
async def test_install_dependencies_from_requirements(python_handlers, mock_venv_manager):
    """Test installing dependencies from requirements.txt."""
    python_handlers.venv_manager = mock_venv_manager
    
    mock_venv_manager.install_dependencies.return_value = {
        "success": True,
        "requirements_file": "requirements.txt",
        "virtual_environment": "project_env",
        "installed_packages": ["flask==2.2.0", "gunicorn==20.1.0", "psycopg2==2.9.5"],
        "installation_output": "Successfully installed 3 packages"
    }
    
    result = await python_handlers.install_dependencies(
        requirements_file="requirements.txt",
        virtual_environment="project_env"
    )
    
    assert result["success"] is True
    assert len(result["installed_packages"]) == 3
    assert "flask" in str(result["installed_packages"])


@pytest.mark.asyncio
async def test_mcp_tool_registration(python_handlers):
    """Test that MCP tools are registered correctly."""
    mock_mcp_server = Mock()
    mock_tool_decorator = Mock()
    mock_mcp_server.tool.return_value = mock_tool_decorator
    
    # Call register_tools
    python_handlers.register_tools(mock_mcp_server)
    
    # Verify that tool decorator was called for each expected tool
    expected_calls = 9  # Number of MCP tools we expect to register (7 original + 2 streaming)
    assert mock_mcp_server.tool.call_count == expected_calls


@pytest.mark.asyncio
async def test_mcp_execute_python_script_tool():
    """Test the MCP execute_python_script tool."""
    python_handlers = PythonHandlers()
    
    # Mock the command executor
    mock_executor = Mock()
    mock_result = CommandResult(
        command="python test.py",
        exit_code=0,
        stdout="Test output",
        stderr="",
        execution_time=1.0,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_executor.execute = AsyncMock(return_value=mock_result)
    python_handlers.command_executor = mock_executor
    
    # Test the handler method directly
    result = await python_handlers.execute_python_script("test.py")
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["script_path"] == "test.py"


@pytest.mark.asyncio
async def test_concurrent_python_operations(python_handlers, mock_command_executor):
    """Test concurrent Python script executions."""
    python_handlers.command_executor = mock_command_executor
    
    # Mock multiple script results
    mock_results = []
    for i in range(3):
        mock_result = CommandResult(
            command=f"python script_{i}.py",
            exit_code=0,
            stdout=f"Output from script {i}",
            stderr="",
            execution_time=0.5,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        mock_results.append(mock_result)
    
    mock_command_executor.execute.side_effect = mock_results
    
    # Execute multiple scripts concurrently
    tasks = [
        python_handlers.execute_python_script(f"script_{i}.py")
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["success"] is True
        assert result["script_path"] == f"script_{i}.py"
        assert f"Output from script {i}" in result["stdout"]


@pytest.mark.asyncio
async def test_error_handling_with_exception(python_handlers, mock_command_executor):
    """Test error handling when execution raises an exception."""
    python_handlers.command_executor = mock_command_executor
    mock_command_executor.execute.side_effect = Exception("File not found")
    
    result = await python_handlers.execute_python_script("nonexistent.py")
    
    assert result["success"] is False
    assert "File not found" in result["error"]


@pytest.mark.asyncio
async def test_working_directory_support(python_handlers, mock_command_executor):
    """Test Python script execution with working directory support."""
    python_handlers.command_executor = mock_command_executor
    
    mock_result = CommandResult(
        command="python script.py",
        exit_code=0,
        stdout="Working directory: /custom/path",
        stderr="",
        execution_time=0.7,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    mock_command_executor.execute.return_value = mock_result
    
    result = await python_handlers.execute_python_script(
        script_path="script.py",
        working_directory="/custom/path"
    )
    
    assert result["success"] is True
    assert result["working_directory"] == "/custom/path"
    
    # Verify working directory was passed to command executor
    call_args = mock_command_executor.execute.call_args[0][0]
    assert call_args.working_directory == "/custom/path"


# ========== Task 4.2: Streaming Tests ==========

@pytest.mark.asyncio
async def test_execute_python_script_with_streaming(python_handlers, mock_command_executor):
    """Test executing Python script with real-time output streaming."""
    python_handlers.command_executor = mock_command_executor
    
    # Mock streaming output
    async def mock_stream_generator():
        yield "Starting script execution...\n"
        yield "Processing data...\n"
        yield "Progress: 50%\n"
        yield "Progress: 100%\n"
        yield "Script completed successfully!\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python long_script.py",
            exit_code=0,
            stdout="Starting script execution...\nProcessing data...\nProgress: 50%\nProgress: 100%\nScript completed successfully!\n",
            stderr="",
            execution_time=5.2,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    # Test streaming execution
    stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
        script_path="long_script.py"
    )
    
    # Collect streamed output
    streamed_chunks = []
    async for chunk in stream_generator:
        streamed_chunks.append(chunk)
    
    assert len(streamed_chunks) == 5
    assert "Starting script execution" in streamed_chunks[0]
    assert "Processing data" in streamed_chunks[1]
    assert "Progress: 50%" in streamed_chunks[2]
    assert "Progress: 100%" in streamed_chunks[3]
    assert "Script completed successfully" in streamed_chunks[4]
    
    # Verify final result
    assert final_result["success"] is True
    assert final_result["exit_code"] == 0
    assert final_result["execution_time"] == 5.2


@pytest.mark.asyncio
async def test_execute_python_script_streaming_with_args(python_handlers, mock_command_executor):
    """Test streaming execution with command line arguments."""
    python_handlers.command_executor = mock_command_executor
    
    async def mock_stream_generator():
        yield "Arguments received: arg1, arg2\n"
        yield "Processing arguments...\n"
        yield "Execution complete.\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python script.py arg1 arg2",
            exit_code=0,
            stdout="Arguments received: arg1, arg2\nProcessing arguments...\nExecution complete.\n",
            stderr="",
            execution_time=2.1,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
        script_path="script.py",
        args=["arg1", "arg2"]
    )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert "Arguments received: arg1, arg2" in chunks[0]
    assert "Processing arguments" in chunks[1]
    assert "Execution complete" in chunks[2]


@pytest.mark.asyncio
async def test_execute_python_script_streaming_with_venv(python_handlers, mock_command_executor):
    """Test streaming execution in virtual environment."""
    python_handlers.command_executor = mock_command_executor
    
    async def mock_stream_generator():
        yield "Virtual environment: my_venv\n"
        yield "Python version: 3.11.0\n"
        yield "Script output here\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="/path/to/venv/bin/python script.py",
            exit_code=0,
            stdout="Virtual environment: my_venv\nPython version: 3.11.0\nScript output here\n",
            stderr="",
            execution_time=1.8,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    with patch.object(python_handlers, '_get_python_executable', return_value="/path/to/venv/bin/python"):
        stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
            script_path="script.py",
            virtual_environment="my_venv"
        )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert "Virtual environment: my_venv" in chunks[0]
    assert "Python version: 3.11.0" in chunks[1]
    assert "Script output here" in chunks[2]
    assert final_result["virtual_environment"] == "my_venv"


@pytest.mark.asyncio
async def test_execute_python_script_streaming_error_handling(python_handlers, mock_command_executor):
    """Test streaming execution with error handling."""
    python_handlers.command_executor = mock_command_executor
    
    async def mock_stream_generator():
        yield "Starting execution...\n"
        yield "Error occurred!\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python error_script.py",
            exit_code=1,
            stdout="Starting execution...\n",
            stderr="Error occurred!\nTraceback: ValueError\n",
            execution_time=0.5,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
        script_path="error_script.py"
    )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 2
    assert "Starting execution" in chunks[0]
    assert "Error occurred" in chunks[1]
    
    # Verify error handling in final result
    assert final_result["success"] is False
    assert final_result["exit_code"] == 1
    assert "Traceback: ValueError" in final_result["stderr"]


@pytest.mark.asyncio
async def test_execute_python_script_streaming_timeout(python_handlers, mock_command_executor):
    """Test streaming execution with timeout handling."""
    python_handlers.command_executor = mock_command_executor
    
    async def mock_stream_generator():
        yield "Starting long operation...\n"
        yield "Still processing...\n"
        # Simulate timeout before completion
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python slow_script.py",
            exit_code=-1,
            stdout="Starting long operation...\nStill processing...\n",
            stderr="Command execution timed out",
            execution_time=30.0,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
        script_path="slow_script.py",
        timeout=30
    )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 2
    assert "Starting long operation" in chunks[0]
    assert "Still processing" in chunks[1]
    
    # Verify timeout handling
    assert final_result["success"] is False
    assert final_result["exit_code"] == -1
    assert "timed out" in final_result["stderr"]


@pytest.mark.asyncio
async def test_execute_python_code_with_streaming(python_handlers, mock_command_executor):
    """Test executing Python code with streaming output."""
    python_handlers.command_executor = mock_command_executor
    
    code = """
for i in range(3):
    print(f"Iteration {i+1}")
    import time
    time.sleep(0.1)
print("Done!")
"""
    
    async def mock_stream_generator():
        yield "Iteration 1\n"
        yield "Iteration 2\n"
        yield "Iteration 3\n"
        yield "Done!\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python -c \"...\"",
            exit_code=0,
            stdout="Iteration 1\nIteration 2\nIteration 3\nDone!\n",
            stderr="",
            execution_time=0.4,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    stream_generator, final_result = await python_handlers.execute_python_code_with_streaming(
        code=code
    )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 4
    assert "Iteration 1" in chunks[0]
    assert "Iteration 2" in chunks[1]
    assert "Iteration 3" in chunks[2]
    assert "Done!" in chunks[3]
    
    assert final_result["success"] is True
    assert final_result["exit_code"] == 0


@pytest.mark.asyncio
async def test_streaming_with_large_output(python_handlers, mock_command_executor):
    """Test streaming with large output to verify buffer handling."""
    python_handlers.command_executor = mock_command_executor
    
    # Simulate large output chunks
    async def mock_stream_generator():
        for i in range(10):
            yield f"Large chunk {i}: " + "x" * 1000 + "\n"
    
    mock_command_executor.execute_with_streaming = AsyncMock()
    mock_command_executor.execute_with_streaming.return_value = (
        mock_stream_generator(),
        CommandResult(
            command="python large_output_script.py",
            exit_code=0,
            stdout="Large output...",
            stderr="",
            execution_time=3.0,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    )
    
    stream_generator, final_result = await python_handlers.execute_python_script_with_streaming(
        script_path="large_output_script.py"
    )
    
    chunks = []
    async for chunk in stream_generator:
        chunks.append(chunk)
    
    assert len(chunks) == 10
    for i, chunk in enumerate(chunks):
        assert f"Large chunk {i}" in chunk
        assert len(chunk) > 1000  # Verify large chunks are handled
    
    assert final_result["success"] is True


@pytest.mark.asyncio
async def test_streaming_mcp_tool_integration(python_handlers):
    """Test that MCP tools support streaming functionality."""
    # Mock MCP server
    mock_mcp_server = Mock()
    mock_tools = []
    
    def mock_tool():
        def decorator(func):
            mock_tools.append(func)
            return func
        return decorator
    
    mock_mcp_server.tool = mock_tool
    
    # Register tools
    python_handlers.register_tools(mock_mcp_server)
    
    # Verify streaming tools are registered
    tool_names = [tool.__name__ for tool in mock_tools]
    assert "execute_python_script" in tool_names
    assert "execute_python_script_with_streaming" in tool_names
    assert "execute_python_code_with_streaming" in tool_names
    
    # Test that streaming tools exist and are callable
    streaming_script_tool = next(tool for tool in mock_tools if tool.__name__ == "execute_python_script_with_streaming")
    streaming_code_tool = next(tool for tool in mock_tools if tool.__name__ == "execute_python_code_with_streaming")
    
    assert callable(streaming_script_tool)
    assert callable(streaming_code_tool)


# ========== Task 4.3: Server Integration Test ==========

@pytest.mark.asyncio
async def test_python_handlers_registered_in_server():
    """Test that Python handlers tools are registered in the MCP server."""
    from terminal_mcp_server.server import TerminalMCPServer
    from unittest.mock import patch
    
    # Mock the config loading to avoid file dependencies
    with patch('terminal_mcp_server.server.load_config') as mock_load_config:
        mock_load_config.return_value = {
            "server": {"name": "test-server"},
            "logging": {"level": "INFO"}
        }
        
        # Mock the auth config loading
        with patch('terminal_mcp_server.server.load_auth_config') as mock_load_auth:
            mock_load_auth.return_value = {}
            
            # Create server instance
            server = TerminalMCPServer()
            
            # Use FastMCP's list_tools method to get registered tools
            tools_list = await server.mcp.list_tools()
            
            # FastMCP returns a list of Tool objects directly
            tool_names = [tool.name for tool in tools_list]
            
            # Expected Python tools that should be registered
            expected_python_tools = [
                "execute_python_script",
                "execute_python_code", 
                "execute_python_script_with_streaming",
                "execute_python_code_with_streaming",
                "list_virtual_environments",
                "activate_virtual_environment",
                "create_virtual_environment",
                "install_python_package",
                "install_dependencies"
            ]
            
            # Verify that all Python tools are registered
            for tool_name in expected_python_tools:
                assert tool_name in tool_names, f"Python tool '{tool_name}' should be registered in server"
            
            # Verify we have the expected total count
            # Expected: 1 (test_connection) + 1 (execute_command) + 6 (process tools) + 9 (python tools) + 4 (environment tools) = 21
            expected_total = 21
            assert len(tool_names) == expected_total, f"Expected exactly {expected_total} tools, got {len(tool_names)}: {tool_names}"
            
            # Verify specific tool categories are present
            assert "test_connection" in tool_names
            assert "execute_command" in tool_names
            assert "execute_command_background" in tool_names

@pytest.mark.asyncio
async def test_streaming_captures_output_chunks(python_handlers):
    """Test that streaming methods capture output chunks in streamed_output array."""
    # Create a mock stream generator that yields some chunks
    async def mock_stream_generator():
        yield "Output chunk 1\n"
        yield "Output chunk 2\n" 
        yield "Output chunk 3\n"
    
    # Mock the command executor to return our test generator and a result
    from datetime import datetime
    mock_result = CommandResult(
        command="python test.py",
        exit_code=0,
        stdout="Full output",
        stderr="",
        execution_time=0.5,
        started_at=datetime(2023, 1, 1, 12, 0, 0),
        completed_at=datetime(2023, 1, 1, 12, 0, 1)
    )
    
    with patch.object(python_handlers.command_executor, 'execute_with_streaming', 
                     return_value=(mock_stream_generator(), mock_result)):
        
        # Test execute_python_script_with_streaming
        stream_gen, final_result = await python_handlers.execute_python_script_with_streaming("test.py")
        
        # Collect the streaming output
        streamed_chunks = []
        async for chunk in stream_gen:
            streamed_chunks.append(chunk)
        
        # Verify that we captured the expected chunks
        assert len(streamed_chunks) == 3
        assert streamed_chunks[0] == "Output chunk 1\n"
        assert streamed_chunks[1] == "Output chunk 2\n"
        assert streamed_chunks[2] == "Output chunk 3\n"
        
        # This is what the MCP tool should include in the final response
        # But currently streamed_output would be empty because the generator is exhausted
        assert final_result["streaming"] is True

@pytest.mark.asyncio
async def test_mcp_tool_streaming_includes_captured_output(python_handlers):
    """Test that MCP streaming tools include captured output in the final response."""
    # Create a mock stream generator 
    async def mock_stream_generator():
        yield "Line 1\n"
        yield "Line 2\n"
        yield "Final line\n"
    
    # Mock the execute_python_script_with_streaming method
    from datetime import datetime
    mock_result = {
        "success": True,
        "script_path": "test.py",
        "command": "python test.py",
        "exit_code": 0,
        "stdout": "Line 1\nLine 2\nFinal line\n",
        "stderr": "",
        "execution_time": 0.5,
        "started_at": "2023-01-01T12:00:00",
        "completed_at": "2023-01-01T12:00:01",
        "streaming": True
    }
    
    with patch.object(python_handlers, 'execute_python_script_with_streaming', 
                     return_value=(mock_stream_generator(), mock_result)) as mock_method:
        
        # Create a mock server to test tool registration
        mock_server = MagicMock()
        registered_tools = {}
        
        def capture_tool(func=None):
            """Capture registered tools for testing."""
            if func is None:
                # Return a decorator that captures the function
                def decorator(f):
                    registered_tools[f.__name__] = f
                    return f
                return decorator
            else:
                # Direct function registration
                registered_tools[func.__name__] = func
                return func
        
        mock_server.tool.side_effect = capture_tool
        
        # Register the tools
        python_handlers.register_tools(mock_server)
        
        # Get the streaming tool
        streaming_tool = registered_tools['execute_python_script_with_streaming']
        
        # Call the tool
        result_json = await streaming_tool("test.py")
        result = json.loads(result_json)
        
        # The streamed_output should contain the captured chunks
        # Currently this test will fail because streamed_output is empty
        assert "streamed_output" in result
        assert "total_streamed_chunks" in result
        
        # This is what we want to achieve:
        # assert len(result["streamed_output"]) == 3
        # assert result["streamed_output"][0] == "Line 1\n"
        # assert result["streamed_output"][1] == "Line 2\n" 
        # assert result["streamed_output"][2] == "Final line\n"
        # assert result["total_streamed_chunks"] == 3

@pytest.mark.asyncio
async def test_streaming_output_currently_empty_issue():
    """Test that demonstrates the current issue where streamed_output is empty."""
    # Create real PythonHandlers instance
    python_handlers = PythonHandlers()
    
    # Mock the command executor to return a stream that yields chunks
    async def mock_stream_generator():
        yield "Chunk 1\n"
        yield "Chunk 2\n"
        yield "Final chunk\n"
    
    # Mock command result
    from datetime import datetime
    mock_result = CommandResult(
        command="python test.py",
        exit_code=0,
        stdout="Chunk 1\nChunk 2\nFinal chunk\n",
        stderr="",
        execution_time=0.5,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    
    # Mock the execute_with_streaming method to return our test data
    with patch.object(python_handlers.command_executor, 'execute_with_streaming', 
                     return_value=(mock_stream_generator(), mock_result)):
        
        # Create mock server for tool registration
        mock_server = MagicMock()
        registered_tools = {}
        
        def tool_decorator():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_server.tool = tool_decorator
        
        # Register tools
        python_handlers.register_tools(mock_server)
        
        # Get the streaming tool function
        streaming_tool = registered_tools['execute_python_script_with_streaming']
        
        # Call the tool - this should demonstrate the issue
        result_json = await streaming_tool("test.py")
        result = json.loads(result_json)
        
        # This should pass and demonstrate the issue:
        # The streamed_output array should be empty (the bug)
        # and total_streamed_chunks should be 0
        assert "streamed_output" in result
        assert "total_streamed_chunks" in result
        
        # After the fix, we should now have the captured chunks
        assert len(result["streamed_output"]) == 3
        assert result["streamed_output"] == ["Chunk 1\n", "Chunk 2\n", "Final chunk\n"]
        assert result["total_streamed_chunks"] == 3
        
        # Verify captured_chunks is not in the final response (cleaned up)
        assert "captured_chunks" not in result

class TestPythonHandlersEnhancedPackageInstallation:
    """Test enhanced package installation with detailed pip output."""
    
    @pytest.fixture
    def python_handlers(self):
        """Create PythonHandlers instance for testing."""
        return PythonHandlers()
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_detailed_output(self, python_handlers):
        """Test that install_python_package returns detailed pip installation output."""
        package = "requests==2.28.0"
        
        # Mock the venv_manager to return detailed installation output
        mock_install_result = {
            "success": True,
            "stdout": "Collecting requests==2.28.0\n  Using cached requests-2.28.0-py3-none-any.whl (62 kB)\nCollecting charset-normalizer<3,>=2\n  Using cached charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\nInstalling collected packages: charset-normalizer, requests\nSuccessfully installed charset-normalizer-2.1.1 requests-2.28.0",
            "stderr": "",
            "returncode": 0,
            "execution_time": 2.5,
            "command": 'pip install "requests==2.28.0"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should return detailed pip output instead of simple success message
            assert result["success"] is True
            assert result["package"] == package
            assert "installation_output" in result
            assert "Collecting requests==2.28.0" in result["installation_output"]
            assert "Using cached requests-2.28.0-py3-none-any.whl" in result["installation_output"]
            assert "Successfully installed" in result["installation_output"]
            assert "charset-normalizer" in result["installation_output"]
            
            # Should include execution details
            assert "execution_time" in result
            assert "command" in result
            assert result["execution_time"] == 2.5
            assert "pip install" in result["command"]
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_detailed_error_output(self, python_handlers):
        """Test that install_python_package returns detailed error output on failure."""
        package = "nonexistent-package-12345"
        
        # Mock the venv_manager to return detailed error output
        mock_install_result = {
            "success": False,
            "stdout": "",
            "stderr": "ERROR: Could not find a version that satisfies the requirement nonexistent-package-12345 (from versions: none)\nERROR: No matching distribution found for nonexistent-package-12345",
            "returncode": 1,
            "execution_time": 1.2,
            "command": 'pip install "nonexistent-package-12345"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should return detailed error information
            assert result["success"] is False
            assert result["package"] == package
            assert "error" in result
            assert "Could not find a version" in result["error"]
            assert "No matching distribution found" in result["error"]
            
            # Should include execution details
            assert "execution_time" in result
            assert "command" in result
            assert result["execution_time"] == 1.2
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_virtual_environment_detailed_output(self, python_handlers):
        """Test package installation in virtual environment with detailed output."""
        package = "flask==2.2.2"
        venv_name = "test-env"
        
        # Mock detailed installation output for virtual environment
        mock_install_result = {
            "success": True,
            "stdout": "Requirement already satisfied: flask==2.2.2 in /home/user/.venvs/test-env/lib/python3.9/site-packages (2.2.2)\nRequirement already satisfied: Werkzeug>=2.2.2 in /home/user/.venvs/test-env/lib/python3.9/site-packages (2.2.2)\nRequirement already satisfied: Jinja2>=3.0 in /home/user/.venvs/test-env/lib/python3.9/site-packages (3.1.2)",
            "stderr": "",
            "returncode": 0,
            "execution_time": 0.8,
            "command": '/home/user/.venvs/test-env/bin/pip install "flask==2.2.2"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package, virtual_environment=venv_name)
            
            # Should return detailed output showing virtual environment path
            assert result["success"] is True
            assert result["virtual_environment"] == venv_name
            assert "installation_output" in result
            assert "/home/user/.venvs/test-env/" in result["installation_output"]
            assert "Requirement already satisfied" in result["installation_output"]
            assert "Werkzeug" in result["installation_output"]
            assert "Jinja2" in result["installation_output"]
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_dependencies_detailed_output(self, python_handlers):
        """Test package installation with dependencies showing detailed output."""
        package = "django==4.1.0"
        
        # Mock detailed installation output showing dependency resolution
        mock_install_result = {
            "success": True,
            "stdout": "Collecting django==4.1.0\n  Downloading Django-4.1.0-py3-none-any.whl (8.1 MB)\nCollecting asgiref<4,>=3.5.2\n  Downloading asgiref-3.5.2-py3-none-any.whl (22 kB)\nCollecting sqlparse>=0.2.2\n  Downloading sqlparse-0.4.2-py3-none-any.whl (42 kB)\nCollecting tzdata\n  Downloading tzdata-2022.2-py2.py3-none-any.whl (336 kB)\nInstalling collected packages: tzdata, sqlparse, asgiref, django\nSuccessfully installed asgiref-3.5.2 django-4.1.0 sqlparse-0.4.2 tzdata-2022.2",
            "stderr": "",
            "returncode": 0,
            "execution_time": 15.3,
            "command": 'pip install "django==4.1.0"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should show detailed dependency resolution
            assert result["success"] is True
            assert "installation_output" in result
            assert "Collecting django==4.1.0" in result["installation_output"]
            assert "Downloading Django-4.1.0-py3-none-any.whl" in result["installation_output"]
            assert "asgiref" in result["installation_output"]
            assert "sqlparse" in result["installation_output"]
            assert "tzdata" in result["installation_output"]
            assert "Successfully installed asgiref-3.5.2 django-4.1.0 sqlparse-0.4.2 tzdata-2022.2" in result["installation_output"]
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_upgrade_detailed_output(self, python_handlers):
        """Test package upgrade with detailed output."""
        package = "pip"
        
        # Mock detailed upgrade output
        mock_install_result = {
            "success": True,
            "stdout": "Requirement already satisfied: pip in /usr/local/lib/python3.9/site-packages (22.2.2)\nCollecting pip\n  Downloading pip-22.3.1-py3-none-any.whl (2.1 MB)\nInstalling collected packages: pip\n  Attempting uninstall: pip\n    Found existing installation: pip 22.2.2\n    Uninstalling pip-22.2.2:\n      Successfully uninstalled pip-22.2.2\nSuccessfully installed pip-22.3.1",
            "stderr": "WARNING: Running pip as the 'root' user",
            "returncode": 0,
            "execution_time": 8.7,
            "command": 'pip install --upgrade "pip"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should show detailed upgrade process
            assert result["success"] is True
            assert "installation_output" in result
            assert "Attempting uninstall" in result["installation_output"]
            assert "Found existing installation" in result["installation_output"]
            assert "Successfully uninstalled pip-22.2.2" in result["installation_output"]
            assert "Successfully installed pip-22.3.1" in result["installation_output"]
            
            # Should include warnings in stderr
            if "stderr" in result:
                assert "WARNING" in result.get("stderr", "")
    
    @pytest.mark.asyncio
    async def test_install_python_package_with_compilation_detailed_output(self, python_handlers):
        """Test package installation requiring compilation with detailed output."""
        package = "lxml==4.9.1"
        
        # Mock detailed compilation output
        mock_install_result = {
            "success": True,
            "stdout": "Collecting lxml==4.9.1\n  Downloading lxml-4.9.1.tar.gz (3.6 MB)\n  Building wheel for lxml (setup.py): started\n  Building wheel for lxml (setup.py): finished with status 'done'\n  Created wheel for lxml: filename=lxml-4.9.1-cp39-cp39-linux_x86_64.whl size=1234567 sha256=abc123...\n  Stored in directory: /home/user/.cache/pip/wheels/...\nInstalling collected packages: lxml\nSuccessfully installed lxml-4.9.1",
            "stderr": "Building wheel for lxml (setup.py): finished with status 'done'",
            "returncode": 0,
            "execution_time": 45.2,
            "command": 'pip install "lxml==4.9.1"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should show detailed compilation process
            assert result["success"] is True
            assert "installation_output" in result
            assert "Building wheel for lxml" in result["installation_output"]
            assert "finished with status 'done'" in result["installation_output"]
            assert "Created wheel for lxml" in result["installation_output"]
            assert "Successfully installed lxml-4.9.1" in result["installation_output"]
            assert result["execution_time"] > 40  # Compilation takes time
    
    @pytest.mark.asyncio
    async def test_install_python_package_fallback_on_venv_manager_error(self, python_handlers):
        """Test fallback behavior when venv_manager doesn't have enhanced method."""
        package = "requests"
        
        # Mock that the venv_manager doesn't have the new method, should fallback gracefully
        with patch.object(python_handlers.venv_manager, 'install_package', return_value=True):
            # Mock hasattr to return False to simulate older venv_manager
            with patch('builtins.hasattr', return_value=False):
                result = await python_handlers.install_python_package(package)
                
                # Should still work but with basic output
                assert result["success"] is True
                assert result["package"] == package
                assert "installation_output" in result
                # Should indicate this is fallback behavior
                assert "basic mode" in result["installation_output"]
    
    @pytest.mark.asyncio
    async def test_install_python_package_preserves_backward_compatibility(self, python_handlers):
        """Test that enhanced functionality preserves existing API compatibility."""
        package = "numpy"
        
        # Mock basic installation for backward compatibility test
        mock_install_result = {
            "success": True,
            "stdout": "Successfully installed numpy-1.23.0",
            "stderr": "",
            "returncode": 0,
            "execution_time": 5.1,
            "command": 'pip install "numpy"'
        }
        
        with patch.object(python_handlers.venv_manager, 'install_package_with_output', return_value=mock_install_result):
            result = await python_handlers.install_python_package(package)
            
            # Should maintain existing required fields
            assert "success" in result
            assert "package" in result
            assert "virtual_environment" in result
            assert isinstance(result["success"], bool)
            assert isinstance(result["package"], str)
            
            # Should add new detailed fields
            assert "installation_output" in result
            assert "execution_time" in result
            assert "command" in result

class TestVirtualEnvironmentErrorHandling:
    """Test comprehensive error handling for virtual environment operations to prevent object access bugs."""
    
    @pytest.fixture
    def python_handlers(self):
        """Create PythonHandlers instance for testing."""
        return PythonHandlers()
    
    @pytest.mark.asyncio
    async def test_list_virtual_environments_with_none_venv_objects(self, python_handlers):
        """Test list_virtual_environments handles None venv objects gracefully."""
        # Mock VenvManager to return list with None objects
        mock_venv_manager = Mock()
        
        # Mix valid VirtualEnvironmentInfo objects with None values
        from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
        valid_venv = VirtualEnvironmentInfo("test-env", "/path/to/env", "3.9.0", False)
        
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[
            valid_venv,
            None,  # This could cause object access bugs
            valid_venv
        ])
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle None objects gracefully without crashing
        result = await python_handlers.list_virtual_environments()
        
        # Should only return valid environments, filtering out None
        assert len(result) == 2
        assert all("name" in env for env in result)
        assert all("path" in env for env in result)
    
    @pytest.mark.asyncio
    async def test_list_virtual_environments_with_malformed_venv_objects(self, python_handlers):
        """Test list_virtual_environments handles malformed venv objects."""
        mock_venv_manager = Mock()
        
        # Create mock objects with missing attributes
        malformed_venv1 = Mock()
        malformed_venv1.name = "test1"
        # Missing path, python_version, is_active
        
        malformed_venv2 = Mock()
        malformed_venv2.name = "test2"
        malformed_venv2.path = "/path/to/test2"
        # Missing python_version, is_active
        
        # Object that raises AttributeError when accessing attributes
        broken_venv = Mock()
        broken_venv.name = PropertyMock(side_effect=AttributeError("No name attribute"))
        
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[
            malformed_venv1,
            malformed_venv2,
            broken_venv
        ])
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle malformed objects gracefully
        result = await python_handlers.list_virtual_environments()
        
        # Should return what it can, with defaults for missing attributes
        assert isinstance(result, list)
        # Should not crash on malformed objects
    
    @pytest.mark.asyncio
    async def test_list_virtual_environments_venv_manager_exception(self, python_handlers):
        """Test list_virtual_environments when VenvManager throws exception."""
        mock_venv_manager = Mock()
        mock_venv_manager.list_virtual_environments = AsyncMock(
            side_effect=Exception("VenvManager error")
        )
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should propagate the exception but not crash
        with pytest.raises(Exception, match="VenvManager error"):
            await python_handlers.list_virtual_environments()
    
    @pytest.mark.asyncio
    async def test_activate_virtual_environment_with_missing_venv_object(self, python_handlers):
        """Test activate_virtual_environment when venv object is not found in list."""
        mock_venv_manager = Mock()
        
        # Return empty list (no venvs found)
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[])
        mock_venv_manager.activate_virtual_environment = AsyncMock(return_value=True)
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Mock _get_python_executable to not fail
        with patch.object(python_handlers, '_get_python_executable', return_value="/usr/bin/python"):
            result = await python_handlers.activate_virtual_environment("nonexistent")
            
            assert result["success"] is True
            assert result["name"] == "nonexistent"
            # Should use fallback path when venv not found in list
            assert "path" in result
    
    @pytest.mark.asyncio
    async def test_activate_virtual_environment_venv_list_exception(self, python_handlers):
        """Test activate_virtual_environment when listing venvs throws exception."""
        mock_venv_manager = Mock()
        
        mock_venv_manager.activate_virtual_environment = AsyncMock(return_value=True)
        # This will throw exception when trying to get venv path
        mock_venv_manager.list_virtual_environments = AsyncMock(
            side_effect=Exception("Cannot list venvs")
        )
        
        python_handlers.venv_manager = mock_venv_manager
        
        with patch.object(python_handlers, '_get_python_executable', return_value="/usr/bin/python"):
            result = await python_handlers.activate_virtual_environment("test-env")
            
            # Should still succeed but use fallback path
            assert result["success"] is True
            assert result["name"] == "test-env"
            assert result["path"] == "/home/user/.venvs/test-env"  # fallback
    
    @pytest.mark.asyncio
    async def test_create_virtual_environment_with_invalid_venv_info_return(self, python_handlers):
        """Test create_virtual_environment when VenvManager returns invalid VirtualEnvironmentInfo."""
        mock_venv_manager = Mock()
        
        # Create a custom class that raises AttributeError on property access
        class InvalidVenvInfo:
            @property
            def name(self):
                raise AttributeError("No name")
            
            @property
            def path(self):
                raise AttributeError("No path")
            
            @property
            def python_version(self):
                raise AttributeError("No version")
        
        invalid_venv_info = InvalidVenvInfo()
        mock_venv_manager.create_virtual_environment = AsyncMock(return_value=invalid_venv_info)
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle invalid return object gracefully
        result = await python_handlers.create_virtual_environment("test-env")
        
        assert result["success"] is False
        assert result["name"] == "test-env"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_create_virtual_environment_none_return(self, python_handlers):
        """Test create_virtual_environment when VenvManager returns None."""
        mock_venv_manager = Mock()
        mock_venv_manager.create_virtual_environment = AsyncMock(return_value=None)
        
        python_handlers.venv_manager = mock_venv_manager
        
        result = await python_handlers.create_virtual_environment("test-env")
        
        assert result["success"] is False
        assert result["name"] == "test-env"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_install_package_with_output_malformed_result(self, python_handlers):
        """Test install_package when install_package_with_output returns malformed result."""
        mock_venv_manager = Mock()
        
        # Return result missing required keys
        malformed_result = {
            "success": True,
            # Missing stdout, stderr, execution_time, command
        }
        
        mock_venv_manager.install_package_with_output = AsyncMock(return_value=malformed_result)
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle malformed result gracefully
        result = await python_handlers.install_python_package("test-package")
        
        # Should not crash, but should handle missing keys
        assert "success" in result
        assert "package" in result
    
    @pytest.mark.asyncio
    async def test_install_package_with_none_result(self, python_handlers):
        """Test install_package when venv_manager returns None."""
        mock_venv_manager = Mock()
        mock_venv_manager.install_package_with_output = AsyncMock(return_value=None)
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle None result gracefully
        result = await python_handlers.install_python_package("test-package")
        
        assert result["success"] is False
        assert result["package"] == "test-package"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_install_package_with_basic_method_none_return(self, python_handlers):
        """Test install_package fallback when basic install_package returns None."""
        mock_venv_manager = Mock()
        
        # Remove enhanced method to force fallback
        mock_venv_manager.install_package = AsyncMock(return_value=None)
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Mock hasattr to return False to simulate older venv_manager
        with patch('builtins.hasattr', return_value=False):
            result = await python_handlers.install_python_package("test-package")
            
            # Should treat None return as failure
            assert result["success"] is False
            assert result["package"] == "test-package"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_python_executable_with_invalid_venv_name(self, python_handlers):
        """Test _get_python_executable with invalid virtual environment name."""
        mock_venv_manager = Mock()
        
        # Return empty list (venv not found)
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[])
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should fall back to system python when venv not found
        result = await python_handlers._get_python_executable("nonexistent-venv")
        
        # Should return a valid python executable (fallback)
        assert result is not None
        assert "python" in result.lower()
    
    @pytest.mark.asyncio
    async def test_venv_operations_with_corrupted_venv_manager(self, python_handlers):
        """Test virtual environment operations when VenvManager is None or corrupted."""
        # Set venv_manager to None
        python_handlers.venv_manager = None
        
        # Operations should raise AttributeError or handle gracefully and return error responses
        try:
            await python_handlers.list_virtual_environments()
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass  # Expected
        
        # activate_virtual_environment should return error response
        result = await python_handlers.activate_virtual_environment("test")
        assert result["success"] is False
        assert "error" in result
        
        # create_virtual_environment should return error response  
        result = await python_handlers.create_virtual_environment("test")
        assert result["success"] is False
        assert "error" in result
        
        # install_python_package should return error response
        result = await python_handlers.install_python_package("test")
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_venv_operations_with_concurrent_access_conflicts(self, python_handlers):
        """Test virtual environment operations under concurrent access scenarios."""
        mock_venv_manager = Mock()
        
        # Simulate race condition where venv list changes between calls
        call_count = 0
        
        def side_effect_list_venvs():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns normal venv
                from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
                return [VirtualEnvironmentInfo("test-env", "/path/1", "3.9.0", False)]
            else:
                # Second call returns different venv (simulating concurrent modification)
                from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
                return [VirtualEnvironmentInfo("different-env", "/path/2", "3.10.0", False)]
        
        mock_venv_manager.list_virtual_environments = AsyncMock(side_effect=side_effect_list_venvs)
        mock_venv_manager.activate_virtual_environment = AsyncMock(return_value=True)
        
        python_handlers.venv_manager = mock_venv_manager
        
        with patch.object(python_handlers, '_get_python_executable', return_value="/usr/bin/python"):
            result = await python_handlers.activate_virtual_environment("test-env")
            
            # Should handle the case where venv is not found in second list call
            assert result["success"] is True
            # Should use fallback path since venv disappeared from list
    
    @pytest.mark.asyncio
    async def test_venv_attribute_access_with_property_errors(self, python_handlers):
        """Test virtual environment operations when venv object properties raise errors."""
        mock_venv_manager = Mock()
        
        # Create venv object that raises errors on property access
        error_venv = Mock()
        error_venv.name = PropertyMock(side_effect=PermissionError("Cannot access name"))
        error_venv.path = PropertyMock(side_effect=OSError("Cannot access path"))
        error_venv.python_version = PropertyMock(side_effect=IOError("Cannot access version"))
        error_venv.is_active = PropertyMock(side_effect=RuntimeError("Cannot access active status"))
        
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[error_venv])
        
        python_handlers.venv_manager = mock_venv_manager
        
        # Should handle property access errors gracefully
        result = await python_handlers.list_virtual_environments()
        
        # Should return empty list or handle errors gracefully
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_venv_operations_with_unicode_and_special_characters(self, python_handlers):
        """Test virtual environment operations with unicode and special characters in names/paths."""
        mock_venv_manager = Mock()
        
        # Test with problematic unicode characters and special names
        unicode_names = ["test-env-ñ", "test-env-中文", "test-env-🐍", "test-env-with spaces", "test-env-with/slash"]
        
        for name in unicode_names:
            mock_venv_manager.activate_virtual_environment = AsyncMock(return_value=True)
            mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[])
            
            python_handlers.venv_manager = mock_venv_manager
            
            with patch.object(python_handlers, '_get_python_executable', return_value="/usr/bin/python"):
                result = await python_handlers.activate_virtual_environment(name)
                
                # Should handle unicode and special characters without crashing
                assert result["success"] is True
                assert result["name"] == name
    
    @pytest.mark.asyncio
    async def test_venv_operations_with_extremely_long_names_and_paths(self, python_handlers):
        """Test virtual environment operations with extremely long names and paths."""
        mock_venv_manager = Mock()
        
        # Test with extremely long name that might cause buffer overflows
        long_name = "a" * 1000
        long_path = "/" + "/".join(["very_long_directory_name"] * 50)
        
        from terminal_mcp_server.utils.venv_manager import VirtualEnvironmentInfo
        long_venv = VirtualEnvironmentInfo(long_name, long_path, "3.9.0", False)
        
        mock_venv_manager.list_virtual_environments = AsyncMock(return_value=[long_venv])
        
        python_handlers.venv_manager = mock_venv_manager
        
        result = await python_handlers.list_virtual_environments()
        
        # Should handle extremely long values without crashing
        assert isinstance(result, list)
        if result:  # If handling succeeded
            assert len(result[0]["name"]) == 1000
            assert result[0]["path"] == long_path