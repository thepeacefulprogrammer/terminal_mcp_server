# Task List: Terminal MCP Server Implementation

## Relevant Files

- `requirements.txt` - Update with new dependencies for terminal operations and process management.
- `src/terminal_mcp_server/__init__.py` - Main module initialization (rename from mcp_scaffolding).
- `src/terminal_mcp_server/server.py` - Main MCP server implementation with terminal-specific tools.
- `src/terminal_mcp_server/handlers/command_handlers.py` - Core command execution handlers.
- `src/terminal_mcp_server/handlers/process_handlers.py` - Background process management handlers.
- `src/terminal_mcp_server/handlers/python_handlers.py` - Python script execution and virtual environment handlers.
- `src/terminal_mcp_server/handlers/environment_handlers.py` - Environment and directory management handlers.
- `src/terminal_mcp_server/models/terminal_models.py` - Data models for commands, processes, and execution results.
- `src/terminal_mcp_server/utils/command_executor.py` - Core command execution utilities with streaming support.
- `src/terminal_mcp_server/utils/process_manager.py` - Background process tracking and management utilities.
- `src/terminal_mcp_server/utils/output_streamer.py` - Real-time output streaming implementation.
- `src/terminal_mcp_server/utils/venv_manager.py` - Virtual environment detection and management utilities.
- `tests/unit/test_command_handlers.py` - Unit tests for command execution handlers.
- `tests/unit/test_process_handlers.py` - Unit tests for process management handlers.
- `tests/unit/test_python_handlers.py` - Unit tests for Python execution handlers.
- `tests/unit/test_environment_handlers.py` - Unit tests for environment management handlers.
- `tests/unit/test_command_executor.py` - Unit tests for command execution utilities.
- `tests/unit/test_process_manager.py` - Unit tests for process management utilities.
- `tests/unit/test_output_streamer.py` - Unit tests for output streaming functionality.
- `tests/unit/test_venv_manager.py` - Unit tests for virtual environment management.
- `tests/integration/test_terminal_integration.py` - Integration tests for complete terminal operations.

### Notes

- Unit tests should be placed in the `tests/unit/` directory following the existing project structure.
- Use `python -m pytest tests/unit/ -n auto -q --tb=line` to run the unit test suite.
- Integration tests should be in `tests/integration/` for testing complete workflows.
- All handlers should follow async/await patterns for non-blocking execution.

## Tasks

- [ ] 1.0 Setup Project Infrastructure and Dependencies
  - [ ] 1.1 Update requirements.txt with new dependencies (psutil, asyncio subprocess utilities)
  - [ ] 1.2 Rename mcp_scaffolding module to terminal_mcp_server throughout the project
  - [ ] 1.3 Update pyproject.toml configuration and scripts entry point
  - [ ] 1.4 Create new directory structure for terminal-specific handlers and utilities
  - [ ] 1.5 Update configuration files to support terminal server settings
  - [ ] 1.6 Remove example handlers and models from the scaffolding

- [ ] 2.0 Implement Core Command Execution System
  - [ ] 2.1 Create terminal_models.py with CommandRequest, CommandResult, and ProcessInfo models
  - [ ] 2.2 Implement command_executor.py with async command execution and output streaming
  - [ ] 2.3 Create command_handlers.py with execute_command MCP tool
  - [ ] 2.4 Implement real-time output streaming with configurable buffer sizes
  - [ ] 2.5 Add command timeout and interruption support (Ctrl+C equivalent)
  - [ ] 2.6 Implement exit code capture and error handling
  - [ ] 2.7 Add support for custom environment variables in command execution
  - [ ] 2.8 Create comprehensive logging for all command executions

- [ ] 3.0 Implement Background Process Management
  - [ ] 3.1 Create process_manager.py with background process tracking and lifecycle management
  - [ ] 3.2 Implement process_handlers.py with background process MCP tools
  - [ ] 3.3 Add execute_command_background tool with process ID return
  - [ ] 3.4 Implement list_background_processes tool with status monitoring
  - [ ] 3.5 Add kill_background_process and restart_background_process tools
  - [ ] 3.6 Implement get_process_status and get_command_output tools
  - [ ] 3.7 Add automatic process cleanup and resource management
  - [ ] 3.8 Implement process output capture and retrieval for background processes

- [ ] 4.0 Implement Python Script Execution and Virtual Environment Support
  - [ ] 4.1 Create python_handlers.py with Python execution MCP tools
  - [ ] 4.2 Implement execute_python_script tool with output streaming
  - [ ] 4.3 Add execute_python_code tool for direct code execution
  - [ ] 4.4 Create venv_manager.py for virtual environment detection and management
  - [ ] 4.5 Implement list_virtual_environments and activate_virtual_environment tools
  - [ ] 4.6 Add create_virtual_environment tool with dependency management
  - [ ] 4.7 Implement install_python_package tool with environment support
  - [ ] 4.8 Add install_dependencies tool for requirements.txt handling
  - [ ] 4.9 Support passing command-line arguments to Python scripts

- [ ] 5.0 Implement Output Streaming and Error Handling
  - [ ] 5.1 Create output_streamer.py with async output streaming implementation
  - [ ] 5.2 Implement real-time stdout and stderr streaming with separation
  - [ ] 5.3 Add configurable output buffer sizes and memory limits
  - [ ] 5.4 Implement output size limits to prevent memory exhaustion
  - [ ] 5.5 Add comprehensive error handling for all command execution scenarios
  - [ ] 5.6 Create environment_handlers.py for directory and environment management
  - [ ] 5.7 Implement change_directory and get_current_directory tools
  - [ ] 5.8 Add set_environment_variable and get_environment_variables tools
  - [ ] 5.9 Implement graceful error recovery and reporting mechanisms

- [ ] 6.0 Add Comprehensive Testing and Documentation
  - [ ] 6.1 Create unit tests for all handler modules with >90% coverage
  - [ ] 6.2 Implement unit tests for all utility modules (command_executor, process_manager, etc.)
  - [ ] 6.3 Create integration tests for complete terminal operation workflows
  - [ ] 6.4 Add performance tests for output streaming and process management
  - [ ] 6.5 Update server.py to register all new MCP tools and remove example tools
  - [ ] 6.6 Create comprehensive error handling tests for edge cases
  - [ ] 6.7 Add tests for virtual environment operations and Python execution
  - [ ] 6.8 Update README.md with terminal server usage examples and API documentation