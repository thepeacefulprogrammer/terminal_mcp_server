"""
Tests for pyproject.toml configuration to ensure it's properly set up for Terminal MCP Server.
"""

import toml
from pathlib import Path
import pytest


@pytest.fixture
def pyproject_data():
    """Load and parse pyproject.toml data."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        return toml.load(f)


def test_project_name_updated(pyproject_data):
    """Test that project name has been updated from scaffolding to terminal-mcp-server."""
    assert pyproject_data["project"]["name"] == "terminal-mcp-server"
    assert "scaffolding" not in pyproject_data["project"]["name"].lower()


def test_project_description_updated(pyproject_data):
    """Test that project description reflects terminal MCP server functionality."""
    description = pyproject_data["project"]["description"]
    assert "terminal" in description.lower()
    assert "command execution" in description.lower()
    assert "scaffolding" not in description.lower()


def test_project_keywords_updated(pyproject_data):
    """Test that keywords reflect terminal functionality, not scaffolding."""
    keywords = pyproject_data["project"]["keywords"]
    
    # Should have terminal-related keywords
    assert "terminal" in keywords
    assert "command-execution" in keywords
    
    # Should not have scaffolding-related keywords
    assert "scaffolding" not in keywords
    assert "template" not in keywords


def test_script_entry_point_updated(pyproject_data):
    """Test that script entry point uses terminal-mcp-server command."""
    scripts = pyproject_data["project"]["scripts"]
    assert "terminal-mcp-server" in scripts
    assert scripts["terminal-mcp-server"] == "terminal_mcp_server.server:main"
    
    # Should not have old scaffolding script
    assert "mcp-scaffolding-server" not in scripts


def test_dependencies_include_terminal_requirements(pyproject_data):
    """Test that dependencies include psutil and aiofiles for terminal operations."""
    dependencies = pyproject_data["project"]["dependencies"]
    
    # Check for terminal-specific dependencies
    psutil_found = any("psutil" in dep for dep in dependencies)
    aiofiles_found = any("aiofiles" in dep for dep in dependencies)
    
    assert psutil_found, "psutil dependency required for process management"
    assert aiofiles_found, "aiofiles dependency required for async file operations"


def test_urls_updated_from_scaffolding(pyproject_data):
    """Test that project URLs have been updated from scaffolding references."""
    urls = pyproject_data["project"]["urls"]
    
    for url_key, url_value in urls.items():
        assert "mcp-scaffolding" not in url_value, f"URL {url_key} still contains scaffolding reference: {url_value}"
        assert "terminal-mcp-server" in url_value, f"URL {url_key} should contain terminal-mcp-server reference: {url_value}"


def test_isort_known_first_party_updated(pyproject_data):
    """Test that isort configuration uses correct module name."""
    isort_config = pyproject_data["tool"]["isort"]
    known_first_party = isort_config["known_first_party"]
    
    assert "terminal_mcp_server" in known_first_party
    assert "mcp_scaffolding" not in known_first_party


def test_mypy_configuration_compatible(pyproject_data):
    """Test that mypy configuration is properly set up."""
    mypy_config = pyproject_data["tool"]["mypy"]
    
    # Should have proper mypy_path for src layout
    assert mypy_config["mypy_path"] == "src"
    assert mypy_config["explicit_package_bases"] is True
    assert mypy_config["namespace_packages"] is True


def test_pytest_configuration_proper(pyproject_data):
    """Test that pytest configuration includes proper test paths and options."""
    pytest_config = pyproject_data["tool"]["pytest"]["ini_options"]
    
    # Should include both src and tests in testpaths
    testpaths = pytest_config["testpaths"]
    assert "src" in testpaths
    assert "tests" in testpaths
    
    # Should have asyncio mode enabled for async tests
    assert pytest_config["asyncio_mode"] == "auto" 