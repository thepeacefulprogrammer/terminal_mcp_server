"""Core command execution utilities for Terminal MCP Server."""

import asyncio
import logging
import os
import signal
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

from ..models.terminal_models import CommandRequest, CommandResult

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Handles command execution with streaming support."""
    
    def __init__(self):
        """Initialize command executor."""
        logger.info("CommandExecutor initialized")
    
    async def execute(self, request: CommandRequest) -> CommandResult:
        """
        Execute a command and return the result.
        
        Args:
            request: Command execution request
            
        Returns:
            CommandResult with execution details
        """
        started_at = datetime.now()
        
        logger.info(f"Executing command: {request.command}")
        logger.debug(f"Working directory: {request.working_directory}")
        logger.debug(f"Environment variables: {request.environment_variables}")
        logger.debug(f"Timeout: {request.timeout}")
        logger.debug(f"Capture output: {request.capture_output}")
        
        try:
            # Prepare environment variables
            env = os.environ.copy()
            if request.environment_variables:
                env.update(request.environment_variables)
            
            # Prepare working directory
            cwd = request.working_directory or os.getcwd()
            
            # Execute command
            if request.capture_output:
                stdout_output, stderr_output, exit_code = await self._execute_with_capture(
                    request.command, cwd, env, request.timeout
                )
            else:
                stdout_output, stderr_output, exit_code = await self._execute_without_capture(
                    request.command, cwd, env, request.timeout
                )
            
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            logger.info(f"Command completed with exit code: {exit_code}")
            logger.debug(f"Execution time: {execution_time:.3f}s")
            
            return CommandResult(
                command=request.command,
                exit_code=exit_code,
                stdout=stdout_output,
                stderr=stderr_output,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            logger.error(f"Command execution failed: {e}")
            
            return CommandResult(
                command=request.command,
                exit_code=-1,
                stdout="",
                stderr=f"Command execution failed: {str(e)}",
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
    
    async def _execute_with_capture(
        self, 
        command: str, 
        cwd: str, 
        env: Dict[str, str], 
        timeout: Optional[int]
    ) -> tuple[str, str, int]:
        """Execute command with output capture."""
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                # Decode output
                stdout_output = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                stderr_output = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                
                return stdout_output, stderr_output, process.returncode
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout} seconds")
                
                # Kill the process and its children
                await self._kill_process_group(process)
                
                # Wait a bit for cleanup
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                return "", f"Command timed out after {timeout} seconds", -1
                
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return "", f"Error executing command: {str(e)}", -1
    
    async def _execute_without_capture(
        self, 
        command: str, 
        cwd: str, 
        env: Dict[str, str], 
        timeout: Optional[int]
    ) -> tuple[str, str, int]:
        """Execute command without output capture."""
        try:
            # Create subprocess without capturing output
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=None,  # Don't capture
                stderr=None,  # Don't capture
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for completion with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                return "", "", process.returncode
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout} seconds")
                
                # Kill the process and its children
                await self._kill_process_group(process)
                
                # Wait a bit for cleanup
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
                return "", f"Command timed out after {timeout} seconds", -1
                
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return "", f"Error executing command: {str(e)}", -1
    
    async def _kill_process_group(self, process):
        """Kill process and its children."""
        try:
            if process.pid and hasattr(os, 'killpg'):
                # Kill the entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                # Wait a bit, then force kill if needed
                await asyncio.sleep(0.5)
                
                if process.returncode is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                # Fallback to killing just the process
                process.terminate()
                await asyncio.sleep(0.5)
                if process.returncode is None:
                    process.kill()
                    
        except (ProcessLookupError, OSError) as e:
            # Process already dead
            logger.debug(f"Process already terminated: {e}")
            pass 