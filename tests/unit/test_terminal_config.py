"""
Tests for Terminal MCP Server configuration to ensure all required
settings are properly configured for terminal command execution.
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def config_data():
    """Load and parse config.yaml data."""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def test_server_config_updated_for_terminal(config_data):
    """Test that server configuration reflects terminal MCP server."""
    server_config = config_data["server"]
    
    assert server_config["name"] == "terminal-mcp-server"
    assert "terminal" in server_config["description"].lower()
    assert server_config["host"] == "localhost"
    assert isinstance(server_config["port"], int)


def test_terminal_execution_config_exists(config_data):
    """Test that terminal execution configuration section exists."""
    assert "terminal" in config_data, "Terminal configuration section should exist"
    
    terminal_config = config_data["terminal"]
    assert "execution" in terminal_config, "Execution settings should exist"


def test_process_management_config_exists(config_data):
    """Test that process management configuration exists."""
    terminal_config = config_data["terminal"]
    assert "processes" in terminal_config, "Process management settings should exist"


def test_security_config_exists(config_data):
    """Test that security configuration exists."""
    terminal_config = config_data["terminal"]
    assert "security" in terminal_config, "Security settings should exist"


def test_output_streaming_config_exists(config_data):
    """Test that output streaming configuration exists."""
    terminal_config = config_data["terminal"]
    
    assert "output" in terminal_config, "Output settings should exist"
    output = terminal_config["output"]
    
    assert "buffer_size" in output, "Output buffer size should be configured"
    assert isinstance(output["buffer_size"], int), "Buffer size should be integer"
    assert output["buffer_size"] > 0, "Buffer size should be positive"
    
    assert "max_output_size" in output, "Max output size should be configured"
    assert isinstance(output["max_output_size"], int), "Max output size should be integer"
    
    assert "stream_real_time" in output, "Real-time streaming setting should exist"
    assert isinstance(output["stream_real_time"], bool), "Streaming should be boolean"
    
    assert "include_timestamps" in output, "Timestamp setting should exist"
    assert isinstance(output["include_timestamps"], bool), "Timestamps should be boolean"


def test_python_environment_config_exists(config_data):
    """Test that Python environment configuration exists."""
    terminal_config = config_data["terminal"]
    
    assert "python" in terminal_config, "Python settings should exist"
    python = terminal_config["python"]
    
    assert "default_interpreter" in python, "Default Python interpreter should be configured"
    assert isinstance(python["default_interpreter"], str), "Interpreter should be string"
    
    assert "venv_directory" in python, "Virtual environment directory should be configured"
    assert isinstance(python["venv_directory"], str), "Venv directory should be string"
    
    assert "auto_activate_venv" in python, "Auto-activate venv setting should exist"
    assert isinstance(python["auto_activate_venv"], bool), "Auto-activate should be boolean"
    
    assert "pip_install_timeout" in python, "Pip install timeout should be configured"
    assert isinstance(python["pip_install_timeout"], int), "Pip timeout should be integer"


def test_logging_config_supports_terminal_operations(config_data):
    """Test that logging configuration supports terminal operations."""
    logging_config = config_data["logging"]
    
    # Should have appropriate log level for terminal operations
    assert "level" in logging_config, "Log level should be configured"
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert logging_config["level"] in valid_levels, f"Log level should be one of {valid_levels}"
    
    # Should have file logging for command history
    assert "file" in logging_config, "File logging should be configured"
    file_config = logging_config["file"]
    
    assert "enabled" in file_config, "File logging enabled setting should exist"
    assert "path" in file_config, "Log file path should be configured"
    assert "max_size" in file_config, "Max log file size should be configured"
    assert "backup_count" in file_config, "Log backup count should be configured"


def test_config_has_reasonable_defaults(config_data):
    """Test that configuration has reasonable default values."""
    terminal_config = config_data["terminal"]
    
    # Execution defaults
    execution = terminal_config["execution"]
    assert 1 <= execution["default_timeout"] <= 300, "Default timeout should be reasonable (1-300 seconds)"
    assert 60 <= execution["max_timeout"] <= 3600, "Max timeout should be reasonable (1-60 minutes)"
    
    # Process limits
    processes = terminal_config["processes"]
    assert 1 <= processes["max_background_processes"] <= 50, "Max processes should be reasonable (1-50)"
    assert 10 <= processes["cleanup_interval"] <= 300, "Cleanup interval should be reasonable (10-300 seconds)"
    
    # Security
    security = terminal_config["security"]
    assert 100 <= security["max_command_length"] <= 10000, "Max command length should be reasonable"
    
    # Output
    output = terminal_config["output"]
    assert 1024 <= output["buffer_size"] <= 65536, "Buffer size should be reasonable (1KB-64KB)"
    assert 1048576 <= output["max_output_size"] <= 104857600, "Max output should be reasonable (1MB-100MB)"


def test_config_file_is_valid_yaml(config_data):
    """Test that the config file is valid YAML and properly structured."""
    # If we got here, the YAML loaded successfully
    assert isinstance(config_data, dict), "Config should be a dictionary"
    
    # Check required top-level sections
    required_sections = ["server", "logging", "terminal"]
    for section in required_sections:
        assert section in config_data, f"Required section '{section}' should exist"
        assert isinstance(config_data[section], dict), f"Section '{section}' should be a dictionary" 