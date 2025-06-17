# Terminal MCP Server

A comprehensive Model Context Protocol (MCP) server that provides full terminal and system access capabilities to AI agents. This server enables AI Coding Agents to execute any command-line operations, manage processes, execute Python scripts, and perform system-level tasks through a secure and robust MCP interface.

## 🎯 Project Vision

**Transform AI agents into autonomous developers** by providing complete terminal access equivalent to what a human developer would have. This server bridges the gap between AI reasoning and system-level operations, enabling:

- **Autonomous Development**: AI agents can compile, test, debug, and deploy code
- **System Administration**: Full access to Linux command-line operations
- **Process Management**: Background process lifecycle management
- **Python Integration**: Script execution with virtual environment support
- **Real-time Feedback**: Streaming command outputs for immediate decision making

## 🚀 Planned Features

### Core Capabilities
- **18 MCP Tools** for comprehensive terminal operations
- **Real-time Output Streaming** with <50ms latency
- **Background Process Management** with monitoring and control
- **Python Script Execution** with dependency management
- **Virtual Environment Support** for project isolation
- **Full System Access** for development and debugging

### MCP Tools (In Development)

#### Command Execution
- `execute_command` - Execute shell commands with real-time output
- `execute_command_background` - Start commands in the background
- `get_command_output` - Retrieve output from background commands

#### Process Management  
- `list_background_processes` - List all active background processes
- `kill_background_process` - Terminate background processes
- `get_process_status` - Get detailed process status
- `restart_background_process` - Restart failed processes

#### Python Integration
- `execute_python_script` - Run Python scripts with output streaming
- `execute_python_code` - Execute Python code directly
- `install_python_package` - Manage Python dependencies

#### Environment Management
- `change_directory` - Change working directory
- `get_current_directory` - Get current directory
- `set_environment_variable` - Set environment variables
- `get_environment_variables` - Get environment variables

#### Virtual Environment Tools
- `list_virtual_environments` - Discover available virtual environments
- `activate_virtual_environment` - Switch virtual environments
- `create_virtual_environment` - Create new virtual environments
- `install_dependencies` - Install requirements.txt dependencies

## 📋 Implementation Status

This project is currently in development. See our [Implementation Task List](tasks/tasks-prd-terminal-mcp-server.md) for detailed progress.

### Phase 1: Core Functionality ⏳
- [ ] Basic command execution with output streaming
- [ ] Error handling and exit code reporting  
- [ ] Background process management

### Phase 2: Python Integration ⏳
- [ ] Python script execution
- [ ] Virtual environment support
- [ ] Dependency management

### Phase 3: Advanced Features ⏳
- [ ] Process monitoring and restart capabilities
- [ ] Advanced output handling and filtering
- [ ] Performance optimizations

## 🎯 Target Use Case

**Primary User**: AI Coding Agent at `/home/randy/workspace/personal/my_coding_agent`

**Capabilities Enabled**:
- Autonomous code compilation and testing
- Real-time debugging with immediate feedback
- File system operations and project management
- Package installation and dependency management
- System monitoring and process control
- Integration testing and deployment tasks

## 🛠️ Current Development Setup

This project provides a comprehensive Terminal MCP Server implementation.

### Quick Start (Development)

```bash
# Clone the repository
git clone <repository-url> terminal_mcp_server
cd terminal_mcp_server

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run Current Server (Scaffolding Version)

```bash
# Run the server (currently example tools only)
python -m terminal_mcp_server.server

# Run tests
pytest
```

## 📚 Documentation

- **[Product Requirements Document](tasks/prd-terminal-mcp-server.md)** - Complete feature specifications
- **[Implementation Task List](tasks/tasks-prd-terminal-mcp-server.md)** - Detailed development roadmap
- **[Current Examples](#available-example-tools)** - Test tools from development version

## 🔧 Architecture Overview

### Design Principles
- **Async-First**: All operations use async/await for non-blocking execution
- **Real-time Streaming**: Command outputs stream in real-time using async generators  
- **Process Safety**: Comprehensive process lifecycle management with cleanup
- **Resource Limits**: Configurable limits for memory usage and process counts
- **Comprehensive Logging**: Full audit trail of all operations

### Technical Stack
- **FastMCP**: MCP protocol implementation
- **psutil**: Advanced process monitoring
- **asyncio**: Asynchronous process execution
- **Pydantic**: Data validation and modeling
- **pytest**: Testing framework with >90% coverage target

## 🎮 Available Example Tools (Current Development)

The current development version includes example tools for testing MCP connectivity:

### 1. `test_connection`
**Purpose**: Test the MCP server connection
**Example**: "Test the connection to the MCP scaffolding server"

### 2. `create_example_tool`  
**Purpose**: Create a new example tool (demonstrates data creation)
**Example**: "Create an example tool called 'my-first-tool'"

### 3. `get_example_data`
**Purpose**: Retrieve example data from the server
**Example**: "Get some example data from the scaffolding server"

> **Note**: These example tools will be replaced with terminal functionality as development progresses.

## 🚧 Development Workflow

### Code Quality Standards
- **Black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning
- **pytest**: >90% test coverage

### Testing Strategy
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

### Task Management
- Follow the [Task List](tasks/tasks-prd-terminal-mcp-server.md) for implementation order
- Use Test-Driven Development (TDD) approach
- One sub-task at a time with user approval
- Mark tasks complete only after tests pass

## 🎯 Success Metrics

- **Functionality**: 100% of PRD requirements implemented
- **Performance**: <100ms command execution latency
- **Reliability**: >99% successful command execution rate
- **Integration**: Seamless AI Coding Agent integration
- **Testing**: >90% code coverage with comprehensive edge cases

## 🤝 Contributing

This project follows a structured development approach:

1. **Review the PRD**: Understand requirements in [prd-terminal-mcp-server.md](tasks/prd-terminal-mcp-server.md)
2. **Follow Task List**: Work through [tasks-prd-terminal-mcp-server.md](tasks/tasks-prd-terminal-mcp-server.md)
3. **Test-Driven Development**: Write tests first, then implement
4. **One Task at a Time**: Complete tasks sequentially with approval

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**🚀 Coming Soon**: Full terminal access for AI agents with real-time command execution, background process management, and comprehensive Python integration!
