"""Real-time output streaming utilities for Terminal MCP Server."""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Union

logger = logging.getLogger(__name__)


class OutputStreamer:
    """Handles real-time output streaming for command execution."""
    
    def __init__(self, buffer_size: int = 8192, max_output_size: int = 10485760):
        """
        Initialize output streamer.
        
        Args:
            buffer_size: Size of output buffer in bytes
            max_output_size: Maximum total output size in bytes
        """
        self.buffer_size = buffer_size
        self.max_output_size = max_output_size
        logger.info(f"OutputStreamer initialized with buffer size: {buffer_size}")
    
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
                
        except Exception as e:
            logger.error(f"Error during output streaming: {e}")
            yield f"\n[STREAMING ERROR: {str(e)}]"
        
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
            stdout_task = None
            stderr_task = None
            
            if process.stdout:
                stdout_task = asyncio.create_task(self._stream_single_output(process.stdout, "stdout"))
            
            if process.stderr:
                stderr_task = asyncio.create_task(self._stream_single_output(process.stderr, "stderr"))
            
            # Stream both outputs concurrently
            if stdout_task and stderr_task:
                async for stdout_chunk, stderr_chunk in self._merge_streams(stdout_task, stderr_task):
                    yield stdout_chunk, stderr_chunk
            elif stdout_task:
                async for chunk in stdout_task:
                    yield chunk, ""
            elif stderr_task:
                async for chunk in stderr_task:
                    yield "", chunk
                    
        except Exception as e:
            logger.error(f"Error during separated streaming: {e}")
            yield f"[STREAMING ERROR: {str(e)}]", ""
        
        finally:
            logger.info("Separated output streaming completed")
    
    async def _stream_single_output(self, stream: asyncio.StreamReader, stream_name: str) -> AsyncGenerator[str, None]:
        """Stream output from a single stream."""
        total_size = 0
        
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
    
    async def _merge_streams(self, stdout_task, stderr_task) -> AsyncGenerator[tuple[str, str], None]:
        """Merge two stream tasks into combined output."""
        # This is a simplified implementation
        # In a more complex implementation, you might want to interleave the streams
        # based on timing, but for now we'll alternate between them
        
        stdout_chunks = []
        stderr_chunks = []
        
        # Collect all chunks (simplified approach)
        try:
            async for chunk in stdout_task:
                stdout_chunks.append(chunk)
        except Exception:
            pass
            
        try:
            async for chunk in stderr_task:
                stderr_chunks.append(chunk)
        except Exception:
            pass
        
        # Yield combined results
        max_len = max(len(stdout_chunks), len(stderr_chunks))
        for i in range(max_len):
            stdout_chunk = stdout_chunks[i] if i < len(stdout_chunks) else ""
            stderr_chunk = stderr_chunks[i] if i < len(stderr_chunks) else ""
            yield stdout_chunk, stderr_chunk 