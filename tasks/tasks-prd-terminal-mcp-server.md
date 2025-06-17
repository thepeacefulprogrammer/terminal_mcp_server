# Task List: Terminal MCP Server Implementation

## Relevant Files

- `requirements.txt` - Updated with new dependencies for terminal operations and process management (psutil, aiofiles).
- `tests/unit/test_requirements.py` - Unit tests to validate required dependencies are present in requirements.txt.
- `tests/unit/test_module_structure.py` - Unit tests to verify module structure and naming after rename.
- `src/terminal_mcp_server/__init__.py` - Main module initialization (renamed from mcp_scaffolding) with updated class imports.
- `src/terminal_mcp_server/server.py` - Main MCP server implementation with terminal-specific tools (renamed with updated class names and log messages).
- `src/terminal_mcp_server/handlers/` - Core handlers directory (renamed from mcp_scaffolding).
- `src/terminal_mcp_server/utils/` - Utility modules directory (renamed from mcp_scaffolding).
- `src/terminal_mcp_server/models/` - Data models directory (renamed from mcp_scaffolding).
- `pyproject.toml` - Updated project configuration with new module references, project name, script entry points, dependencies, URLs, and pytest configuration.
- `Makefile` - Updated with new module run commands.
- `tests/unit/test_models.py` - Updated imports to use terminal_mcp_server.
- `tests/unit/test_example_handlers.py` - Updated imports to use terminal_mcp_server.
- `config/config.yaml` - Updated server name and description to Terminal MCP Server.
- `tests/unit/test_pyproject_config.py` - Comprehensive tests for pyproject.toml configuration validation.
- `src/terminal_mcp_server/handlers/command_handlers.py` - Core command execution handlers with placeholder implementations.
- `src/terminal_mcp_server/handlers/process_handlers.py` - Complete background process management handlers with 6 MCP tools (execute_command_background, list_background_processes, get_process_status, kill_background_process, restart_background_process, get_process_output).
- `tests/unit/test_process_handlers.py` - Comprehensive unit tests for process handlers functionality (18 tests covering all MCP tools, error handling, and concurrent operations).
- `src/terminal_mcp_server/handlers/python_handlers.py` - Python script execution and virtual environment handlers.
- `src/terminal_mcp_server/handlers/environment_handlers.py` - Environment and directory management handlers.
- `src/terminal_mcp_server/models/terminal_models.py` - Data models for commands, processes, and execution results with Pydantic validation.
- `src/terminal_mcp_server/utils/command_executor.py` - Core command execution utilities with streaming support (placeholder).
- `src/terminal_mcp_server/utils/process_manager.py` - Complete background process tracking and management implementation with async process control, lifecycle management, output capture, and resource cleanup.
- `tests/unit/test_process_manager.py` - Comprehensive unit tests for process manager functionality (15 tests covering process lifecycle, status tracking, killing, restarting, and output capture).
- `src/terminal_mcp_server/utils/output_streamer.py` - Enhanced real-time output streaming implementation with configurable buffer sizes, dynamic adjustment, and validation.
- `src/terminal_mcp_server/utils/venv_manager.py` - Complete virtual environment detection and management implementation with system Python detection, common venv locations scanning, real venv creation, and package installation support.
- `tests/unit/test_directory_structure.py` - Comprehensive tests for validating the terminal server directory structure.
- `tests/unit/test_terminal_models.py` - Tests for the new terminal-specific data models.
- `config/config.yaml` - Comprehensive terminal server configuration with execution, security, and streaming settings.
- `tests/unit/test_terminal_config.py` - Comprehensive tests for terminal server configuration validation.
- `tests/unit/test_scaffolding_cleanup.py` - Tests verifying all example/scaffolding files have been removed.
- `README.md` - Updated to remove scaffolding references and reflect terminal server focus.
- `src/terminal_mcp_server/utils/command_executor.py` - Complete async command execution implementation with timeout, environment support, and output capture.
- `tests/unit/test_command_executor.py` - Comprehensive tests for command executor functionality (15 tests covering all execution scenarios).
- `tests/unit/test_command_handlers.py` - Comprehensive unit tests for command execution handlers with MCP tool registration (17 tests covering basic execution, parameter handling, error scenarios, and MCP tool functionality).
- `src/terminal_mcp_server/handlers/command_handlers.py` - Enhanced command handlers with MCP tool registration method and JSON response formatting for the execute_command tool.
- `src/terminal_mcp_server/server.py` - Updated server implementation to use command_handlers.register_tools() instead of placeholder execute_command implementation.
- `tests/unit/test_scaffolding_cleanup.py` - Updated to include new test_command_handlers.py in expected test files list.
- `tests/unit/test_process_handlers.py` - Unit tests for process management handlers.
- `tests/unit/test_python_handlers.py` - Unit tests for Python execution handlers.
- `tests/unit/test_environment_handlers.py` - Unit tests for environment management handlers.
- `tests/unit/test_command_executor.py` - Unit tests for command execution utilities.
- `tests/unit/test_process_manager.py` - Unit tests for process management utilities.
- `tests/unit/test_output_streamer.py` - Unit tests for output streaming functionality with enhanced buffer configuration tests.
- `tests/unit/test_venv_manager.py` - Unit tests for virtual environment management.
- `tests/integration/test_terminal_integration.py` - Integration tests for complete terminal operations.
- `src/terminal_mcp_server/utils/command_executor.py` - Enhanced with streaming output capture that stores chunks as they pass through for inclusion in final responses.
- `src/terminal_mcp_server/handlers/python_handlers.py` - Updated streaming methods to include captured chunks in final MCP tool responses instead of returning empty streamed_output arrays.
- `tests/unit/test_python_handlers.py` - Added comprehensive tests for streaming output capture functionality to verify that real-time chunks are properly collected and included in responses.
- `src/terminal_mcp_server/handlers/environment_handlers.py` - Complete environment and directory management handlers with 4 MCP tools (get_current_directory, change_directory, get_environment_variables, set_environment_variable).
- `tests/unit/test_environment_handlers.py` - Comprehensive unit tests for environment handlers functionality (18 tests covering directory operations, environment variables, error handling, and MCP tool registration).
- `src/terminal_mcp_server/server.py` - Updated to register environment handlers tools for directory and environment variable management.
- `tests/unit/test_scaffolding_cleanup.py` - Updated to include test_environment_handlers.py in expected test files list.

### Notes

- Unit tests should be placed in the `tests/unit/` directory following the existing project structure.
- Use `python -m pytest tests/unit/ -n auto -q --tb=line` to run the unit test suite.
- Integration tests should be in `tests/integration/` for testing complete workflows.
- All handlers should follow async/await patterns for non-blocking execution.

## Tasks

- [x] 1.0 Setup Project Infrastructure and Dependencies
  - [x] 1.1 Update requirements.txt with new dependencies (psutil, asyncio subprocess utilities)
  - [x] 1.2 Rename mcp_scaffolding module to terminal_mcp_server throughout the project
  - [x] 1.3 Update pyproject.toml configuration and scripts entry point
  - [x] 1.4 Create new directory structure for terminal-specific handlers and utilities
  - [x] 1.5 Update configuration files to support terminal server settings
  - [x] 1.6 Remove example handlers and models from the scaffolding

- [x] 2.0 Implement Core Command Execution System
  - [x] 2.1 Create terminal_models.py with CommandRequest, CommandResult, and ProcessInfo models
  - [x] 2.2 Implement command_executor.py with async command execution and output streaming
  - [x] 2.3 Create command_handlers.py with execute_command MCP tool
  - [x] 2.4 Implement real-time output streaming with configurable buffer sizes
  - [x] 2.5 Add command timeout and interruption support (Ctrl+C equivalent)
  - [x] 2.6 Implement exit code capture and error handling
  - [x] 2.7 Add support for custom environment variables in command execution
  - [x] 2.8 Create comprehensive logging for all command executions

- [x] 3.0 Implement Background Process Management
  - [x] 3.1 Create process_manager.py with background process tracking and lifecycle management
  - [x] 3.2 Implement process_handlers.py with background process MCP tools
  - [x] 3.3 Add execute_command_background tool with process ID return
  - [x] 3.4 Implement list_background_processes tool with status monitoring
  - [x] 3.5 Add kill_background_process and restart_background_process tools
  - [x] 3.6 Implement get_process_status and get_command_output tools
  - [x] 3.7 Add automatic process cleanup and resource management
  - [x] 3.8 Implement process output capture and retrieval for background processes
  - [x] 3.9 Register process handlers tools in server.py

- [x] 4.0 Implement Python Script Execution and Virtual Environment Support
  - [x] 4.1 Create python_handlers.py with Python execution MCP tools
  - [x] 4.2 Implement execute_python_script tool with output streaming
  - [x] 4.3 Register python handlers tools in server.py
  - [x] 4.4 Add execute_python_code tool for direct code execution
  - [x] 4.5 Create venv_manager.py for virtual environment detection and management
  - [x] 4.6 Implement list_virtual_environments and activate_virtual_environment tools
  - [x] 4.7 Add create_virtual_environment tool with dependency management
  - [x] 4.8 Implement install_python_package tool with environment support
  - [x] 4.9 Add install_dependencies tool for requirements.txt handling
  - [x] 4.10 Support passing command-line arguments to Python scripts

- [ ] 5.0 Implement Environment Management and Enhanced Error Handling
  - [x] 5.1 Create output_streamer.py with async output streaming implementation (completed in previous tasks)
  - [ ] 5.2 Implement real-time stdout and stderr streaming with separation (enhance current combined streaming)
  - [x] 5.3 Add configurable output buffer sizes and memory limits (completed in previous tasks)
  - [ ] 5.4 Implement output size limits to prevent memory exhaustion (add memory safeguards)
  - [ ] 5.5 Add comprehensive error handling for all command execution scenarios
  - [x] 5.6 Create environment_handlers.py for directory and environment management
  - [x] 5.7 Implement change_directory and get_current_directory tools
  - [x] 5.8 Add set_environment_variable and get_environment_variables tools
  - [x] 5.9 Register environment handlers tools in server.py
  - [ ] 5.10 Implement graceful error recovery and reporting mechanisms

- [ ] 7.0 Fix Identified Issues and Polish Implementation
  - [x] 7.1 Fix virtual environment listing bug - VirtualEnvironmentInfo object not subscriptable error in list_virtual_environments tool
  - [x] 7.2 Investigate missing execute_python_script_with_streaming tool in MCP client (registered but not accessible)
  - [x] 7.3 Improve streaming output collection to capture real-time chunks in final response (currently returns empty streamed_output array)
  - [ ] 7.4 Enhance install_python_package to provide detailed pip installation output instead of simplified success message
  - [ ] 7.5 Add comprehensive error handling tests for virtual environment operations to prevent object access bugs
  - [ ] 7.6 Verify all 17 tools are accessible through different MCP clients and resolve any client-specific issues
  - [ ] 7.7 Add integration tests for Python package installation and usage workflows to ensure end-to-end functionality