"""
Tests to verify that all example/scaffolding files have been properly removed
and replaced with terminal-specific implementations.
"""

import pytest
from pathlib import Path


def test_no_example_handlers_exist():
    """Test that no example handler files exist in the project."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check that example handlers don't exist
    example_handler_files = [
        "src/terminal_mcp_server/handlers/example_handlers.py",
        "src/mcp_scaffolding/handlers/example_handlers.py",
    ]
    
    for file_path in example_handler_files:
        full_path = project_root / file_path
        assert not full_path.exists(), f"Example handler file should not exist: {file_path}"


def test_no_example_models_exist():
    """Test that no example model files exist in the project."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check that example models don't exist
    example_model_files = [
        "src/terminal_mcp_server/models/example_models.py",
        "src/mcp_scaffolding/models/example_models.py",
    ]
    
    for file_path in example_model_files:
        full_path = project_root / file_path
        assert not full_path.exists(), f"Example model file should not exist: {file_path}"


def test_no_example_tests_exist():
    """Test that no example test files exist in the project."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check that example test files don't exist
    example_test_files = [
        "tests/unit/test_example_handlers.py",
        "tests/unit/test_models.py",  # This was the old generic models test
    ]
    
    for file_path in example_test_files:
        full_path = project_root / file_path
        assert not full_path.exists(), f"Example test file should not exist: {file_path}"


def test_no_mcp_scaffolding_directory_exists():
    """Test that the old mcp_scaffolding directory structure doesn't exist."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check that old scaffolding directory is gone
    scaffolding_dirs = [
        "src/mcp_scaffolding",
        "src/mcp_scaffolding/handlers",
        "src/mcp_scaffolding/models",
        "src/mcp_scaffolding/utils",
    ]
    
    for dir_path in scaffolding_dirs:
        full_path = project_root / dir_path
        assert not full_path.exists(), f"Old scaffolding directory should not exist: {dir_path}"


def test_no_scaffolding_egg_info_exists():
    """Test that old egg-info directories don't exist."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check that old egg-info is gone
    old_egg_info = project_root / "src" / "mcp_scaffolding.egg-info"
    assert not old_egg_info.exists(), "Old mcp_scaffolding.egg-info should not exist"


def test_only_terminal_handlers_exist():
    """Test that only terminal-specific handlers exist."""
    project_root = Path(__file__).parent.parent.parent
    handlers_dir = project_root / "src" / "terminal_mcp_server" / "handlers"
    
    assert handlers_dir.exists(), "Terminal handlers directory should exist"
    
    # Expected terminal handler files
    expected_handlers = {
        "__init__.py",
        "command_handlers.py",
        "process_handlers.py", 
        "python_handlers.py",
        "environment_handlers.py"
    }
    
    # Get actual handler files
    actual_handlers = {f.name for f in handlers_dir.iterdir() if f.is_file()}
    
    # Should only have expected handlers, no example files
    assert actual_handlers == expected_handlers, (
        f"Handlers directory should only contain terminal handlers. "
        f"Expected: {expected_handlers}, Actual: {actual_handlers}"
    )


def test_only_terminal_models_exist():
    """Test that only terminal-specific models exist."""
    project_root = Path(__file__).parent.parent.parent
    models_dir = project_root / "src" / "terminal_mcp_server" / "models"
    
    assert models_dir.exists(), "Terminal models directory should exist"
    
    # Expected terminal model files
    expected_models = {
        "__init__.py",
        "terminal_models.py"
    }
    
    # Get actual model files
    actual_models = {f.name for f in models_dir.iterdir() if f.is_file()}
    
    # Should only have expected models, no example files
    assert actual_models == expected_models, (
        f"Models directory should only contain terminal models. "
        f"Expected: {expected_models}, Actual: {actual_models}"
    )


def test_only_terminal_tests_exist():
    """Test that only terminal-specific tests exist."""
    project_root = Path(__file__).parent.parent.parent
    tests_dir = project_root / "tests" / "unit"
    
    assert tests_dir.exists(), "Unit tests directory should exist"
    
    # Expected test files (no example tests)
    expected_tests = {
        "test_directory_structure.py",
        "test_module_structure.py", 
        "test_pyproject_config.py",
        "test_requirements.py",
        "test_terminal_models.py",
        "test_terminal_config.py",
        "test_scaffolding_cleanup.py",  # This test file itself
        "test_command_executor.py",     # New command executor tests
        "test_command_handlers.py",    # New command handlers tests
        "test_output_streamer.py",     # New output streamer tests
        "test_process_manager.py",     # New process manager tests
        "test_process_handlers.py",    # New process handlers tests
        "test_python_handlers.py",     # New python handlers tests
        "test_venv_manager.py",        # New venv manager tests
        "test_environment_handlers.py" # New environment handlers tests
    }
    
    # Get actual test files
    actual_tests = {f.name for f in tests_dir.iterdir() if f.is_file() and f.name.endswith('.py')}
    
    # Should only have expected tests, no example tests
    assert actual_tests == expected_tests, (
        f"Tests directory should only contain terminal tests. "
        f"Expected: {expected_tests}, Actual: {actual_tests}"
    )


def test_server_imports_only_terminal_handlers():
    """Test that server.py only imports terminal handlers, not example handlers."""
    project_root = Path(__file__).parent.parent.parent
    server_file = project_root / "src" / "terminal_mcp_server" / "server.py"
    
    assert server_file.exists(), "Server file should exist"
    
    # Read server file content
    content = server_file.read_text()
    
    # Should not import example handlers
    forbidden_imports = [
        "from .handlers.example_handlers",
        "import example_handlers",
        "example_handlers",
    ]
    
    for forbidden in forbidden_imports:
        assert forbidden not in content, f"Server should not import example handlers: {forbidden}"
    
    # Should import terminal handlers (check for the actual import pattern used)
    expected_imports = [
        "from terminal_mcp_server.handlers import (",
        "command_handlers,",
        "process_handlers,", 
        "python_handlers,",
        "environment_handlers,"
    ]
    
    for expected in expected_imports:
        assert expected in content, f"Server should import terminal handlers: {expected}"


def test_no_example_references_in_config():
    """Test that configuration files don't reference example/scaffolding inappropriately."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check config files
    config_files = [
        "config/config.yaml",
        "pyproject.toml"
    ]
    
    forbidden_terms = [
        "example_handlers",
        "example_models", 
        "mcp_scaffolding"
    ]
    
    for config_file in config_files:
        file_path = project_root / config_file
        if file_path.exists():
            content = file_path.read_text().lower()
            
            for term in forbidden_terms:
                assert term not in content, (
                    f"Config file {config_file} should not reference {term}"
                ) 