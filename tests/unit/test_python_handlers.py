"""Tests for Python script execution handlers and MCP tools."""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
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
    
    # venv_manager.install_package returns bool
    mock_venv_manager.install_package.return_value = True
    
    result = await python_handlers.install_python_package(
        package="requests",
        virtual_environment="web_project"
    )
    
    assert result["success"] is True
    assert result["package"] == "requests==2.28.2"
    assert "Successfully installed" in result["installation_output"]


@pytest.mark.asyncio
async def test_install_python_package_with_version(python_handlers, mock_venv_manager):
    """Test installing a specific version of a Python package."""
    python_handlers.venv_manager = mock_venv_manager
    
    # venv_manager.install_package returns bool
    mock_venv_manager.install_package.return_value = True
    
    result = await python_handlers.install_python_package(
        package="django==4.1.0",
        virtual_environment="web_app"
    )
    
    assert result["success"] is True
    assert "4.1.0" in result["package"]


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
            # Expected: 1 (test_connection) + 1 (execute_command) + 6 (process tools) + 9 (python tools) = 17
            expected_total = 17
            assert len(tool_names) == expected_total, f"Expected exactly {expected_total} tools, got {len(tool_names)}: {tool_names}"
            
            # Verify specific tool categories are present
            assert "test_connection" in tool_names
            assert "execute_command" in tool_names
            assert "execute_command_background" in tool_names