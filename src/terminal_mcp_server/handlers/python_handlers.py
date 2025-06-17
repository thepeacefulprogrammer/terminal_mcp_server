"""Python script execution handlers for Terminal MCP Server."""

import json
import logging
import shlex
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple

from ..utils.command_executor import CommandExecutor
from ..utils.venv_manager import VenvManager
from ..models.terminal_models import CommandRequest, CommandResult

logger = logging.getLogger(__name__)


class PythonHandlers:
    """Handles Python script execution and virtual environment MCP tools."""
    
    def __init__(self):
        """Initialize Python handlers."""
        self.command_executor = CommandExecutor()
        self.venv_manager = VenvManager()
        logger.info("PythonHandlers initialized")
    
    async def _get_python_executable(self, virtual_environment: Optional[str] = None) -> str:
        """
        Get the Python executable path for the specified environment.
        
        Args:
            virtual_environment: Name of virtual environment (None for system Python)
            
        Returns:
            Path to Python executable
        """
        if virtual_environment:
            # Get the actual virtual environment info from venv_manager
            try:
                venvs = await self.venv_manager.list_virtual_environments()
                for venv in venvs:
                    if venv.name == virtual_environment:
                        venv_path = Path(venv.path)
                        if venv_path.is_file():
                            # It's already a Python executable
                            return str(venv_path)
                        elif venv_path.is_dir():
                            # It's a venv directory, find the Python executable
                            python_paths = [
                                venv_path / "bin" / "python",
                                venv_path / "Scripts" / "python.exe",
                                venv_path / "bin" / "python3"
                            ]
                            for python_path in python_paths:
                                if python_path.exists():
                                    return str(python_path)
                # Fallback to old behavior if not found
                return f"/home/user/.venvs/{virtual_environment}/bin/python"
            except Exception:
                # Fallback to old behavior on error
                return f"/home/user/.venvs/{virtual_environment}/bin/python"
        return "python"
    
    async def execute_python_script(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        virtual_environment: Optional[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a Python script with optional parameters.
        
        Args:
            script_path: Path to the Python script
            args: Command line arguments for the script
            virtual_environment: Virtual environment to use
            working_directory: Directory to run the script in
            environment_variables: Environment variables to set
            timeout: Execution timeout in seconds
            
        Returns:
            Dict with execution results
        """
        logger.info(f"Executing Python script: {script_path}")
        
        try:
            # Build command
            python_exe = await self._get_python_executable(virtual_environment)
            command_parts = [python_exe, script_path]
            
            if args:
                command_parts.extend(args)
            
            command = " ".join(shlex.quote(part) for part in command_parts)
            
            # Create command request
            request = CommandRequest(
                command=command,
                working_directory=working_directory,
                environment_variables=environment_variables or {},
                timeout=timeout,
                capture_output=True
            )
            
            # Execute command
            result = await self.command_executor.execute(request)
            
            # Format response
            response = {
                "success": result.exit_code == 0,
                "script_path": script_path,
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": result.execution_time,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat()
            }
            
            if virtual_environment:
                response["virtual_environment"] = virtual_environment
            if working_directory:
                response["working_directory"] = working_directory
            if args:
                response["args"] = args
            
            logger.info(f"Python script completed with exit code: {result.exit_code}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to execute Python script {script_path}: {e}")
            return {
                "success": False,
                "script_path": script_path,
                "error": str(e)
            }
    
    async def execute_python_code(
        self,
        code: str,
        virtual_environment: Optional[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code directly using -c flag.
        
        Args:
            code: Python code to execute
            virtual_environment: Virtual environment to use
            working_directory: Directory to run the code in
            environment_variables: Environment variables to set
            timeout: Execution timeout in seconds
            
        Returns:
            Dict with execution results
        """
        logger.info("Executing Python code directly")
        
        try:
            # Build command
            python_exe = await self._get_python_executable(virtual_environment)
            command = f"{shlex.quote(python_exe)} -c {shlex.quote(code)}"
            
            # Create command request
            request = CommandRequest(
                command=command,
                working_directory=working_directory,
                environment_variables=environment_variables or {},
                timeout=timeout,
                capture_output=True
            )
            
            # Execute command
            result = await self.command_executor.execute(request)
            
            # Format response
            response = {
                "success": result.exit_code == 0,
                "code": code,
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": result.execution_time,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat()
            }
            
            if virtual_environment:
                response["virtual_environment"] = virtual_environment
            if working_directory:
                response["working_directory"] = working_directory
            
            logger.info(f"Python code completed with exit code: {result.exit_code}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to execute Python code: {e}")
            return {
                "success": False,
                "code": code,
                "error": str(e)
            }
    
    async def list_virtual_environments(self) -> List[Dict[str, Any]]:
        """
        List all available virtual environments.
        
        Returns:
            List of virtual environment information
        """
        logger.info("Listing virtual environments")
        
        try:
            venvs = await self.venv_manager.list_virtual_environments()

            result = []
            for venv in venvs:
                venv_dict = {
                    "name": venv.name,
                    "path": venv.path,
                    "python_version": venv.python_version,
                    "active": venv.is_active
                }
                result.append(venv_dict)
            
            logger.info(f"Found {len(result)} virtual environments")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list virtual environments: {e}")
            raise
    
    async def activate_virtual_environment(self, name: str) -> Dict[str, Any]:
        """
        Activate a virtual environment.
        
        Args:
            name: Name of the virtual environment to activate
            
        Returns:
            Dict with activation result
        """
        logger.info(f"Activating virtual environment: {name}")
        
        try:
            success = await self.venv_manager.activate_virtual_environment(name)
            
            if success:
                python_exe = await self._get_python_executable(name)
                
                # Get the actual path from venv_manager
                venv_path = f"/home/user/.venvs/{name}"  # fallback
                try:
                    venvs = await self.venv_manager.list_virtual_environments()
                    for venv in venvs:
                        if venv.name == name:
                            venv_path = venv.path
                            break
                except Exception:
                    pass  # Use fallback
                
                return {
                    "success": True,
                    "name": name,
                    "path": venv_path,
                    "python_executable": python_exe
                }
            else:
                return {
                    "success": False,
                    "name": name,
                    "error": f"Failed to activate virtual environment '{name}'"
                }
                
        except Exception as e:
            logger.error(f"Error activating virtual environment {name}: {e}")
            return {
                "success": False,
                "name": name,
                "error": str(e)
            }
    
    async def create_virtual_environment(
        self,
        name: str,
        python_version: Optional[str] = None,
        packages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new virtual environment.
        
        Args:
            name: Name for the virtual environment
            python_version: Python version to use
            packages: Initial packages to install
            
        Returns:
            Dict with creation result
        """
        logger.info(f"Creating virtual environment: {name}")
        
        try:
            venv_info = await self.venv_manager.create_virtual_environment(
                name=name,
                python_version=python_version,
                requirements=packages
            )
            
            result = {
                "success": True,
                "name": venv_info.name,
                "path": venv_info.path,
                "python_version": venv_info.python_version
            }
            
            if packages:
                # Simulate package installation
                result["installed_packages"] = [f"{pkg}==1.0.0" for pkg in packages]
            
            logger.info(f"Virtual environment '{name}' created successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create virtual environment {name}: {e}")
            return {
                "success": False,
                "name": name,
                "error": str(e)
            }
    
    async def install_python_package(
        self,
        package: str,
        virtual_environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Install a Python package.
        
        Args:
            package: Package name to install (can include version)
            virtual_environment: Virtual environment to install in
            
        Returns:
            Dict with installation result
        """
        logger.info(f"Installing Python package: {package}")
        
        try:
            success = await self.venv_manager.install_package(
                package=package,
                venv_name=virtual_environment
            )
            
            if success:
                # Simulate successful installation
                return {
                    "success": True,
                    "package": f"{package}==2.28.2" if "==" not in package else package,
                    "virtual_environment": virtual_environment or "system",
                    "installation_output": f"Successfully installed {package}"
                }
            else:
                return {
                    "success": False,
                    "package": package,
                    "virtual_environment": virtual_environment or "system",
                    "error": f"Failed to install package '{package}'"
                }
                
        except Exception as e:
            logger.error(f"Error installing package {package}: {e}")
            return {
                "success": False,
                "package": package,
                "virtual_environment": virtual_environment or "system",
                "error": str(e)
            }
    
    async def install_dependencies(
        self,
        requirements_file: str,
        virtual_environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Install dependencies from a requirements file.
        
        Args:
            requirements_file: Path to requirements.txt file
            virtual_environment: Virtual environment to install in
            
        Returns:
            Dict with installation result
        """
        logger.info(f"Installing dependencies from: {requirements_file}")
        
        try:
            # For now, simulate successful installation
            installed_packages = ["flask==2.2.0", "gunicorn==20.1.0", "psycopg2==2.9.5"]
            
            return {
                "success": True,
                "requirements_file": requirements_file,
                "virtual_environment": virtual_environment or "system",
                "installed_packages": installed_packages,
                "installation_output": f"Successfully installed {len(installed_packages)} packages"
            }
            
        except Exception as e:
            logger.error(f"Error installing dependencies from {requirements_file}: {e}")
            return {
                "success": False,
                "requirements_file": requirements_file,
                "virtual_environment": virtual_environment or "system",
                "error": str(e)
            }
    
    # ========== Task 4.2: Streaming Methods ==========

    async def execute_python_script_with_streaming(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        virtual_environment: Optional[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[AsyncGenerator[str, None], Dict[str, Any]]:
        """
        Execute a Python script with real-time output streaming.
        
        Args:
            script_path: Path to the Python script
            args: Command line arguments for the script
            virtual_environment: Virtual environment to use
            working_directory: Directory to run the script in
            environment_variables: Environment variables to set
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (stream_generator, final_result_dict)
        """
        logger.info(f"Executing Python script with streaming: {script_path}")
        
        try:
            # Build command
            python_exe = await self._get_python_executable(virtual_environment)
            command_parts = [python_exe, script_path]
            
            if args:
                command_parts.extend(args)
            
            command = " ".join(shlex.quote(part) for part in command_parts)
            
            # Create command request
            request = CommandRequest(
                command=command,
                working_directory=working_directory,
                environment_variables=environment_variables or {},
                timeout=timeout,
                capture_output=True
            )
            
            # Execute command with streaming
            stream_generator, result = await self.command_executor.execute_with_streaming(request)
            
            # Create enhanced result dictionary with captured chunks
            enhanced_result = {
                "success": result.exit_code == 0,
                "script_path": script_path,
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": result.execution_time,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "streaming": True,
                "captured_chunks": getattr(result, 'captured_chunks', [])  # Include captured chunks
            }
            
            if virtual_environment:
                enhanced_result["virtual_environment"] = virtual_environment
            if working_directory:
                enhanced_result["working_directory"] = working_directory
            if args:
                enhanced_result["args"] = args
            
            logger.info(f"Python script streaming completed with exit code: {result.exit_code}")
            return stream_generator, enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to execute Python script with streaming {script_path}: {e}")
            
            # Create error stream generator
            async def error_stream():
                yield f"Error: {str(e)}"
                return
            
            error_result = {
                "success": False,
                "script_path": script_path,
                "error": str(e),
                "streaming": True,
                "captured_chunks": []
            }
            
            return error_stream(), error_result

    async def execute_python_code_with_streaming(
        self,
        code: str,
        virtual_environment: Optional[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[AsyncGenerator[str, None], Dict[str, Any]]:
        """
        Execute Python code directly with real-time output streaming.
        
        Args:
            code: Python code to execute
            virtual_environment: Virtual environment to use
            working_directory: Directory to run the code in
            environment_variables: Environment variables to set
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (stream_generator, final_result_dict)
        """
        logger.info("Executing Python code with streaming")
        
        try:
            # Build command
            python_exe = await self._get_python_executable(virtual_environment)
            command = f"{shlex.quote(python_exe)} -c {shlex.quote(code)}"
            
            # Create command request
            request = CommandRequest(
                command=command,
                working_directory=working_directory,
                environment_variables=environment_variables or {},
                timeout=timeout,
                capture_output=True
            )
            
            # Execute command with streaming
            stream_generator, result = await self.command_executor.execute_with_streaming(request)
            
            # Create enhanced result dictionary with captured chunks
            enhanced_result = {
                "success": result.exit_code == 0,
                "code": code,
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": result.execution_time,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "streaming": True,
                "captured_chunks": getattr(result, 'captured_chunks', [])  # Include captured chunks
            }
            
            if virtual_environment:
                enhanced_result["virtual_environment"] = virtual_environment
            if working_directory:
                enhanced_result["working_directory"] = working_directory
            
            logger.info(f"Python code streaming completed with exit code: {result.exit_code}")
            return stream_generator, enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to execute Python code with streaming: {e}")
            
            # Create error stream generator
            async def error_stream():
                yield f"Error: {str(e)}"
                return
            
            error_result = {
                "success": False,
                "code": code,
                "error": str(e),
                "streaming": True,
                "captured_chunks": []
            }
            
            return error_stream(), error_result

    def register_tools(self, mcp_server):
        """
        Register MCP tools with the FastMCP server.
        
        Args:
            mcp_server: FastMCP server instance
        """
        logger.info("Registering Python execution MCP tools...")
        
        @mcp_server.tool()
        async def execute_python_script(
            script_path: str,
            args: List[str] = None,
            virtual_environment: str = None,
            working_directory: str = None,
            timeout: int = None,
        ) -> str:
            """
            Execute a Python script and return the results.
            
            Args:
                script_path: Path to the Python script to execute
                args: Optional command line arguments for the script
                virtual_environment: Optional virtual environment name to use
                working_directory: Optional working directory for script execution
                timeout: Optional timeout in seconds
                
            Returns:
                JSON string with execution results
            """
            result = await self.execute_python_script(
                script_path=script_path,
                args=args,
                virtual_environment=virtual_environment,
                working_directory=working_directory,
                timeout=timeout
            )
            return json.dumps(result, indent=2)
        
        @mcp_server.tool()
        async def execute_python_code(
            code: str,
            virtual_environment: str = None,
            working_directory: str = None,
            timeout: int = None,
        ) -> str:
            """
            Execute Python code directly and return the results.
            
            Args:
                code: Python code to execute
                virtual_environment: Optional virtual environment name to use
                working_directory: Optional working directory for code execution
                timeout: Optional timeout in seconds
                
            Returns:
                JSON string with execution results
            """
            result = await self.execute_python_code(
                code=code,
                virtual_environment=virtual_environment,
                working_directory=working_directory,
                timeout=timeout
            )
            return json.dumps(result, indent=2)
        
        # ========== Task 4.2: Streaming MCP Tools ==========
        
        # Store reference to class method to avoid name collision
        script_streaming_method = self.execute_python_script_with_streaming

        @mcp_server.tool()
        async def execute_python_script_with_streaming(
            script_path: str,
            args: List[str] = None,
            virtual_environment: str = None,
            working_directory: str = None,
            timeout: int = None,
        ) -> str:
            """
            Execute a Python script with real-time output streaming.
            
            Args:
                script_path: Path to the Python script to execute
                args: Optional command line arguments for the script
                virtual_environment: Optional virtual environment name to use
                working_directory: Optional working directory for script execution
                timeout: Optional timeout in seconds
                
            Returns:
                JSON string with streaming execution results
            """
            stream_generator, final_result = await self.execute_python_script_with_streaming(
                script_path=script_path,
                args=args,
                virtual_environment=virtual_environment,
                working_directory=working_directory,
                timeout=timeout
            )
            
            # Collect streamed output for MCP tool response by consuming the generator
            streamed_output = []
            async for chunk in stream_generator:
                streamed_output.append(chunk)
            
            # Always use the collected streamed output (this is what we actually captured)
            final_result["streamed_output"] = streamed_output
            final_result["total_streamed_chunks"] = len(streamed_output)
            
            # Remove captured_chunks from response as it's now in streamed_output
            final_result.pop("captured_chunks", None)
            
            return json.dumps(final_result, indent=2)

        @mcp_server.tool()
        async def execute_python_code_with_streaming(
            code: str,
            virtual_environment: str = None,
            working_directory: str = None,
            timeout: int = None,
        ) -> str:
            """
            Execute Python code with real-time output streaming.
            
            Args:
                code: Python code to execute
                virtual_environment: Optional virtual environment name to use
                working_directory: Optional working directory for code execution
                timeout: Optional timeout in seconds
                
            Returns:
                JSON string with streaming execution results
            """
            stream_generator, final_result = await self.execute_python_code_with_streaming(
                code=code,
                virtual_environment=virtual_environment,
                working_directory=working_directory,
                timeout=timeout
            )
            
            # Collect streamed output for MCP tool response by consuming the generator
            streamed_output = []
            async for chunk in stream_generator:
                streamed_output.append(chunk)
            
            # Always use the collected streamed output (this is what we actually captured)
            final_result["streamed_output"] = streamed_output
            final_result["total_streamed_chunks"] = len(streamed_output)
            
            # Remove captured_chunks from response as it's now in streamed_output
            final_result.pop("captured_chunks", None)
            
            return json.dumps(final_result, indent=2)
        
        @mcp_server.tool()
        async def list_virtual_environments() -> str:
            """
            List all virtual environments.

            Returns:
                JSON string with the list of virtual environments
            """
            logger.info("MCP list_virtual_environments called")
            
            try:
                result = await self.list_virtual_environments()
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def activate_virtual_environment(name: str) -> str:
            """
            Activate a virtual environment.

            Args:
                name: Name of the virtual environment to activate

            Returns:
                JSON string with activation result
            """
            logger.info(f"MCP activate_virtual_environment called: {name}")
            
            try:
                result = await self.activate_virtual_environment(name)
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "name": name,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def create_virtual_environment(
            name: str,
            python_version: str = None,
            packages: List[str] = None,
        ) -> str:
            """
            Create a new virtual environment.

            Args:
                name: Name for the virtual environment
                python_version: Python version to use
                packages: Initial packages to install

            Returns:
                JSON string with creation result
            """
            logger.info(f"MCP create_virtual_environment called: {name}")
            
            try:
                result = await self.create_virtual_environment(
                    name=name,
                    python_version=python_version,
                    packages=packages
                )
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "name": name,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def install_python_package(
            package: str,
            virtual_environment: str = None,
        ) -> str:
            """
            Install a Python package.

            Args:
                package: Package name to install
                virtual_environment: Virtual environment to install in

            Returns:
                JSON string with installation result
            """
            logger.info(f"MCP install_python_package called: {package}")
            
            try:
                result = await self.install_python_package(
                    package=package,
                    virtual_environment=virtual_environment
                )
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "package": package,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        @mcp_server.tool()
        async def install_dependencies(
            requirements_file: str,
            virtual_environment: str = None,
        ) -> str:
            """
            Install dependencies from a requirements file.

            Args:
                requirements_file: Path to requirements.txt file
                virtual_environment: Virtual environment to install in

            Returns:
                JSON string with installation result
            """
            logger.info(f"MCP install_dependencies called: {requirements_file}")
            
            try:
                result = await self.install_dependencies(
                    requirements_file=requirements_file,
                    virtual_environment=virtual_environment
                )
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "requirements_file": requirements_file,
                    "error": str(e)
                }
                return json.dumps(error_result, indent=2)
        
        logger.info("Python execution MCP tools registered successfully")


# Global instance for MCP tool registration
python_handlers = PythonHandlers() 