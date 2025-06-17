"""Core command execution utilities for Terminal MCP Server."""

import asyncio
import logging
import os
import signal
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator, Tuple
import errno
import json

from ..models.terminal_models import CommandRequest, CommandResult
from .output_streamer import OutputStreamer

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Handles command execution with streaming support."""
    
    def __init__(self):
        """Initialize command executor."""
        logger.info("CommandExecutor initialized")
        self._command_counter = 0
        self._total_execution_time = 0.0
    
    def _log_command_audit(self, request: CommandRequest, result: CommandResult, execution_id: str):
        """
        Log a comprehensive audit trail for command execution.
        
        Args:
            request: The original command request
            result: The execution result
            execution_id: Unique identifier for this execution
        """
        audit_data = {
            "execution_id": execution_id,
            "timestamp": result.started_at.isoformat(),
            "command": request.command,
            "working_directory": request.working_directory,
            "environment_variables": bool(request.environment_variables),  # Don't log sensitive values
            "environment_var_count": len(request.environment_variables) if request.environment_variables else 0,
            "timeout": request.timeout,
            "capture_output": request.capture_output,
            "exit_code": result.exit_code,
            "execution_time_seconds": result.execution_time,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
            "success": result.exit_code == 0,
            "completed_at": result.completed_at.isoformat()
        }
        
        # Log as structured JSON for easy parsing
        logger.info(f"COMMAND_AUDIT: {json.dumps(audit_data)}")
        
        # Also log human-readable summary
        status = "SUCCESS" if result.exit_code == 0 else f"FAILED(exit_code={result.exit_code})"
        logger.info(f"Command execution {execution_id}: {status} - '{request.command}' in {result.execution_time:.3f}s")

    def _log_command_metrics(self):
        """Log cumulative command execution metrics."""
        logger.debug(f"Command execution metrics: total_commands={self._command_counter}, "
                    f"total_execution_time={self._total_execution_time:.3f}s, "
                    f"average_execution_time={self._total_execution_time/max(1, self._command_counter):.3f}s")

    def _get_error_message(self, exception: Exception) -> str:
        """
        Get a user-friendly error message based on the exception type.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            User-friendly error message
        """
        if isinstance(exception, FileNotFoundError):
            return f"Command or file not found: {str(exception)}"
        elif isinstance(exception, PermissionError):
            return f"Permission denied: {str(exception)}"
        elif isinstance(exception, OSError):
            if exception.errno == errno.ENOENT:
                return f"Command not found: {str(exception)}"
            elif exception.errno == errno.EACCES:
                return f"Permission denied: {str(exception)}"
            elif exception.errno == errno.ENOTDIR:
                return f"Invalid directory path: {str(exception)}"
            else:
                return f"System error: {str(exception)}"
        elif isinstance(exception, asyncio.TimeoutError):
            return "Command execution timed out"
        else:
            return f"Command execution failed: {str(exception)}"

    async def execute(self, request: CommandRequest) -> CommandResult:
        """
        Execute a command and return the result.
        
        Args:
            request: Command execution request
            
        Returns:
            CommandResult with execution details
        """
        started_at = datetime.now()
        self._command_counter += 1
        execution_id = f"cmd_{self._command_counter}_{started_at.strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"[{execution_id}] Starting command execution")
        logger.info(f"[{execution_id}] Executing command: {request.command}")
        logger.debug(f"[{execution_id}] Working directory: {request.working_directory}")
        logger.debug(f"[{execution_id}] Environment variables count: {len(request.environment_variables) if request.environment_variables else 0}")
        if request.environment_variables:
            # Log environment variable names (not values for security)
            env_var_names = list(request.environment_variables.keys())
            logger.debug(f"[{execution_id}] Environment variable names: {env_var_names}")
        logger.debug(f"[{execution_id}] Timeout: {request.timeout}")
        logger.debug(f"[{execution_id}] Capture output: {request.capture_output}")
        
        try:
            # Validate working directory if specified
            if request.working_directory and not os.path.exists(request.working_directory):
                raise FileNotFoundError(f"Working directory does not exist: {request.working_directory}")
            
            if request.working_directory and not os.path.isdir(request.working_directory):
                raise NotADirectoryError(f"Working directory is not a directory: {request.working_directory}")
            
            # Prepare environment variables
            env = os.environ.copy()
            if request.environment_variables:
                # Validate environment variables
                for key, value in request.environment_variables.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        logger.warning(f"[{execution_id}] Invalid environment variable: {key}={value}, skipping")
                        continue
                    env[key] = value
                logger.debug(f"[{execution_id}] Environment variables applied successfully")
            
            # Prepare working directory
            cwd = request.working_directory or os.getcwd()
            logger.debug(f"[{execution_id}] Resolved working directory: {cwd}")
            
            # Execute command
            logger.debug(f"[{execution_id}] Starting command subprocess")
            if request.capture_output:
                stdout_output, stderr_output, exit_code = await self._execute_with_capture(
                    request.command, cwd, env, request.timeout, execution_id
                )
            else:
                stdout_output, stderr_output, exit_code = await self._execute_without_capture(
                    request.command, cwd, env, request.timeout, execution_id
                )
            
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            self._total_execution_time += execution_time
            
            logger.info(f"[{execution_id}] Command completed with exit code: {exit_code}")
            logger.info(f"[{execution_id}] Execution time: {execution_time:.3f}s")
            logger.debug(f"[{execution_id}] Output lengths - stdout: {len(stdout_output)}, stderr: {len(stderr_output)}")
            
            if exit_code != 0:
                logger.warning(f"[{execution_id}] Command failed with exit code {exit_code}: {request.command}")
            else:
                logger.debug(f"[{execution_id}] Command executed successfully")
            
            result = CommandResult(
                command=request.command,
                exit_code=exit_code,
                stdout=stdout_output,
                stderr=stderr_output,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Log comprehensive audit trail
            self._log_command_audit(request, result, execution_id)
            
            # Log metrics periodically
            if self._command_counter % 10 == 0:
                self._log_command_metrics()
            
            return result
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            self._total_execution_time += execution_time
            
            error_message = self._get_error_message(e)
            logger.error(f"[{execution_id}] Command execution failed: {error_message}")
            logger.error(f"[{execution_id}] Exception type: {type(e).__name__}")
            logger.debug(f"[{execution_id}] Full exception: {str(e)}")
            
            result = CommandResult(
                command=request.command,
                exit_code=-1,
                stdout="",
                stderr=error_message,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Log audit trail even for failures
            self._log_command_audit(request, result, execution_id)
            
            return result

    async def _execute_with_capture(
        self, 
        command: str, 
        cwd: str, 
        env: Dict[str, str], 
        timeout: Optional[int],
        execution_id: str
    ) -> tuple[str, str, int]:
        """Execute command with output capture."""
        try:
            logger.debug(f"[{execution_id}] Creating subprocess with output capture")
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            logger.debug(f"[{execution_id}] Subprocess created with PID: {process.pid}")
            
            # Wait for completion with timeout
            try:
                logger.debug(f"[{execution_id}] Waiting for process completion (timeout: {timeout}s)")
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                # Decode output
                stdout_output = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                stderr_output = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                
                logger.debug(f"[{execution_id}] Process completed normally with exit code: {process.returncode}")
                return stdout_output, stderr_output, process.returncode
                
            except asyncio.TimeoutError:
                logger.warning(f"[{execution_id}] Command timed out after {timeout} seconds")
                
                # Kill the process and its children
                await self._kill_process_group(process, execution_id)
                
                # Wait a bit for cleanup
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                    logger.debug(f"[{execution_id}] Process cleanup completed")
                except asyncio.TimeoutError:
                    logger.warning(f"[{execution_id}] Process cleanup timed out")
                    pass
                
                return "", f"Command timed out after {timeout} seconds", -1
                
        except Exception as e:
            logger.error(f"[{execution_id}] Error executing command: {e}")
            return "", f"Error executing command: {str(e)}", -1
    
    async def _execute_without_capture(
        self, 
        command: str, 
        cwd: str, 
        env: Dict[str, str], 
        timeout: Optional[int],
        execution_id: str
    ) -> tuple[str, str, int]:
        """Execute command without output capture."""
        try:
            logger.debug(f"[{execution_id}] Creating subprocess without output capture")
            # Create subprocess without capturing output
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=None,  # Don't capture
                stderr=None,  # Don't capture
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            logger.debug(f"[{execution_id}] Subprocess created with PID: {process.pid}")
            
            # Wait for completion with timeout
            try:
                logger.debug(f"[{execution_id}] Waiting for process completion (timeout: {timeout}s)")
                await asyncio.wait_for(process.wait(), timeout=timeout)
                logger.debug(f"[{execution_id}] Process completed normally with exit code: {process.returncode}")
                return "", "", process.returncode
                
            except asyncio.TimeoutError:
                logger.warning(f"[{execution_id}] Command timed out after {timeout} seconds")
                
                # Kill the process and its children
                await self._kill_process_group(process, execution_id)
                
                # Wait a bit for cleanup
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                    logger.debug(f"[{execution_id}] Process cleanup completed")
                except asyncio.TimeoutError:
                    logger.warning(f"[{execution_id}] Process cleanup timed out")
                    pass
                
                return "", f"Command timed out after {timeout} seconds", -1
                
        except Exception as e:
            logger.error(f"[{execution_id}] Error executing command: {e}")
            return "", f"Error executing command: {str(e)}", -1
    
    async def _kill_process_group(self, process, execution_id: str):
        """Kill process and its children."""
        try:
            logger.debug(f"[{execution_id}] Attempting to terminate process group for PID: {process.pid}")
            if process.pid and hasattr(os, 'killpg'):
                # Kill the entire process group
                logger.debug(f"[{execution_id}] Sending SIGTERM to process group")
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                # Wait a bit, then force kill if needed
                await asyncio.sleep(0.5)
                
                if process.returncode is None:
                    logger.debug(f"[{execution_id}] Process still running, sending SIGKILL to process group")
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    logger.debug(f"[{execution_id}] Process terminated successfully with SIGTERM")
            else:
                # Fallback to killing just the process
                logger.debug(f"[{execution_id}] Using fallback process termination")
                process.terminate()
                await asyncio.sleep(0.5)
                if process.returncode is None:
                    logger.debug(f"[{execution_id}] Force killing process")
                    process.kill()
                    
        except (ProcessLookupError, OSError) as e:
            # Process already dead
            logger.debug(f"[{execution_id}] Process already terminated: {e}")
            pass

    async def execute_with_streaming(
        self, 
        request: CommandRequest
    ) -> Tuple[AsyncGenerator[str, None], CommandResult]:
        """
        Execute a command with real-time output streaming.
        
        Args:
            request: Command execution request
            
        Returns:
            Tuple of (stream_generator, final_result)
        """
        started_at = datetime.now()
        self._command_counter += 1
        execution_id = f"cmd_stream_{self._command_counter}_{started_at.strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"[{execution_id}] Starting streaming command execution")
        logger.info(f"[{execution_id}] Executing command: {request.command}")
        logger.debug(f"[{execution_id}] Working directory: {request.working_directory}")
        logger.debug(f"[{execution_id}] Environment variables count: {len(request.environment_variables) if request.environment_variables else 0}")
        
        try:
            # Validate working directory if specified
            if request.working_directory and not os.path.exists(request.working_directory):
                raise FileNotFoundError(f"Working directory does not exist: {request.working_directory}")
            
            if request.working_directory and not os.path.isdir(request.working_directory):
                raise NotADirectoryError(f"Working directory is not a directory: {request.working_directory}")
            
            # Prepare environment variables
            env = os.environ.copy()
            if request.environment_variables:
                for key, value in request.environment_variables.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        logger.warning(f"[{execution_id}] Invalid environment variable: {key}={value}, skipping")
                        continue
                    env[key] = value
                logger.debug(f"[{execution_id}] Environment variables applied successfully")
            
            # Prepare working directory
            cwd = request.working_directory or os.getcwd()
            logger.debug(f"[{execution_id}] Resolved working directory: {cwd}")
            
            # Create output streamer
            output_streamer = OutputStreamer()
            
            # Execute command with streaming
            stream_generator, final_result = await self._execute_with_streaming_capture(
                request.command, cwd, env, request.timeout, execution_id, output_streamer
            )
            
            return stream_generator, final_result
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            self._total_execution_time += execution_time
            
            error_message = self._get_error_message(e)
            logger.error(f"[{execution_id}] Streaming command execution failed: {error_message}")
            
            result = CommandResult(
                command=request.command,
                exit_code=-1,
                stdout="",
                stderr=error_message,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Create empty stream generator for error case
            async def empty_stream():
                yield f"Error: {error_message}"
                return
            
            return empty_stream(), result

    async def _execute_with_streaming_capture(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        timeout: Optional[int],
        execution_id: str,
        output_streamer: OutputStreamer
    ) -> Tuple[AsyncGenerator[str, None], CommandResult]:
        """Execute command with streaming output capture."""
        started_at = datetime.now()
        
        # Create a shared container for captured chunks that both the generator and result can access
        class ChunkCapture:
            def __init__(self):
                self.chunks = []
                self.completed = False
        
        chunk_capture = ChunkCapture()
        
        try:
            logger.debug(f"[{execution_id}] Creating subprocess for streaming")
            # Create subprocess with pipes
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            logger.debug(f"[{execution_id}] Subprocess created with PID: {process.pid}")
            
            # Create a capturing stream generator that stores chunks as they pass through
            async def capturing_stream_generator():
                try:
                    async for chunk in output_streamer.stream_output(process):
                        chunk_capture.chunks.append(chunk)  # Store in shared container
                        yield chunk
                except Exception as e:
                    logger.error(f"[{execution_id}] Error during output streaming: {e}")
                    error_chunk = f"\n[STREAMING ERROR: {str(e)}]"
                    chunk_capture.chunks.append(error_chunk)
                    yield error_chunk
                finally:
                    chunk_capture.completed = True
                    logger.debug(f"[{execution_id}] Output streaming completed")
            
            # Create a preliminary result that will be updated when process completes
            # But include the shared chunk container immediately
            preliminary_result = CommandResult(
                command=command,
                exit_code=0,  # Will be updated when process completes
                stdout="",  # Will be updated when process completes
                stderr="",  # Will be updated when process completes
                execution_time=0.0,  # Will be updated when process completes
                started_at=started_at,
                completed_at=started_at,  # Will be updated when process completes
                captured_chunks=chunk_capture.chunks  # Reference to shared container
            )
            
            # Start process completion task in background to update the result
            async def update_result_when_complete():
                try:
                    # Wait for process completion with timeout
                    if timeout:
                        await asyncio.wait_for(process.wait(), timeout=timeout)
                    else:
                        await process.wait()
                    
                    completed_at = datetime.now()
                    execution_time = (completed_at - started_at).total_seconds()
                    self._total_execution_time += execution_time
                    
                    # Capture remaining output
                    stdout_bytes, stderr_bytes = await process.communicate()
                    stdout_output = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                    stderr_output = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                    
                    # Update the result object in place
                    preliminary_result.exit_code = process.returncode
                    preliminary_result.stdout = stdout_output
                    preliminary_result.stderr = stderr_output
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
                    
                    logger.info(f"[{execution_id}] Streaming command completed with exit code: {process.returncode}")
                    logger.info(f"[{execution_id}] Execution time: {execution_time:.3f}s")
                    
                    # Log audit trail
                    self._log_command_audit(
                        CommandRequest(command=command, capture_output=True), 
                        preliminary_result, 
                        execution_id
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning(f"[{execution_id}] Streaming command timed out after {timeout} seconds")
                    
                    # Kill the process
                    await self._kill_process_group(process, execution_id)
                    
                    completed_at = datetime.now()
                    execution_time = (completed_at - started_at).total_seconds()
                    self._total_execution_time += execution_time
                    
                    # Update result with timeout info
                    preliminary_result.exit_code = -1
                    preliminary_result.stderr = f"Command timed out after {timeout} seconds"
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
                    
                except Exception as e:
                    logger.error(f"[{execution_id}] Error waiting for process completion: {e}")
                    completed_at = datetime.now()
                    execution_time = (completed_at - started_at).total_seconds()
                    
                    # Update result with error info
                    preliminary_result.exit_code = -1
                    preliminary_result.stderr = f"Error during execution: {str(e)}"
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
            
            # Start background task to update result
            asyncio.create_task(update_result_when_complete())
            
            # Return the stream generator and result immediately
            # The result contains a reference to the shared chunk container
            return capturing_stream_generator(), preliminary_result
            
        except Exception as e:
            logger.error(f"[{execution_id}] Error creating streaming subprocess: {e}")
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            
            result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Error creating subprocess: {str(e)}",
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at,
                captured_chunks=[]  # Empty chunks for error case
            )
            
            async def error_stream():
                yield f"Error: {str(e)}"
                return
            
            return error_stream(), result 