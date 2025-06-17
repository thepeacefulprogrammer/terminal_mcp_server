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
    
    def __init__(self, max_output_size: int = 10485760, buffer_size: int = 8192, enable_safety_checks: bool = True):
        """
        Initialize command executor.
        
        Args:
            max_output_size: Maximum output size in bytes to prevent memory exhaustion
            buffer_size: Buffer size for output streaming
            enable_safety_checks: Whether to perform safety checks on commands
        """
        logger.info("CommandExecutor initialized")
        self._command_counter = 0
        self._total_execution_time = 0.0
        self._max_output_size = max_output_size
        self._buffer_size = buffer_size
        self._enable_safety_checks = enable_safety_checks
    
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
        elif isinstance(exception, NotADirectoryError):
            return f"Invalid directory path - not a directory: {str(exception)}"
        elif isinstance(exception, OSError):
            if exception.errno == errno.ENOENT:
                return f"Command not found: {str(exception)}"
            elif exception.errno == errno.EACCES:
                return f"Permission denied: {str(exception)}"
            elif exception.errno == errno.ENOTDIR:
                return f"Invalid directory path: {str(exception)}"
            elif exception.errno == errno.EMFILE:
                return f"Too many open files: {str(exception)}"
            elif exception.errno == errno.ENFILE:
                return f"System file table overflow: {str(exception)}"
            elif exception.errno == errno.ENOMEM:
                return f"Out of memory: {str(exception)}"
            elif exception.errno == errno.EAGAIN:
                return f"Resource temporarily unavailable: {str(exception)}"
            else:
                return f"System error (errno {exception.errno}): {str(exception)}"
        elif isinstance(exception, asyncio.TimeoutError):
            return "Command execution timed out"
        elif isinstance(exception, ValueError):
            return f"Invalid parameter value: {str(exception)}"
        elif isinstance(exception, UnicodeDecodeError):
            return f"Text encoding error: {str(exception)}"
        elif isinstance(exception, MemoryError):
            return f"Memory exhausted: {str(exception)}"
        elif isinstance(exception, asyncio.CancelledError):
            return "Command execution was cancelled"
        else:
            return f"Command execution failed: {str(exception)} (type: {type(exception).__name__})"

    def _validate_command_safety(self, command: str, execution_id: str) -> tuple[bool, str]:
        """
        Validate command for basic safety checks.
        
        Args:
            command: Command to validate
            execution_id: Execution ID for logging
            
        Returns:
            Tuple of (is_safe, warning_message)
        """
        if not self._enable_safety_checks:
            return True, ""
        
        warnings = []
        
        # Check for extremely long commands
        if len(command) > 50000:  # 50KB command line
            warnings.append(f"Extremely long command ({len(command)} chars) may cause issues")
        
        # Check for suspicious patterns (basic checks only)
        suspicious_patterns = [
            r'rm\s+-rf\s*/',  # Dangerous rm commands
            r'>\s*/dev/sd[a-z]',  # Writing to disk devices
            r':\(\)\{\s*:\s*\|\s*:\s*&\s*\}',  # Fork bomb pattern
            r'sudo\s+rm',  # Sudo rm commands
        ]
        
        import re
        for pattern in suspicious_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                warnings.append(f"Potentially dangerous command pattern detected: {pattern}")
        
        # Check for null bytes which can cause shell issues
        if '\x00' in command:
            warnings.append("Command contains null bytes which may cause parsing issues")
        
        # Log warnings but don't block execution (user responsibility)
        if warnings:
            warning_message = "; ".join(warnings)
            logger.warning(f"[{execution_id}] Command safety warnings: {warning_message}")
            return True, warning_message
        
        return True, ""

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
            # Validate and sanitize inputs
            if not request.command or not request.command.strip():
                logger.warning(f"[{execution_id}] Empty or whitespace-only command received")
                # Allow empty commands but log the warning
            
            # Perform safety validation
            is_safe, safety_warning = self._validate_command_safety(request.command, execution_id)
            if safety_warning:
                logger.warning(f"[{execution_id}] Safety warning: {safety_warning}")
            
            # Validate timeout
            if request.timeout is not None:
                if request.timeout < 0:
                    logger.warning(f"[{execution_id}] Negative timeout {request.timeout} treated as no timeout")
                    request = request.model_copy(update={"timeout": None})
                elif request.timeout == 0:
                    logger.warning(f"[{execution_id}] Zero timeout may cause immediate termination")
            
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
            
            # Wait for completion with timeout - using streaming approach for better timeout handling
            try:
                logger.debug(f"[{execution_id}] Waiting for process completion (timeout: {timeout}s)")
                
                # Use streaming approach to better handle timeouts and partial output
                stdout_parts = []
                stderr_parts = []
                
                async def capture_with_timeout():
                    """Capture output with proper timeout handling that preserves partial output."""
                    stdout_task = None
                    stderr_task = None
                    
                    # Create tasks to read from each stream
                    if process.stdout:
                        stdout_task = asyncio.create_task(self._read_stream_until_timeout(process.stdout, "stdout", execution_id))
                    if process.stderr:
                        stderr_task = asyncio.create_task(self._read_stream_until_timeout(process.stderr, "stderr", execution_id))
                    
                    # Wait for process completion
                    process_task = asyncio.create_task(process.wait())
                    
                    # Gather results, allowing partial completion on timeout
                    tasks = [t for t in [stdout_task, stderr_task, process_task] if t is not None]
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
                    
                    # Cancel any pending tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    
                    # Collect results
                    stdout_result = ""
                    stderr_result = ""
                    
                    if stdout_task and stdout_task.done():
                        try:
                            stdout_result = await stdout_task
                        except Exception as e:
                            logger.debug(f"[{execution_id}] Stdout reading error: {e}")
                    
                    if stderr_task and stderr_task.done():
                        try:
                            stderr_result = await stderr_task
                        except Exception as e:
                            logger.debug(f"[{execution_id}] Stderr reading error: {e}")
                    
                    return stdout_result, stderr_result
                
                stdout_output, stderr_output = await asyncio.wait_for(capture_with_timeout(), timeout=timeout)
                
                logger.debug(f"[{execution_id}] Process completed normally with exit code: {process.returncode}")
                return stdout_output, stderr_output, process.returncode
                
            except asyncio.TimeoutError:
                logger.warning(f"[{execution_id}] Command timed out after {timeout} seconds")
                
                # Try to capture any remaining buffered output
                partial_stdout = ""
                partial_stderr = ""
                
                try:
                    # Quick attempt to read any immediately available data
                    if process.stdout and not process.stdout.at_eof():
                        try:
                            # Read with a very short timeout to get whatever is immediately available
                            data = await asyncio.wait_for(process.stdout.read(32768), timeout=0.05)
                            if data:
                                partial_stdout = data.decode('utf-8', errors='replace')
                        except (asyncio.TimeoutError, UnicodeDecodeError, Exception):
                            pass
                    
                    if process.stderr and not process.stderr.at_eof():
                        try:
                            data = await asyncio.wait_for(process.stderr.read(32768), timeout=0.05)
                            if data:
                                partial_stderr = data.decode('utf-8', errors='replace')
                        except (asyncio.TimeoutError, UnicodeDecodeError, Exception):
                            pass
                            
                except Exception as read_error:
                    logger.debug(f"[{execution_id}] Could not read partial output: {read_error}")
                
                # Kill the process and its children
                await self._kill_process_group(process, execution_id)
                
                # Wait a bit for cleanup
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                    logger.debug(f"[{execution_id}] Process cleanup completed")
                except asyncio.TimeoutError:
                    logger.warning(f"[{execution_id}] Process cleanup timed out")
                    pass
                
                # Return any partial output we managed to capture along with timeout error
                timeout_stderr = f"Command timed out after {timeout} seconds"
                if partial_stderr:
                    timeout_stderr = f"{partial_stderr}\n{timeout_stderr}"
                
                return partial_stdout, timeout_stderr, -1
                
        except Exception as e:
            logger.error(f"[{execution_id}] Error executing command: {e}")
            return "", f"Error executing command: {str(e)}", -1
    
    async def _read_stream_until_timeout(self, stream: asyncio.StreamReader, stream_name: str, execution_id: str) -> str:
        """
        Read from a stream until it's exhausted or cancelled, preserving partial output.
        
        Args:
            stream: Stream to read from
            stream_name: Name for logging
            execution_id: Execution ID for logging
            
        Returns:
            All content read from the stream
        """
        content_parts = []
        total_size = 0
        
        try:
            while True:
                try:
                    chunk_bytes = await stream.read(self._buffer_size)
                    
                    if not chunk_bytes:
                        # End of stream
                        break
                    
                    # Check size limits
                    total_size += len(chunk_bytes)
                    if total_size > self._max_output_size:
                        logger.warning(f"[{execution_id}] {stream_name} size limit exceeded: {total_size} > {self._max_output_size}")
                        content_parts.append(f"\n[{stream_name.upper()} TRUNCATED: Size limit exceeded]")
                        break
                    
                    # Decode with error handling
                    try:
                        chunk_str = chunk_bytes.decode('utf-8', errors='replace')
                        content_parts.append(chunk_str)
                    except Exception as decode_error:
                        logger.warning(f"[{execution_id}] Decode error for {stream_name}: {decode_error}")
                        chunk_str = chunk_bytes.decode('latin-1', errors='replace')
                        content_parts.append(chunk_str)
                        
                except asyncio.CancelledError:
                    # Task was cancelled - return whatever we've read so far
                    logger.debug(f"[{execution_id}] {stream_name} reading cancelled, preserving partial output")
                    break
                except Exception as e:
                    logger.debug(f"[{execution_id}] Error reading {stream_name}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"[{execution_id}] Unexpected error reading {stream_name}: {e}")
        
        result = ''.join(content_parts)
        logger.debug(f"[{execution_id}] Read {len(result)} characters from {stream_name}")
        return result
    
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
        """Kill process and its children with comprehensive error handling."""
        try:
            logger.debug(f"[{execution_id}] Attempting to terminate process group for PID: {process.pid}")
            
            if not process.pid:
                logger.warning(f"[{execution_id}] No PID available for process termination")
                return
            
            if hasattr(os, 'killpg'):
                try:
                    # Kill the entire process group
                    logger.debug(f"[{execution_id}] Sending SIGTERM to process group")
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                    # Wait a bit, then check if process is still running
                    await asyncio.sleep(0.5)
                    
                    if process.returncode is None:
                        logger.debug(f"[{execution_id}] Process still running, sending SIGKILL to process group")
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except (ProcessLookupError, OSError) as kill_error:
                            logger.debug(f"[{execution_id}] SIGKILL failed (process may be dead): {kill_error}")
                    else:
                        logger.debug(f"[{execution_id}] Process terminated successfully with SIGTERM")
                        
                except (ProcessLookupError, OSError) as pg_error:
                    logger.debug(f"[{execution_id}] Process group termination failed: {pg_error}")
                    # Fall back to individual process termination
                    self._terminate_individual_process(process, execution_id)
            else:
                # System doesn't support process groups
                logger.debug(f"[{execution_id}] Process groups not supported, using individual process termination")
                self._terminate_individual_process(process, execution_id)
                    
        except Exception as e:
            logger.error(f"[{execution_id}] Unexpected error during process termination: {e}")
            # Last resort - try individual process kill
            try:
                if process.returncode is None:
                    process.kill()
            except Exception as last_resort_error:
                logger.error(f"[{execution_id}] Last resort process kill failed: {last_resort_error}")
    
    def _terminate_individual_process(self, process, execution_id: str):
        """Terminate an individual process as fallback."""
        try:
            logger.debug(f"[{execution_id}] Using fallback individual process termination")
            process.terminate()
            
            # Give process time to terminate gracefully
            # Note: We can't use asyncio.sleep here since this is a sync method
            import time
            time.sleep(0.5)
            
            if process.returncode is None:
                logger.debug(f"[{execution_id}] Force killing individual process")
                process.kill()
                
        except (ProcessLookupError, OSError) as e:
            # Process already dead or can't be killed
            logger.debug(f"[{execution_id}] Individual process termination failed (process may be dead): {e}")

    async def execute_with_streaming(
        self, 
        request: CommandRequest
    ) -> Tuple[AsyncGenerator[str, None], CommandResult]:
        """
        Execute command with real-time output streaming.
        
        Args:
            request: Command execution request
            
        Returns:
            Tuple of (stream_generator, result)
            
        Note: The result object is updated as the command executes
        """
        started_at = datetime.now()
        execution_id = f"stream_{self._command_counter:04d}"
        self._command_counter += 1
        
        logger.info(f"[{execution_id}] Starting streaming command execution: {request.command}")
        
        try:
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
            
            # Create output streamer with configured memory limits
            output_streamer = OutputStreamer(
                buffer_size=self._buffer_size,
                max_output_size=self._max_output_size
            )
            
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

    async def execute_with_separated_streaming(
        self, 
        request: CommandRequest
    ) -> Tuple[AsyncGenerator[Tuple[str, str], None], CommandResult]:
        """
        Execute command with real-time separated stdout/stderr streaming.
        
        Args:
            request: Command execution request
            
        Returns:
            Tuple of (separated_stream_generator, result)
            
        Note: The result object is updated as the command executes.
        The stream generator yields tuples of (stdout_chunk, stderr_chunk).
        """
        started_at = datetime.now()
        execution_id = f"sep_stream_{self._command_counter:04d}"
        self._command_counter += 1
        
        logger.info(f"[{execution_id}] Starting separated streaming command execution: {request.command}")
        
        try:
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
            
            # Create output streamer with configured memory limits
            output_streamer = OutputStreamer(
                buffer_size=self._buffer_size,
                max_output_size=self._max_output_size
            )
            
            # Execute command with separated streaming
            stream_generator, final_result = await self._execute_with_separated_streaming_capture(
                request.command, cwd, env, request.timeout, execution_id, output_streamer
            )
            
            return stream_generator, final_result
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()
            self._total_execution_time += execution_time
            
            error_message = self._get_error_message(e)
            logger.error(f"[{execution_id}] Separated streaming command execution failed: {error_message}")
            
            result = CommandResult(
                command=request.command,
                exit_code=-1,
                stdout="",
                stderr=error_message,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Create empty separated stream generator for error case
            async def empty_separated_stream():
                yield "", f"Error: {error_message}"
                return
            
            return empty_separated_stream(), result

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

    async def _execute_with_separated_streaming_capture(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        timeout: Optional[int],
        execution_id: str,
        output_streamer: OutputStreamer
    ) -> Tuple[AsyncGenerator[Tuple[str, str], None], CommandResult]:
        """Execute command with separated streaming output capture."""
        started_at = datetime.now()
        
        # Create a shared container for captured chunks that both the generator and result can access
        class SeparatedChunkCapture:
            def __init__(self):
                self.stdout_chunks = []
                self.stderr_chunks = []
                self.completed = False
        
        chunk_capture = SeparatedChunkCapture()
        
        try:
            logger.debug(f"[{execution_id}] Creating subprocess for separated streaming")
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
            async def capturing_separated_stream_generator():
                try:
                    async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(process):
                        # Store in shared container
                        if stdout_chunk:
                            chunk_capture.stdout_chunks.append(stdout_chunk)
                        if stderr_chunk:
                            chunk_capture.stderr_chunks.append(stderr_chunk)
                        yield stdout_chunk, stderr_chunk
                except Exception as e:
                    logger.error(f"[{execution_id}] Error during separated output streaming: {e}")
                    error_chunk = f"\n[SEPARATED STREAMING ERROR: {str(e)}]"
                    chunk_capture.stderr_chunks.append(error_chunk)
                    yield "", error_chunk
                finally:
                    chunk_capture.completed = True
                    logger.debug(f"[{execution_id}] Separated output streaming completed")
            
            # Create a preliminary result that will be updated when process completes
            preliminary_result = CommandResult(
                command=command,
                exit_code=0,  # Will be updated when process completes
                stdout="",  # Will be updated when process completes
                stderr="",  # Will be updated when process completes
                execution_time=0.0,  # Will be updated when process completes
                started_at=started_at,
                completed_at=started_at,  # Will be updated when process completes
                captured_chunks=[]  # Will be updated with combined chunks
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
                    
                    # Capture any remaining output
                    stdout_bytes, stderr_bytes = await process.communicate()
                    stdout_output = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                    stderr_output = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                    
                    # Combine captured chunks with final output
                    all_stdout = ''.join(chunk_capture.stdout_chunks) + stdout_output
                    all_stderr = ''.join(chunk_capture.stderr_chunks) + stderr_output
                    
                    # Update the result object in place
                    preliminary_result.exit_code = process.returncode
                    preliminary_result.stdout = all_stdout
                    preliminary_result.stderr = all_stderr
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
                    # Combine chunks for backward compatibility
                    preliminary_result.captured_chunks = chunk_capture.stdout_chunks + chunk_capture.stderr_chunks
                    
                    logger.info(f"[{execution_id}] Separated streaming command completed with exit code: {process.returncode}")
                    logger.info(f"[{execution_id}] Execution time: {execution_time:.3f}s")
                    
                    # Log audit trail
                    self._log_command_audit(
                        CommandRequest(command=command, capture_output=True), 
                        preliminary_result, 
                        execution_id
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning(f"[{execution_id}] Separated streaming command timed out after {timeout} seconds")
                    
                    # Kill the process
                    await self._kill_process_group(process, execution_id)
                    
                    completed_at = datetime.now()
                    execution_time = (completed_at - started_at).total_seconds()
                    self._total_execution_time += execution_time
                    
                    # Update result with timeout info
                    preliminary_result.exit_code = -1
                    preliminary_result.stdout = ''.join(chunk_capture.stdout_chunks)
                    preliminary_result.stderr = ''.join(chunk_capture.stderr_chunks) + f"\nCommand timed out after {timeout} seconds"
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
                    
                except Exception as e:
                    logger.error(f"[{execution_id}] Error waiting for process completion: {e}")
                    completed_at = datetime.now()
                    execution_time = (completed_at - started_at).total_seconds()
                    
                    # Update result with error info
                    preliminary_result.exit_code = -1
                    preliminary_result.stdout = ''.join(chunk_capture.stdout_chunks)
                    preliminary_result.stderr = ''.join(chunk_capture.stderr_chunks) + f"\nError during execution: {str(e)}"
                    preliminary_result.execution_time = execution_time
                    preliminary_result.completed_at = completed_at
            
            # Start background task to update result
            asyncio.create_task(update_result_when_complete())
            
            # Return the stream generator and result immediately
            return capturing_separated_stream_generator(), preliminary_result
            
        except Exception as e:
            logger.error(f"[{execution_id}] Error creating separated streaming subprocess: {e}")
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
            
            async def error_separated_stream():
                yield "", f"Error: {str(e)}"
                return
            
            return error_separated_stream(), result 