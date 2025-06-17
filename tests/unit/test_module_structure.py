"""
Unit tests for module structure and naming.

Tests to ensure the module has been properly renamed from mcp_scaffolding to terminal_mcp_server.
"""

import importlib
import sys
from pathlib import Path


def test_terminal_mcp_server_module_exists():
    """Test that terminal_mcp_server module exists and can be imported."""
    try:
        import terminal_mcp_server
        assert True, "terminal_mcp_server module imported successfully"
    except ImportError as e:
        assert False, f"terminal_mcp_server module cannot be imported: {e}"


def test_terminal_mcp_server_submodules_exist():
    """Test that terminal_mcp_server submodules exist."""
    expected_submodules = [
        "terminal_mcp_server.server",
        "terminal_mcp_server.utils",
        "terminal_mcp_server.utils.config",
        "terminal_mcp_server.utils.auth",
        "terminal_mcp_server.handlers",
        "terminal_mcp_server.models",
    ]
    
    missing_modules = []
    for module_name in expected_submodules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)
    
    assert not missing_modules, f"Missing terminal_mcp_server submodules: {missing_modules}"


def test_old_mcp_scaffolding_module_not_importable():
    """Test that the old mcp_scaffolding module is no longer importable."""
    try:
        import mcp_scaffolding
        # If we get here, the old module still exists (which we don't want)
        assert False, "Old mcp_scaffolding module should not be importable after renaming"
    except ImportError:
        # This is what we want - the old module should not be importable
        assert True, "Old mcp_scaffolding module correctly not importable"


def test_terminal_mcp_server_directory_exists():
    """Test that the terminal_mcp_server directory exists in src/."""
    src_path = Path(__file__).parent.parent.parent / "src"
    terminal_mcp_server_path = src_path / "terminal_mcp_server"
    
    assert terminal_mcp_server_path.exists(), "terminal_mcp_server directory should exist in src/"
    assert terminal_mcp_server_path.is_dir(), "terminal_mcp_server should be a directory"


def test_old_mcp_scaffolding_directory_not_exists():
    """Test that the old mcp_scaffolding directory no longer exists in src/."""
    src_path = Path(__file__).parent.parent.parent / "src"
    mcp_scaffolding_path = src_path / "mcp_scaffolding"
    
    assert not mcp_scaffolding_path.exists(), "Old mcp_scaffolding directory should not exist after renaming" 