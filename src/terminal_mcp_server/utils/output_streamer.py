"""Real-time output streaming utilities for Terminal MCP Server."""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Union
import sys

logger = logging.getLogger(__name__)


class OutputStreamer:
    """Handles real-time output streaming for command execution."""
    
    def __init__(self, buffer_size: int = 8192, max_output_size: int = 10485760):
        """
        Initialize output streamer.
        
        Args:
            buffer_size: Size of output buffer in bytes
            max_output_size: Maximum total output size in bytes
            
        Raises:
            ValueError: If buffer_size is invalid (zero or negative)
        """
        # Validate buffer size
        if buffer_size <= 0:
            raise ValueError(f"Buffer size must be positive, got: {buffer_size}")
        
        if max_output_size <= 0:
            raise ValueError(f"Max output size must be positive, got: {max_output_size}")
        
        self.buffer_size = buffer_size
        self.max_output_size = max_output_size
        self._original_buffer_size = buffer_size  # Store original for reset capability
        logger.info(f"OutputStreamer initialized with buffer size: {buffer_size}")
    
    def adjust_buffer_size(self, new_buffer_size: int) -> None:
        """
        Dynamically adjust the buffer size during runtime.
        
        Args:
            new_buffer_size: New buffer size in bytes
            
        Raises:
            ValueError: If new_buffer_size is invalid
        """
        if new_buffer_size <= 0:
            raise ValueError(f"Buffer size must be positive, got: {new_buffer_size}")
        
        old_size = self.buffer_size
        self.buffer_size = new_buffer_size
        logger.info(f"Buffer size adjusted from {old_size} to {new_buffer_size}")
    
    def reset_buffer_size(self) -> None:
        """Reset buffer size to original initialization value."""
        old_size = self.buffer_size
        self.buffer_size = self._original_buffer_size
        logger.info(f"Buffer size reset from {old_size} to {self.buffer_size}")
    
    def get_buffer_stats(self) -> dict:
        """
        Get current buffer configuration statistics.
        
        Returns:
            Dictionary containing buffer size information
        """
        return {
            "current_buffer_size": self.buffer_size,
            "original_buffer_size": self._original_buffer_size,
            "max_output_size": self.max_output_size,
            "buffer_size_adjusted": self.buffer_size != self._original_buffer_size
        }
    
    async def stream_output(
        self,
        process: asyncio.subprocess.Process
    ) -> AsyncGenerator[str, None]:
        """
        Stream output from a process in real-time.
        
        Args:
            process: The subprocess to stream from
            
        Yields:
            Output chunks as they become available
        """
        logger.info("Starting output streaming")
        
        try:
            if not process.stdout:
                logger.warning("No stdout stream available for streaming")
                return
            
            total_size = 0
            while True:
                # Read chunks of data from stdout
                chunk_bytes = await process.stdout.read(self.buffer_size)
                
                if not chunk_bytes:
                    # End of stream
                    break
                
                # Check output size limits
                total_size += len(chunk_bytes)
                if total_size > self.max_output_size:
                    logger.warning(f"Output size limit exceeded: {total_size} > {self.max_output_size}")
                    yield f"\n[OUTPUT TRUNCATED: Size limit of {self.max_output_size} bytes exceeded]"
                    break
                
                # Decode bytes to string with error handling
                try:
                    chunk_str = chunk_bytes.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    chunk_str = chunk_bytes.decode('utf-8', errors='replace')
                
                yield chunk_str
                
        except asyncio.CancelledError:
            logger.info("Output streaming was cancelled")
            yield "\n[STREAMING CANCELLED]"
            raise
        except UnicodeDecodeError as e:
            logger.warning(f"Unicode decode error during streaming: {e}")
            yield f"\n[ENCODING ERROR: {str(e)}]"
        except MemoryError as e:
            logger.error(f"Memory exhausted during streaming: {e}")
            yield f"\n[MEMORY ERROR: Output too large]"
        except OSError as e:
            logger.error(f"I/O error during streaming: {e}")
            yield f"\n[I/O ERROR: {str(e)}]"
        except Exception as e:
            logger.error(f"Unexpected error during output streaming: {e}")
            yield f"\n[STREAMING ERROR: {type(e).__name__}: {str(e)}]"
        
        finally:
            logger.info("Output streaming completed")
    
    async def capture_output(
        self,
        stdout: Optional[asyncio.StreamReader],
        stderr: Optional[asyncio.StreamReader]
    ) -> tuple[str, str]:
        """
        Capture complete output from stdout and stderr.
        
        Args:
            stdout: Stdout stream reader
            stderr: Stderr stream reader
            
        Returns:
            Tuple of (stdout_content, stderr_content)
        """
        logger.info("Capturing output")
        
        # Capture stdout and stderr concurrently
        tasks = []
        
        if stdout:
            tasks.append(self._read_stream_content(stdout, "stdout"))
        else:
            tasks.append(self._create_empty_task())
        
        if stderr:
            tasks.append(self._read_stream_content(stderr, "stderr"))
        else:
            tasks.append(self._create_empty_task())
        
        try:
            stdout_content, stderr_content = await asyncio.gather(*tasks)
            return stdout_content, stderr_content
        except Exception as e:
            logger.error(f"Error capturing output: {e}")
            return "", f"Error capturing output: {str(e)}"
    
    async def _read_stream_content(self, stream: asyncio.StreamReader, stream_name: str) -> str:
        """
        Read all content from a stream with buffer size management.
        
        Args:
            stream: Stream reader to read from
            stream_name: Name of the stream for logging
            
        Returns:
            Complete stream content as string
        """
        content_parts = []
        total_size = 0
        
        try:
            while True:
                chunk_bytes = await stream.read(self.buffer_size)
                
                if not chunk_bytes:
                    # End of stream
                    break
                
                # Check size limits
                total_size += len(chunk_bytes)
                if total_size > self.max_output_size:
                    logger.warning(f"{stream_name} size limit exceeded: {total_size} > {self.max_output_size}")
                    content_parts.append(f"\n[{stream_name.upper()} TRUNCATED: Size limit exceeded]")
                    break
                
                # Decode with error handling
                try:
                    chunk_str = chunk_bytes.decode('utf-8', errors='replace')
                    content_parts.append(chunk_str)
                except Exception as decode_error:
                    logger.warning(f"Decode error for {stream_name}: {decode_error}")
                    # Fallback to latin-1 which can decode any byte sequence
                    chunk_str = chunk_bytes.decode('latin-1', errors='replace')
                    content_parts.append(chunk_str)
        
        except Exception as e:
            logger.error(f"Error reading {stream_name}: {e}")
            content_parts.append(f"\n[{stream_name.upper()} READ ERROR: {str(e)}]")
        
        return ''.join(content_parts)
    
    async def _create_empty_task(self) -> str:
        """Create an empty task that returns empty string."""
        return ""
    
    async def stream_output_with_separation(
        self,
        process: asyncio.subprocess.Process
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Stream output from a process with stdout/stderr separation.
        
        Args:
            process: The subprocess to stream from
            
        Yields:
            Tuples of (stdout_chunk, stderr_chunk) as they become available
        """
        logger.info("Starting separated output streaming")
        
        try:
            # Create async generators for each stream
            stdout_generator = None
            stderr_generator = None
            
            if process.stdout:
                stdout_generator = self._stream_single_output(process.stdout, "stdout")
            
            if process.stderr:
                stderr_generator = self._stream_single_output(process.stderr, "stderr")
            
            # Stream both outputs concurrently with real-time merging
            if stdout_generator and stderr_generator:
                async for stdout_chunk, stderr_chunk in self._merge_streams_realtime(stdout_generator, stderr_generator):
                    yield stdout_chunk, stderr_chunk
            elif stdout_generator:
                async for chunk in stdout_generator:
                    yield chunk, ""
            elif stderr_generator:
                async for chunk in stderr_generator:
                    yield "", chunk
            else:
                # No streams available
                logger.warning("No stdout or stderr streams available for separated streaming")
                    
        except Exception as e:
            logger.error(f"Error during separated streaming: {e}")
            yield f"[STREAMING ERROR: {str(e)}]", ""
        
        finally:
            logger.info("Separated output streaming completed")
    
    async def _stream_single_output(self, stream: asyncio.StreamReader, stream_name: str) -> AsyncGenerator[str, None]:
        """Stream output from a single stream with proper error handling."""
        total_size = 0
        
        try:
            while True:
                chunk_bytes = await stream.read(self.buffer_size)
                
                if not chunk_bytes:
                    break
                
                total_size += len(chunk_bytes)
                if total_size > self.max_output_size:
                    logger.warning(f"{stream_name} streaming size limit exceeded")
                    yield f"[{stream_name.upper()} TRUNCATED: Size limit exceeded]"
                    break
                
                try:
                    chunk_str = chunk_bytes.decode('utf-8', errors='replace')
                    yield chunk_str
                except Exception as e:
                    logger.warning(f"Decode error in {stream_name} streaming: {e}")
                    yield f"[{stream_name.upper()} DECODE ERROR]"
                    
        except Exception as e:
            logger.error(f"Error streaming {stream_name}: {e}")
            yield f"[{stream_name.upper()} STREAM ERROR: {str(e)}]"
    
    async def _merge_streams_realtime(self, stdout_generator, stderr_generator) -> AsyncGenerator[tuple[str, str], None]:
        """
        Merge two async generators into real-time combined output.
        
        This simplified implementation alternates between reading from stdout and stderr,
        yielding chunks as they become available.
        """
        # Convert generators to async iterators
        stdout_iter = aiter(stdout_generator)
        stderr_iter = aiter(stderr_generator)
        
        # Track if streams are exhausted
        stdout_exhausted = False
        stderr_exhausted = False
        
        while not (stdout_exhausted and stderr_exhausted):
            stdout_chunk = ""
            stderr_chunk = ""
            
            # Try to get chunk from stdout
            if not stdout_exhausted:
                try:
                    stdout_chunk = await asyncio.wait_for(anext(stdout_iter), timeout=0.01)
                except (StopAsyncIteration, asyncio.TimeoutError):
                    if isinstance(sys.exc_info()[1], StopAsyncIteration):
                        stdout_exhausted = True
                except Exception as e:
                    logger.warning(f"Error reading stdout chunk: {e}")
                    stdout_chunk = f"[STDOUT ERROR: {str(e)}]"
            
            # Try to get chunk from stderr
            if not stderr_exhausted:
                try:
                    stderr_chunk = await asyncio.wait_for(anext(stderr_iter), timeout=0.01)
                except (StopAsyncIteration, asyncio.TimeoutError):
                    if isinstance(sys.exc_info()[1], StopAsyncIteration):
                        stderr_exhausted = True
                except Exception as e:
                    logger.warning(f"Error reading stderr chunk: {e}")
                    stderr_chunk = f"[STDERR ERROR: {str(e)}]"
            
            # Yield if we got any chunks
            if stdout_chunk or stderr_chunk:
                yield stdout_chunk, stderr_chunk 