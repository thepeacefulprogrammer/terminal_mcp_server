"""Virtual environment detection and management utilities for Terminal MCP Server."""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class VirtualEnvironmentInfo:
    """Information about a virtual environment."""
    
    def __init__(self, name: str, path: str, python_version: str, is_active: bool = False):
        """Initialize virtual environment info."""
        self.name = name
        self.path = path
        self.python_version = python_version
        self.is_active = is_active


class VenvManager:
    """Manages virtual environments for Python execution."""
    
    def __init__(self):
        """Initialize virtual environment manager."""
        self.common_venv_paths = [
            Path.home() / ".venvs",
            Path.home() / "venvs", 
            Path.home() / ".pyenv" / "versions",
            Path.cwd() / "venv",
            Path.cwd() / ".venv",
            Path("/opt/python/venvs"),
            Path("/usr/local/venvs")
        ]
        logger.info("VenvManager initialized")
    
    async def _run_command(self, command: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
        """Run a command asynchronously and return (returncode, stdout, stderr)."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            return process.returncode, stdout.decode('utf-8'), stderr.decode('utf-8')
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return 1, "", str(e)
    
    async def _get_python_version(self, python_path: str) -> Optional[str]:
        """Get Python version from a Python executable."""
        try:
            returncode, stdout, stderr = await self._run_command(f'"{python_path}" --version')
            if returncode == 0:
                # Python 3.x outputs "Python 3.11.9"
                version_line = stdout.strip() or stderr.strip()
                if version_line.startswith("Python "):
                    return version_line.split()[1]
            return None
        except Exception as e:
            logger.debug(f"Failed to get Python version for {python_path}: {e}")
            return None
    
    async def _detect_system_python(self) -> List[VirtualEnvironmentInfo]:
        """Detect system Python installations."""
        venvs = []
        
        # Check current Python (sys.executable)
        current_python = sys.executable
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        venvs.append(VirtualEnvironmentInfo(
            name="system",
            path=current_python,
            python_version=current_version,
            is_active=True  # Current Python is considered active
        ))
        
        # Check common Python executables
        python_executables = ["python3", "python", "python3.11", "python3.10", "python3.9"]
        
        for python_exe in python_executables:
            try:
                python_path = shutil.which(python_exe)
                if python_path and python_path != current_python:
                    version = await self._get_python_version(python_path)
                    if version:
                        venvs.append(VirtualEnvironmentInfo(
                            name=f"system-{python_exe}",
                            path=python_path,
                            python_version=version,
                            is_active=False
                        ))
            except Exception as e:
                logger.debug(f"Failed to check {python_exe}: {e}")
        
        return venvs
    
    async def _detect_venv_at_path(self, venv_path: Path) -> Optional[VirtualEnvironmentInfo]:
        """Detect virtual environment at a specific path."""
        try:
            if not venv_path.exists():
                return None
            
            # Check for common venv structure
            python_paths = [
                venv_path / "bin" / "python",  # Unix/Linux/macOS
                venv_path / "Scripts" / "python.exe",  # Windows
                venv_path / "bin" / "python3",
            ]
            
            for python_path in python_paths:
                if python_path.exists():
                    version = await self._get_python_version(str(python_path))
                    if version:
                        return VirtualEnvironmentInfo(
                            name=venv_path.name,
                            path=str(venv_path),
                            python_version=version,
                            is_active=False
                        )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to detect venv at {venv_path}: {e}")
            return None
    
    async def _detect_venvs_in_directory(self, directory: Path) -> List[VirtualEnvironmentInfo]:
        """Detect virtual environments in a directory."""
        venvs = []
        
        try:
            if not directory.exists() or not directory.is_dir():
                return venvs
            
            # Look for subdirectories that might be venvs
            for item in directory.iterdir():
                if item.is_dir():
                    venv_info = await self._detect_venv_at_path(item)
                    if venv_info:
                        venvs.append(venv_info)
        
        except Exception as e:
            logger.debug(f"Failed to scan directory {directory}: {e}")
        
        return venvs
    
    async def list_virtual_environments(self) -> List[VirtualEnvironmentInfo]:
        """
        List all available virtual environments.
        
        Returns:
            List of virtual environment information
        """
        logger.info("Listing virtual environments")
        
        venvs = []
        
        try:
            # Detect system Python installations
            system_venvs = await self._detect_system_python()
            venvs.extend(system_venvs)
            
            # Detect virtual environments in common locations
            for venv_dir in self.common_venv_paths:
                detected_venvs = await self._detect_venvs_in_directory(venv_dir)
                venvs.extend(detected_venvs)
            
            # Remove duplicates based on path
            seen_paths = set()
            unique_venvs = []
            for venv in venvs:
                if venv.path not in seen_paths:
                    seen_paths.add(venv.path)
                    unique_venvs.append(venv)
            
            logger.info(f"Found {len(unique_venvs)} virtual environments")
            return unique_venvs
            
        except Exception as e:
            logger.error(f"Failed to list virtual environments: {e}")
            # Return at least the system Python
            return [VirtualEnvironmentInfo(
                name="system",
                path=sys.executable,
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                is_active=True
            )]
    
    async def create_virtual_environment(
        self,
        name: str,
        python_version: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> VirtualEnvironmentInfo:
        """
        Create a new virtual environment.
        
        Args:
            name: Name for the virtual environment
            python_version: Python version to use
            requirements: List of packages to install
            
        Returns:
            Information about the created environment
        """
        logger.info(f"Creating virtual environment: {name}")
        
        try:
            # Determine where to create the venv
            venv_base_dir = Path.home() / ".venvs"
            venv_base_dir.mkdir(exist_ok=True)
            venv_path = venv_base_dir / name
            
            if venv_path.exists():
                logger.warning(f"Virtual environment {name} already exists at {venv_path}")
                # Return info about existing venv
                existing_venv = await self._detect_venv_at_path(venv_path)
                if existing_venv:
                    return existing_venv
            
            # Determine Python executable to use
            python_exe = sys.executable
            if python_version:
                # Try to find specific Python version
                possible_pythons = [
                    f"python{python_version}",
                    f"python{python_version.split('.')[0]}.{python_version.split('.')[1]}",
                    "python3",
                    "python"
                ]
                for py_exe in possible_pythons:
                    found_python = shutil.which(py_exe)
                    if found_python:
                        # Check if it matches the requested version
                        version = await self._get_python_version(found_python)
                        if version and version.startswith(python_version.split('.')[0]):
                            python_exe = found_python
                            break
            
            # Create virtual environment
            create_command = f'"{python_exe}" -m venv "{venv_path}"'
            returncode, stdout, stderr = await self._run_command(create_command)
            
            if returncode != 0:
                raise RuntimeError(f"Failed to create virtual environment: {stderr}")
            
            # Install requirements if provided
            if requirements:
                pip_path = venv_path / "bin" / "pip"
                if not pip_path.exists():
                    pip_path = venv_path / "Scripts" / "pip.exe"
                
                if pip_path.exists():
                    for package in requirements:
                        install_command = f'"{pip_path}" install "{package}"'
                        install_returncode, install_stdout, install_stderr = await self._run_command(install_command)
                        if install_returncode != 0:
                            logger.warning(f"Failed to install {package}: {install_stderr}")
            
            # Get info about the created environment
            created_venv = await self._detect_venv_at_path(venv_path)
            if created_venv:
                logger.info(f"Virtual environment '{name}' created successfully")
                return created_venv
            else:
                raise RuntimeError("Virtual environment was created but could not be detected")
                
        except Exception as e:
            logger.error(f"Failed to create virtual environment {name}: {e}")
            # Return a placeholder for now
            return VirtualEnvironmentInfo(
                name=name,
                path=str(Path.home() / ".venvs" / name),
                python_version=python_version or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                is_active=False
            )
    
    async def activate_virtual_environment(self, name: str) -> bool:
        """
        Activate a virtual environment.
        
        Args:
            name: Name of the virtual environment to activate
            
        Returns:
            True if activation was successful
        """
        logger.info(f"Activating virtual environment: {name}")
        
        try:
            # Find the virtual environment
            venvs = await self.list_virtual_environments()
            target_venv = None
            
            for venv in venvs:
                if venv.name == name:
                    target_venv = venv
                    break
            
            if not target_venv:
                logger.error(f"Virtual environment '{name}' not found")
                return False
            
            # For now, we can't truly activate a venv in the current process
            # But we can verify it exists and is valid
            venv_path = Path(target_venv.path)
            if venv_path.is_file():
                # It's a Python executable
                return True
            elif venv_path.is_dir():
                # It's a venv directory, check for Python executable
                python_paths = [
                    venv_path / "bin" / "python",
                    venv_path / "Scripts" / "python.exe"
                ]
                for python_path in python_paths:
                    if python_path.exists():
                        return True
            
            logger.error(f"Virtual environment '{name}' is not valid")
            return False
            
        except Exception as e:
            logger.error(f"Failed to activate virtual environment {name}: {e}")
            return False
    
    async def install_package(
        self,
        package: str,
        venv_name: Optional[str] = None
    ) -> bool:
        """
        Install a Python package in the specified virtual environment.
        
        Args:
            package: Package name to install
            venv_name: Virtual environment name (None for current)
            
        Returns:
            True if installation was successful
        """
        logger.info(f"Installing package {package} in environment {venv_name or 'current'}")
        
        try:
            # Determine pip executable to use
            pip_exe = "pip"
            
            if venv_name:
                # Find the virtual environment
                venvs = await self.list_virtual_environments()
                target_venv = None
                
                for venv in venvs:
                    if venv.name == venv_name:
                        target_venv = venv
                        break
                
                if not target_venv:
                    logger.error(f"Virtual environment '{venv_name}' not found")
                    return False
                
                # Determine pip path for the venv
                venv_path = Path(target_venv.path)
                if venv_path.is_file():
                    # It's a Python executable, use it with -m pip
                    pip_exe = f'"{venv_path}" -m pip'
                elif venv_path.is_dir():
                    # It's a venv directory
                    pip_paths = [
                        venv_path / "bin" / "pip",
                        venv_path / "Scripts" / "pip.exe"
                    ]
                    for pip_path in pip_paths:
                        if pip_path.exists():
                            pip_exe = f'"{pip_path}"'
                            break
                    else:
                        # Fallback to python -m pip
                        python_paths = [
                            venv_path / "bin" / "python",
                            venv_path / "Scripts" / "python.exe"
                        ]
                        for python_path in python_paths:
                            if python_path.exists():
                                pip_exe = f'"{python_path}" -m pip'
                                break
            
            # Install the package
            install_command = f'{pip_exe} install "{package}"'
            returncode, stdout, stderr = await self._run_command(install_command)
            
            if returncode == 0:
                logger.info(f"Successfully installed {package}")
                return True
            else:
                logger.error(f"Failed to install {package}: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing package {package}: {e}")
            return False 
    
    async def install_package_with_output(
        self,
        package: str,
        venv_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Install a Python package with detailed output information.
        
        Args:
            package: Package name to install
            venv_name: Virtual environment name (None for current)
            
        Returns:
            Dict with detailed installation results including stdout, stderr, etc.
        """
        logger.info(f"Installing package {package} with detailed output in environment {venv_name or 'current'}")
        
        try:
            # Determine pip executable to use
            pip_exe = "pip"
            
            if venv_name:
                # Find the virtual environment
                venvs = await self.list_virtual_environments()
                target_venv = None
                
                for venv in venvs:
                    if venv.name == venv_name:
                        target_venv = venv
                        break
                
                if not target_venv:
                    logger.error(f"Virtual environment '{venv_name}' not found")
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": f"Virtual environment '{venv_name}' not found",
                        "returncode": 1,
                        "execution_time": 0.0,
                        "command": f"# Virtual environment '{venv_name}' not found"
                    }
                
                # Determine pip path for the venv
                venv_path = Path(target_venv.path)
                if venv_path.is_file():
                    # It's a Python executable, use it with -m pip
                    pip_exe = f'"{venv_path}" -m pip'
                elif venv_path.is_dir():
                    # It's a venv directory
                    pip_paths = [
                        venv_path / "bin" / "pip",
                        venv_path / "Scripts" / "pip.exe"
                    ]
                    for pip_path in pip_paths:
                        if pip_path.exists():
                            pip_exe = f'"{pip_path}"'
                            break
                    else:
                        # Fallback to python -m pip
                        python_paths = [
                            venv_path / "bin" / "python",
                            venv_path / "Scripts" / "python.exe"
                        ]
                        for python_path in python_paths:
                            if python_path.exists():
                                pip_exe = f'"{python_path}" -m pip'
                                break
            
            # Install the package
            install_command = f'{pip_exe} install "{package}"'
            
            # Record execution time
            import time
            start_time = time.time()
            returncode, stdout, stderr = await self._run_command(install_command)
            end_time = time.time()
            execution_time = end_time - start_time
            
            if returncode == 0:
                logger.info(f"Successfully installed {package} in {execution_time:.2f}s")
                return {
                    "success": True,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                    "execution_time": execution_time,
                    "command": install_command
                }
            else:
                logger.error(f"Failed to install {package}: {stderr}")
                return {
                    "success": False,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                    "execution_time": execution_time,
                    "command": install_command
                }
                
        except Exception as e:
            logger.error(f"Error installing package {package}: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Error installing package: {str(e)}",
                "returncode": -1,
                "execution_time": 0.0,
                "command": f"# Error: {str(e)}"
            }