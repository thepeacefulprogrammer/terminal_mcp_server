"""
Tests for Terminal MCP Server directory structure to ensure all required
handlers, utilities, and models are properly organized.
"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def src_dir(project_root):
    """Get the src directory."""
    return project_root / "src" / "terminal_mcp_server"


def test_main_package_structure_exists(src_dir):
    """Test that the main package structure exists."""
    assert src_dir.exists(), "Main package directory should exist"
    assert (src_dir / "__init__.py").exists(), "Package __init__.py should exist"
    assert (src_dir / "server.py").exists(), "Main server module should exist"


def test_handlers_directory_structure(src_dir):
    """Test that the handlers directory and required handler modules exist."""
    handlers_dir = src_dir / "handlers"
    assert handlers_dir.exists(), "Handlers directory should exist"
    assert handlers_dir.is_dir(), "Handlers should be a directory"
    assert (handlers_dir / "__init__.py").exists(), "Handlers __init__.py should exist"
    
    # Test for required handler modules
    required_handlers = [
        "command_handlers.py",
        "process_handlers.py", 
        "python_handlers.py",
        "environment_handlers.py"
    ]
    
    for handler_file in required_handlers:
        handler_path = handlers_dir / handler_file
        assert handler_path.exists(), f"Handler {handler_file} should exist"
        assert handler_path.is_file(), f"Handler {handler_file} should be a file"


def test_models_directory_structure(src_dir):
    """Test that the models directory and required model modules exist."""
    models_dir = src_dir / "models"
    assert models_dir.exists(), "Models directory should exist"
    assert models_dir.is_dir(), "Models should be a directory"
    assert (models_dir / "__init__.py").exists(), "Models __init__.py should exist"
    
    # Test for required model modules
    required_models = [
        "terminal_models.py"
    ]
    
    for model_file in required_models:
        model_path = models_dir / model_file
        assert model_path.exists(), f"Model {model_file} should exist"
        assert model_path.is_file(), f"Model {model_file} should be a file"


def test_utils_directory_structure(src_dir):
    """Test that the utils directory and required utility modules exist."""
    utils_dir = src_dir / "utils"
    assert utils_dir.exists(), "Utils directory should exist"
    assert utils_dir.is_dir(), "Utils should be a directory"
    assert (utils_dir / "__init__.py").exists(), "Utils __init__.py should exist"
    
    # Test for required utility modules
    required_utils = [
        "command_executor.py",
        "process_manager.py",
        "output_streamer.py",
        "venv_manager.py"
    ]
    
    for util_file in required_utils:
        util_path = utils_dir / util_file
        assert util_path.exists(), f"Utility {util_file} should exist"
        assert util_path.is_file(), f"Utility {util_file} should be a file"


def test_legacy_example_files_removed(src_dir):
    """Test that legacy example files from scaffolding have been removed."""
    handlers_dir = src_dir / "handlers"
    models_dir = src_dir / "models"
    
    # These files should not exist (they're from the scaffolding template)
    legacy_files = [
        handlers_dir / "example_handlers.py",
        models_dir / "example_models.py"
    ]
    
    for legacy_file in legacy_files:
        assert not legacy_file.exists(), f"Legacy file {legacy_file.name} should be removed"


def test_handler_modules_are_importable(src_dir):
    """Test that all handler modules can be imported without errors."""
    import sys
    import importlib
    
    # Add src to path temporarily
    src_path = str(src_dir.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        # Test importing handler modules
        handler_modules = [
            "terminal_mcp_server.handlers.command_handlers",
            "terminal_mcp_server.handlers.process_handlers",
            "terminal_mcp_server.handlers.python_handlers", 
            "terminal_mcp_server.handlers.environment_handlers"
        ]
        
        for module_name in handler_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} should be importable"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    finally:
        # Clean up sys.path
        if src_path in sys.path:
            sys.path.remove(src_path)


def test_model_modules_are_importable(src_dir):
    """Test that all model modules can be imported without errors."""
    import sys
    import importlib
    
    # Add src to path temporarily
    src_path = str(src_dir.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        # Test importing model modules
        model_modules = [
            "terminal_mcp_server.models.terminal_models"
        ]
        
        for module_name in model_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} should be importable"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    finally:
        # Clean up sys.path
        if src_path in sys.path:
            sys.path.remove(src_path)


def test_utility_modules_are_importable(src_dir):
    """Test that all utility modules can be imported without errors."""
    import sys
    import importlib
    
    # Add src to path temporarily
    src_path = str(src_dir.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        # Test importing utility modules
        util_modules = [
            "terminal_mcp_server.utils.command_executor",
            "terminal_mcp_server.utils.process_manager",
            "terminal_mcp_server.utils.output_streamer",
            "terminal_mcp_server.utils.venv_manager"
        ]
        
        for module_name in util_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} should be importable"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
    finally:
        # Clean up sys.path
        if src_path in sys.path:
            sys.path.remove(src_path)


def test_directory_organization_follows_conventions(src_dir):
    """Test that the directory organization follows Python packaging conventions."""
    # Each directory should have an __init__.py file
    subdirs = ["handlers", "models", "utils"]
    
    for subdir_name in subdirs:
        subdir = src_dir / subdir_name
        init_file = subdir / "__init__.py"
        assert init_file.exists(), f"{subdir_name}/__init__.py should exist for proper Python package structure"
        
        # Check that subdirectory contains at least one .py file besides __init__.py
        py_files = list(subdir.glob("*.py"))
        non_init_files = [f for f in py_files if f.name != "__init__.py"]
        assert len(non_init_files) > 0, f"{subdir_name} should contain at least one module besides __init__.py"


def test_handlers_directory_exists(src_dir):
    """Test that the handlers directory exists with required files."""
    handlers_dir = src_dir / "handlers"
    assert handlers_dir.exists(), "Handlers directory should exist"
    
    required_handlers = [
        "command_handlers.py",
        "process_handlers.py", 
        "python_handlers.py",
        "environment_handlers.py"
    ]
    
    for handler_file in required_handlers:
        assert (handlers_dir / handler_file).exists(), f"Handler {handler_file} should exist"


def test_models_directory_exists(src_dir):
    """Test that the models directory exists with required files."""
    models_dir = src_dir / "models"
    assert models_dir.exists(), "Models directory should exist"
    assert (models_dir / "terminal_models.py").exists(), "terminal_models.py should exist"


def test_utils_directory_exists(src_dir):
    """Test that the utils directory exists with required files."""
    utils_dir = src_dir / "utils"
    assert utils_dir.exists(), "Utils directory should exist"
    
    required_utils = [
        "command_executor.py",
        "process_manager.py",
        "output_streamer.py",
        "venv_manager.py"
    ]
    
    for util_file in required_utils:
        assert (utils_dir / util_file).exists(), f"Utility {util_file} should exist" 