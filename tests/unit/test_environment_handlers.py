"""Tests for environment and directory management handlers."""

import os
import tempfile
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from src.terminal_mcp_server.handlers.environment_handlers import EnvironmentHandlers


@pytest.fixture
def environment_handlers():
    """Create an EnvironmentHandlers instance for testing."""
    # Save original directory
    original_dir = os.getcwd()
    
    yield EnvironmentHandlers()
    
    # Restore original directory after test
    try:
        os.chdir(original_dir)
    except Exception:
        # If original directory is not available, go to a safe directory
        os.chdir(os.path.expanduser("~"))


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.mark.asyncio
async def test_environment_handlers_initialization(environment_handlers):
    """Test that EnvironmentHandlers initializes properly."""
    assert environment_handlers is not None
    assert hasattr(environment_handlers, 'get_current_directory')
    assert hasattr(environment_handlers, 'change_directory')
    assert hasattr(environment_handlers, 'get_environment_variables')
    assert hasattr(environment_handlers, 'set_environment_variable')
    assert hasattr(environment_handlers, 'register_tools')


@pytest.mark.asyncio
async def test_get_current_directory(environment_handlers):
    """Test getting the current working directory."""
    result = await environment_handlers.get_current_directory()
    
    assert isinstance(result, dict)
    assert "success" in result
    assert "current_directory" in result
    assert result["success"] is True
    assert isinstance(result["current_directory"], str)
    assert os.path.exists(result["current_directory"])


@pytest.mark.asyncio
async def test_change_directory_success(environment_handlers, temp_directory):
    """Test successfully changing directory."""
    # Ensure temp directory exists
    assert os.path.exists(temp_directory)
    
    result = await environment_handlers.change_directory(temp_directory)
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["new_directory"] == temp_directory
    assert result["previous_directory"] is not None
    assert "changed_at" in result


@pytest.mark.asyncio
async def test_change_directory_nonexistent(environment_handlers):
    """Test changing to a non-existent directory."""
    nonexistent_path = "/this/path/should/not/exist"
    
    result = await environment_handlers.change_directory(nonexistent_path)
    
    assert isinstance(result, dict)
    assert result["success"] is False
    assert "error" in result
    assert nonexistent_path in result["error"]


@pytest.mark.asyncio
async def test_change_directory_not_a_directory(environment_handlers, temp_directory):
    """Test changing to a path that exists but is not a directory."""
    # Create a temporary file
    temp_file = os.path.join(temp_directory, "test_file.txt")
    with open(temp_file, "w") as f:
        f.write("test content")
    
    result = await environment_handlers.change_directory(temp_file)
    
    assert isinstance(result, dict)
    assert result["success"] is False
    assert "error" in result
    assert "not a directory" in result["error"].lower()


@pytest.mark.asyncio
async def test_change_directory_permission_denied(environment_handlers):
    """Test changing to a directory without permission."""
    # Use a system directory that typically has restricted access
    restricted_path = "/root"
    
    # Only test if the path exists and we don't have access
    if os.path.exists(restricted_path) and not os.access(restricted_path, os.R_OK):
        result = await environment_handlers.change_directory(restricted_path)
        
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_get_environment_variables_all(environment_handlers):
    """Test getting all environment variables."""
    result = await environment_handlers.get_environment_variables()
    
    assert isinstance(result, dict)
    assert "success" in result
    assert "environment_variables" in result
    assert "count" in result
    assert result["success"] is True
    assert isinstance(result["environment_variables"], dict)
    assert isinstance(result["count"], int)
    assert result["count"] > 0
    
    # Check that common environment variables exist
    env_vars = result["environment_variables"]
    assert "PATH" in env_vars or "Path" in env_vars  # Windows uses "Path"


@pytest.mark.asyncio
async def test_get_environment_variables_specific(environment_handlers):
    """Test getting specific environment variables."""
    # Test getting PATH variable
    result = await environment_handlers.get_environment_variables(variables=["PATH"])
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert "environment_variables" in result
    
    env_vars = result["environment_variables"]
    # Should contain PATH or be empty if PATH doesn't exist (unlikely)
    assert len(env_vars) <= 1


@pytest.mark.asyncio
async def test_get_environment_variables_nonexistent(environment_handlers):
    """Test getting non-existent environment variables."""
    nonexistent_vars = ["NONEXISTENT_VAR_12345", "ANOTHER_FAKE_VAR"]
    
    result = await environment_handlers.get_environment_variables(variables=nonexistent_vars)
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["environment_variables"] == {}
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_set_environment_variable_success(environment_handlers):
    """Test successfully setting an environment variable."""
    var_name = "TEST_VAR_12345"
    var_value = "test_value"
    
    # Ensure the variable doesn't exist before
    if var_name in os.environ:
        del os.environ[var_name]
    
    result = await environment_handlers.set_environment_variable(var_name, var_value)
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["variable"] == var_name
    assert result["value"] == var_value
    assert result["previous_value"] is None
    assert "set_at" in result
    
    # Verify the variable was actually set
    assert os.environ.get(var_name) == var_value
    
    # Cleanup
    if var_name in os.environ:
        del os.environ[var_name]


@pytest.mark.asyncio
async def test_set_environment_variable_overwrite(environment_handlers):
    """Test overwriting an existing environment variable."""
    var_name = "TEST_OVERWRITE_VAR"
    original_value = "original_value"
    new_value = "new_value"
    
    # Set initial value
    os.environ[var_name] = original_value
    
    result = await environment_handlers.set_environment_variable(var_name, new_value)
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["variable"] == var_name
    assert result["value"] == new_value
    assert result["previous_value"] == original_value
    
    # Verify the variable was updated
    assert os.environ.get(var_name) == new_value
    
    # Cleanup
    if var_name in os.environ:
        del os.environ[var_name]


@pytest.mark.asyncio
async def test_set_environment_variable_empty_value(environment_handlers):
    """Test setting an environment variable to an empty value."""
    var_name = "TEST_EMPTY_VAR"
    var_value = ""
    
    result = await environment_handlers.set_environment_variable(var_name, var_value)
    
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["value"] == ""
    
    # Verify the variable was set to empty
    assert os.environ.get(var_name) == ""
    
    # Cleanup
    if var_name in os.environ:
        del os.environ[var_name]


@pytest.mark.asyncio
async def test_mcp_tool_registration(environment_handlers):
    """Test that environment tools can be registered with MCP server."""
    mock_server = MagicMock()
    registered_tools = {}
    
    def tool_decorator():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func
        return decorator
    
    mock_server.tool = tool_decorator
    
    # Register tools
    environment_handlers.register_tools(mock_server)
    
    # Verify all expected tools are registered
    expected_tools = [
        "get_current_directory",
        "change_directory", 
        "get_environment_variables",
        "set_environment_variable"
    ]
    
    for tool_name in expected_tools:
        assert tool_name in registered_tools
        assert callable(registered_tools[tool_name])


@pytest.mark.asyncio
async def test_mcp_get_current_directory_tool(environment_handlers):
    """Test the MCP get_current_directory tool."""
    mock_server = MagicMock()
    registered_tools = {}
    
    def tool_decorator():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func
        return decorator
    
    mock_server.tool = tool_decorator
    
    # Register tools
    environment_handlers.register_tools(mock_server)
    
    # Get the tool function
    tool_func = registered_tools['get_current_directory']
    
    # Call the tool
    result_json = await tool_func()
    result = json.loads(result_json)
    
    assert "success" in result
    assert "current_directory" in result
    assert result["success"] is True


@pytest.mark.asyncio
async def test_mcp_change_directory_tool(environment_handlers, temp_directory):
    """Test the MCP change_directory tool."""
    mock_server = MagicMock()
    registered_tools = {}
    
    def tool_decorator():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func
        return decorator
    
    mock_server.tool = tool_decorator
    
    # Register tools
    environment_handlers.register_tools(mock_server)
    
    # Get the tool function
    tool_func = registered_tools['change_directory']
    
    # Call the tool
    result_json = await tool_func(temp_directory)
    result = json.loads(result_json)
    
    assert "success" in result
    assert result["success"] is True
    assert result["new_directory"] == temp_directory


@pytest.mark.asyncio
async def test_mcp_set_environment_variable_tool(environment_handlers):
    """Test the MCP set_environment_variable tool."""
    mock_server = MagicMock()
    registered_tools = {}
    
    def tool_decorator():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func
        return decorator
    
    mock_server.tool = tool_decorator
    
    # Register tools
    environment_handlers.register_tools(mock_server)
    
    # Get the tool function
    tool_func = registered_tools['set_environment_variable']
    
    # Call the tool
    var_name = "TEST_MCP_VAR"
    var_value = "test_mcp_value"
    
    result_json = await tool_func(var_name, var_value)
    result = json.loads(result_json)
    
    assert "success" in result
    assert result["success"] is True
    assert result["variable"] == var_name
    assert result["value"] == var_value
    
    # Cleanup
    if var_name in os.environ:
        del os.environ[var_name]


@pytest.mark.asyncio
async def test_error_handling_robustness(environment_handlers):
    """Test error handling for various edge cases."""
    # Test with None directory
    result = await environment_handlers.change_directory(None)
    assert result["success"] is False
    assert "error" in result
    
    # Test setting environment variable with None name
    result = await environment_handlers.set_environment_variable(None, "value")
    assert result["success"] is False
    assert "error" in result
    
    # Test setting environment variable with None value
    result = await environment_handlers.set_environment_variable("VAR_NAME", None)
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_directory_change_preserves_state(environment_handlers, temp_directory):
    """Test that directory changes work correctly and preserve previous state."""
    # Get original directory
    original_result = await environment_handlers.get_current_directory()
    original_dir = original_result["current_directory"]
    
    # Change to temp directory
    change_result = await environment_handlers.change_directory(temp_directory)
    assert change_result["success"] is True
    assert change_result["previous_directory"] == original_dir
    
    # Verify we're in the new directory
    current_result = await environment_handlers.get_current_directory()
    assert current_result["current_directory"] == temp_directory
    
    # Change back to original directory
    restore_result = await environment_handlers.change_directory(original_dir)
    assert restore_result["success"] is True
    assert restore_result["previous_directory"] == temp_directory 