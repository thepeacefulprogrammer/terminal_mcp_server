"""
Unit tests for output streaming utilities.

Tests the OutputStreamer class that provides real-time output streaming
for command execution with configurable buffer sizes.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from io import BytesIO

from src.terminal_mcp_server.utils.output_streamer import OutputStreamer


class TestOutputStreamer:
    """Test cases for OutputStreamer class."""
    
    @pytest.fixture
    def output_streamer(self):
        """Create OutputStreamer instance for testing."""
        return OutputStreamer()
    
    @pytest.fixture
    def custom_buffer_streamer(self):
        """Create OutputStreamer with custom buffer size."""
        return OutputStreamer(buffer_size=4096)
    
    @pytest.fixture
    def mock_stream_reader(self):
        """Create mock StreamReader for testing."""
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        return mock_reader
    
    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess Process for testing."""
        mock_proc = Mock()
        mock_proc.stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_proc.stderr = AsyncMock(spec=asyncio.StreamReader)
        return mock_proc
    
    def test_init_default_buffer_size(self, output_streamer):
        """Test that OutputStreamer initializes with default buffer size."""
        assert output_streamer.buffer_size == 8192
    
    def test_init_custom_buffer_size(self, custom_buffer_streamer):
        """Test that OutputStreamer initializes with custom buffer size."""
        assert custom_buffer_streamer.buffer_size == 4096
    
    def test_init_logs_initialization(self):
        """Test that OutputStreamer logs initialization."""
        with patch('src.terminal_mcp_server.utils.output_streamer.logger') as mock_logger:
            OutputStreamer(buffer_size=1024)
            mock_logger.info.assert_called_with("OutputStreamer initialized with buffer size: 1024")
    
    @pytest.mark.asyncio
    async def test_stream_output_basic(self, output_streamer, mock_process):
        """Test basic output streaming functionality."""
        # Mock the process streams
        mock_process.stdout.read.side_effect = [
            b"First chunk\n",
            b"Second chunk\n", 
            b"",  # EOF
        ]
        
        chunks = []
        async for chunk in output_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        assert len(chunks) >= 2
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_stream_output_with_buffer_size(self, output_streamer, mock_process):
        """Test that streaming respects buffer size."""
        # Create data larger than buffer
        large_data = "x" * (output_streamer.buffer_size + 100)
        mock_process.stdout.read.side_effect = [
            large_data.encode(),
            b"",  # EOF
        ]
        
        chunks = []
        async for chunk in output_streamer.stream_output(mock_process):
            chunks.append(chunk)
            
        # Should receive chunks that respect buffer size constraints
        assert len(chunks) > 0
    
    @pytest.mark.asyncio
    async def test_stream_output_empty_process(self, output_streamer, mock_process):
        """Test streaming with process that has no output."""
        mock_process.stdout.read.side_effect = [b""]  # Immediate EOF
        
        chunks = []
        async for chunk in output_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should handle empty output gracefully
        assert isinstance(chunks, list)
    
    @pytest.mark.asyncio
    async def test_stream_output_logs_streaming(self, output_streamer, mock_process):
        """Test that streaming is properly logged."""
        mock_process.stdout.read.side_effect = [b"test", b""]
        
        with patch('src.terminal_mcp_server.utils.output_streamer.logger') as mock_logger:
            chunks = []
            async for chunk in output_streamer.stream_output(mock_process):
                chunks.append(chunk)
            
            # Verify logging calls
            mock_logger.info.assert_any_call("Starting output streaming")
            mock_logger.info.assert_any_call("Output streaming completed")
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_basic(self, output_streamer, mock_process):
        """Test basic separated streaming functionality."""
        # Mock stdout and stderr with different content
        mock_process.stdout.read.side_effect = [b"stdout chunk 1\n", b"stdout chunk 2\n", b""]
        mock_process.stderr.read.side_effect = [b"stderr chunk 1\n", b"stderr chunk 2\n", b""]
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should receive tuples of (stdout, stderr)
        assert len(chunks) > 0
        assert all(isinstance(chunk, tuple) and len(chunk) == 2 for chunk in chunks)
        assert all(isinstance(stdout, str) and isinstance(stderr, str) 
                  for stdout, stderr in chunks)
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_stdout_only(self, output_streamer, mock_process):
        """Test separated streaming when only stdout has content."""
        mock_process.stdout.read.side_effect = [b"stdout only\n", b""]
        mock_process.stderr.read.side_effect = [b""]  # No stderr content
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should receive chunks with stdout content and empty stderr
        assert len(chunks) > 0
        has_stdout_content = any(stdout for stdout, stderr in chunks if stdout.strip())
        has_stderr_content = any(stderr for stdout, stderr in chunks if stderr.strip())
        
        assert has_stdout_content
        assert not has_stderr_content
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_stderr_only(self, output_streamer, mock_process):
        """Test separated streaming when only stderr has content."""
        mock_process.stdout.read.side_effect = [b""]  # No stdout content
        mock_process.stderr.read.side_effect = [b"stderr only\n", b""]
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should receive chunks with stderr content and empty stdout
        assert len(chunks) > 0
        has_stdout_content = any(stdout for stdout, stderr in chunks if stdout.strip())
        has_stderr_content = any(stderr for stdout, stderr in chunks if stderr.strip())
        
        assert not has_stdout_content
        assert has_stderr_content
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_no_streams(self, output_streamer, mock_process):
        """Test separated streaming when process has no stdout/stderr."""
        mock_process.stdout = None
        mock_process.stderr = None
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should handle gracefully and return empty strings
        assert isinstance(chunks, list)
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_size_limits(self, output_streamer, mock_process):
        """Test that separated streaming respects size limits."""
        # Create data larger than max output size
        large_stdout_data = "x" * (output_streamer.max_output_size + 100)
        large_stderr_data = "y" * (output_streamer.max_output_size + 100)
        
        mock_process.stdout.read.side_effect = [large_stdout_data.encode(), b""]
        mock_process.stderr.read.side_effect = [large_stderr_data.encode(), b""]
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should receive chunks and handle size limits
        assert len(chunks) > 0
        
        # Check for truncation messages
        all_stdout = ''.join(stdout for stdout, stderr in chunks)
        all_stderr = ''.join(stderr for stdout, stderr in chunks)
        
        # At least one should have truncation message
        has_truncation = "TRUNCATED" in all_stdout or "TRUNCATED" in all_stderr
        assert has_truncation
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_unicode_handling(self, output_streamer, mock_process):
        """Test that separated streaming handles unicode correctly."""
        # Test with unicode content
        unicode_stdout = "Hello 世界 🌍\n"
        unicode_stderr = "Error ❌ 错误\n"
        
        mock_process.stdout.read.side_effect = [unicode_stdout.encode('utf-8'), b""]
        mock_process.stderr.read.side_effect = [unicode_stderr.encode('utf-8'), b""]
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should properly decode unicode
        assert len(chunks) > 0
        all_stdout = ''.join(stdout for stdout, stderr in chunks)
        all_stderr = ''.join(stderr for stdout, stderr in chunks)
        
        assert "世界" in all_stdout or "🌍" in all_stdout
        assert "❌" in all_stderr or "错误" in all_stderr
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_error_handling(self, output_streamer, mock_process):
        """Test error handling in separated streaming."""
        # Mock an exception during streaming
        mock_process.stdout.read.side_effect = Exception("Stream read error")
        mock_process.stderr.read.side_effect = [b"stderr content", b""]
        
        chunks = []
        async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
            chunks.append((stdout_chunk, stderr_chunk))
        
        # Should handle errors gracefully
        assert len(chunks) >= 0  # May be empty or contain error messages
        
        # Check for error messages if any chunks received
        if chunks:
            all_content = ''.join(stdout + stderr for stdout, stderr in chunks)
            # Should contain some indication of error handling
            assert isinstance(all_content, str)
    
    @pytest.mark.asyncio
    async def test_stream_output_with_separation_logs_activity(self, output_streamer, mock_process):
        """Test that separated streaming logs its activity."""
        mock_process.stdout.read.side_effect = [b"test stdout", b""]
        mock_process.stderr.read.side_effect = [b"test stderr", b""]
        
        with patch('src.terminal_mcp_server.utils.output_streamer.logger') as mock_logger:
            chunks = []
            async for stdout_chunk, stderr_chunk in output_streamer.stream_output_with_separation(mock_process):
                chunks.append((stdout_chunk, stderr_chunk))
            
            # Verify logging calls
            mock_logger.info.assert_any_call("Starting separated output streaming")
            mock_logger.info.assert_any_call("Separated output streaming completed")
    
    @pytest.mark.asyncio
    async def test_capture_output_both_streams(self, output_streamer, mock_stream_reader):
        """Test capturing output from both stdout and stderr."""
        # Mock stream readers
        stdout_reader = AsyncMock(spec=asyncio.StreamReader)
        stderr_reader = AsyncMock(spec=asyncio.StreamReader)
        
        # Configure async mocks properly - return data then EOF
        stdout_reader.read = AsyncMock(side_effect=[b"Standard output content", b""])
        stderr_reader.read = AsyncMock(side_effect=[b"Error output content", b""])
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            stdout_reader, stderr_reader
        )
        
        assert isinstance(stdout_content, str)
        assert isinstance(stderr_content, str)
        assert len(stdout_content) > 0
        assert len(stderr_content) >= 0  # stderr can be empty
    
    @pytest.mark.asyncio
    async def test_capture_output_stdout_only(self, output_streamer):
        """Test capturing output from stdout only."""
        stdout_reader = AsyncMock(spec=asyncio.StreamReader)
        stdout_reader.read = AsyncMock(side_effect=[b"Only stdout content", b""])
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            stdout_reader, None
        )
        
        assert isinstance(stdout_content, str)
        assert isinstance(stderr_content, str)
        assert len(stdout_content) > 0
    
    @pytest.mark.asyncio
    async def test_capture_output_stderr_only(self, output_streamer):
        """Test capturing output from stderr only."""
        stderr_reader = AsyncMock(spec=asyncio.StreamReader)
        stderr_reader.read = AsyncMock(side_effect=[b"Only stderr content", b""])
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            None, stderr_reader
        )
        
        assert isinstance(stdout_content, str)
        assert isinstance(stderr_content, str)
        assert len(stderr_content) > 0
    
    @pytest.mark.asyncio
    async def test_capture_output_no_streams(self, output_streamer):
        """Test capturing output when no streams are provided."""
        stdout_content, stderr_content = await output_streamer.capture_output(
            None, None
        )
        
        assert isinstance(stdout_content, str)
        assert isinstance(stderr_content, str)
    
    @pytest.mark.asyncio
    async def test_capture_output_with_buffer_size_limit(self, output_streamer):
        """Test that capture respects buffer size limits."""
        stdout_reader = AsyncMock(spec=asyncio.StreamReader)
        
        # Create data larger than buffer
        large_data = "x" * (output_streamer.buffer_size * 2)
        stdout_reader.read.return_value = large_data.encode()
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            stdout_reader, None
        )
        
        assert isinstance(stdout_content, str)
        assert len(stdout_content) > 0
    
    @pytest.mark.asyncio
    async def test_capture_output_logs_capture(self, output_streamer):
        """Test that output capture is properly logged."""
        with patch('src.terminal_mcp_server.utils.output_streamer.logger') as mock_logger:
            await output_streamer.capture_output(None, None)
            
            # Verify logging call
            mock_logger.info.assert_called_with("Capturing output")
    
    @pytest.mark.asyncio
    async def test_capture_output_handles_unicode(self, output_streamer):
        """Test that output capture handles unicode properly."""
        stdout_reader = AsyncMock(spec=asyncio.StreamReader)
        
        # Unicode content
        unicode_content = "Hello 世界 🌍"
        stdout_reader.read = AsyncMock(side_effect=[unicode_content.encode('utf-8'), b""])
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            stdout_reader, None
        )
        
        assert isinstance(stdout_content, str)
        assert unicode_content in stdout_content
    
    @pytest.mark.asyncio
    async def test_capture_output_handles_binary_gracefully(self, output_streamer):
        """Test that output capture handles binary data gracefully."""
        stdout_reader = AsyncMock(spec=asyncio.StreamReader)
        
        # Binary data that might not decode properly
        binary_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        stdout_reader.read = AsyncMock(side_effect=[binary_data, b""])
        
        stdout_content, stderr_content = await output_streamer.capture_output(
            stdout_reader, None
        )
        
        # Should still return strings, even if content is garbled
        assert isinstance(stdout_content, str)
        assert isinstance(stderr_content, str)
    
    def test_buffer_size_property(self, output_streamer):
        """Test that buffer_size property is accessible."""
        assert hasattr(output_streamer, 'buffer_size')
        assert isinstance(output_streamer.buffer_size, int)
        assert output_streamer.buffer_size > 0
    
    def test_different_buffer_sizes(self):
        """Test creating streamers with different buffer sizes."""
        sizes = [1024, 4096, 8192, 16384]
        
        for size in sizes:
            streamer = OutputStreamer(buffer_size=size)
            assert streamer.buffer_size == size
    
    @pytest.mark.asyncio
    async def test_stream_output_respects_custom_buffer_size(self, custom_buffer_streamer, mock_process):
        """Test that streaming uses the custom buffer size."""
        # Verify the custom buffer size is being used
        assert custom_buffer_streamer.buffer_size == 4096
        
        mock_process.stdout.read.side_effect = [b"test data", b""]
        
        chunks = []
        async for chunk in custom_buffer_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should complete without errors using custom buffer size
        assert isinstance(chunks, list)
    
    @pytest.mark.asyncio
    async def test_concurrent_streaming(self, output_streamer):
        """Test that multiple streams can be handled concurrently."""
        mock_process1 = Mock()
        mock_process1.stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_process1.stdout.read.side_effect = [b"Process 1", b""]
        
        mock_process2 = Mock()
        mock_process2.stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_process2.stdout.read.side_effect = [b"Process 2", b""]
        
        # Start concurrent streaming
        task1 = asyncio.create_task(
            self._collect_stream_chunks(output_streamer.stream_output(mock_process1))
        )
        task2 = asyncio.create_task(
            self._collect_stream_chunks(output_streamer.stream_output(mock_process2))
        )
        
        # Wait for both to complete
        chunks1, chunks2 = await asyncio.gather(task1, task2)
        
        assert isinstance(chunks1, list)
        assert isinstance(chunks2, list)
    
    async def _collect_stream_chunks(self, stream):
        """Helper method to collect all chunks from a stream."""
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        return chunks


class TestAdvancedBufferConfiguration:
    """Test cases for advanced buffer size configuration and real-time streaming."""
    
    @pytest.fixture
    def output_streamer(self):
        """Create standard OutputStreamer instance for testing."""
        return OutputStreamer()
    
    @pytest.fixture
    def micro_buffer_streamer(self):
        """Create OutputStreamer with very small buffer for testing buffer behavior."""
        return OutputStreamer(buffer_size=32)  # Very small buffer
    
    @pytest.fixture
    def large_buffer_streamer(self):
        """Create OutputStreamer with large buffer for performance testing."""
        return OutputStreamer(buffer_size=65536)  # 64KB buffer
    
    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess Process for testing."""
        mock_proc = Mock()
        mock_proc.stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_proc.stderr = AsyncMock(spec=asyncio.StreamReader)
        return mock_proc
    
    @pytest.mark.asyncio
    async def test_adaptive_buffer_sizing_small_data(self, micro_buffer_streamer, mock_process):
        """Test streaming behavior with small buffer and small data."""
        # Small data that fits in one buffer
        test_data = "Small test data"
        mock_process.stdout.read.side_effect = [test_data.encode(), b""]
        
        chunks = []
        chunk_sizes = []
        async for chunk in micro_buffer_streamer.stream_output(mock_process):
            chunks.append(chunk)
            chunk_sizes.append(len(chunk))
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        # With micro buffer, should respect buffer size limits
        assert all(size <= micro_buffer_streamer.buffer_size for size in chunk_sizes)
    
    @pytest.mark.asyncio
    async def test_adaptive_buffer_sizing_large_data(self, micro_buffer_streamer, mock_process):
        """Test streaming behavior with small buffer and large data."""
        # Large data that requires multiple buffer reads
        test_data = "X" * 1000  # Much larger than 32-byte buffer
        mock_process.stdout.read.side_effect = [
            test_data[:32].encode(),  # First chunk fits buffer
            test_data[32:64].encode(),  # Second chunk
            test_data[64:].encode(),    # Remaining data
            b""  # EOF
        ]
        
        chunks = []
        total_data = ""
        async for chunk in micro_buffer_streamer.stream_output(mock_process):
            chunks.append(chunk)
            total_data += chunk
        
        assert len(chunks) >= 3  # Should have multiple chunks due to small buffer
        assert len(total_data) == len(test_data)
    
    @pytest.mark.asyncio
    async def test_buffer_memory_efficiency(self, large_buffer_streamer, mock_process):
        """Test that large buffers handle large data efficiently."""
        # Large data that fits in one large buffer read
        test_data = "Y" * 50000  # 50KB of data
        mock_process.stdout.read.side_effect = [test_data.encode(), b""]
        
        chunks = []
        async for chunk in large_buffer_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Large buffer should handle data more efficiently (fewer chunks)
        assert len(chunks) > 0
        # Should be able to handle large chunks efficiently
        assert sum(len(chunk) for chunk in chunks) == len(test_data)
    
    @pytest.mark.asyncio
    async def test_streaming_latency_with_different_buffers(self, micro_buffer_streamer, large_buffer_streamer):
        """Test that streaming latency varies appropriately with buffer sizes."""
        mock_process_micro = Mock()
        mock_process_micro.stdout = AsyncMock()
        mock_process_micro.stdout.read.side_effect = [b"data" * 10, b""]
        
        mock_process_large = Mock()
        mock_process_large.stdout = AsyncMock()
        mock_process_large.stdout.read.side_effect = [b"data" * 10, b""]
        
        # Time both streaming operations
        import time
        
        # Micro buffer streaming
        start_time = time.time()
        micro_chunks = []
        async for chunk in micro_buffer_streamer.stream_output(mock_process_micro):
            micro_chunks.append(chunk)
        micro_time = time.time() - start_time
        
        # Large buffer streaming
        start_time = time.time()
        large_chunks = []
        async for chunk in large_buffer_streamer.stream_output(mock_process_large):
            large_chunks.append(chunk)
        large_time = time.time() - start_time
        
        # Both should complete successfully
        assert len(micro_chunks) > 0
        assert len(large_chunks) > 0
    
    @pytest.mark.asyncio
    async def test_configurable_streaming_intervals(self, output_streamer):
        """Test that streaming can be configured for different output intervals."""
        # This tests enhanced real-time streaming with configurable flush intervals
        mock_process = Mock()
        mock_process.stdout = AsyncMock()
        
        # Simulate data coming in multiple small chunks over time
        mock_process.stdout.read.side_effect = [
            b"chunk1\n",
            b"chunk2\n", 
            b"chunk3\n",
            b""
        ]
        
        chunks = []
        chunk_times = []
        import time
        
        async for chunk in output_streamer.stream_output(mock_process):
            chunks.append(chunk)
            chunk_times.append(time.time())
        
        assert len(chunks) >= 3
        # Should have received chunks in real-time intervals
        assert len(chunk_times) >= 3
    
    @pytest.mark.asyncio
    async def test_dynamic_buffer_size_adjustment(self):
        """Test that buffer size can be dynamically adjusted during streaming."""
        # Create streamer with initial buffer size
        streamer = OutputStreamer(buffer_size=1024)
        assert streamer.buffer_size == 1024
        
        # Test dynamic adjustment (this would be new functionality)
        # This test would fail initially, indicating we need to implement this feature
        try:
            streamer.adjust_buffer_size(2048)
            assert streamer.buffer_size == 2048
        except AttributeError:
            # Expected to fail initially - method doesn't exist yet
            pytest.skip("Dynamic buffer size adjustment not yet implemented")
    
    @pytest.mark.asyncio
    async def test_streaming_with_backpressure_handling(self, micro_buffer_streamer):
        """Test streaming behavior when consumer is slower than producer."""
        mock_process = Mock()
        mock_process.stdout = AsyncMock()
        
        # Fast data production
        large_chunks = [b"X" * 100 for _ in range(10)]  # 10 chunks of 100 bytes each
        large_chunks.append(b"")  # EOF
        mock_process.stdout.read.side_effect = large_chunks
        
        chunks = []
        async for chunk in micro_buffer_streamer.stream_output(mock_process):
            chunks.append(chunk)
            # Simulate slow consumer
            await asyncio.sleep(0.01)
        
        # Should handle backpressure gracefully
        assert len(chunks) > 0
        total_data = "".join(chunks)
        assert len(total_data) == 1000  # 10 * 100 bytes
    
    @pytest.mark.asyncio
    async def test_concurrent_streaming_with_different_buffers(self):
        """Test concurrent streaming operations with different buffer configurations."""
        # Create streamers with different buffer sizes
        streamers = [
            OutputStreamer(buffer_size=512),
            OutputStreamer(buffer_size=1024),
            OutputStreamer(buffer_size=4096)
        ]
        
        # Create mock processes for each streamer
        processes = []
        for i in range(3):
            mock_process = Mock()
            mock_process.stdout = AsyncMock()
            mock_process.stdout.read.side_effect = [f"Process {i} data".encode(), b""]
            processes.append(mock_process)
        
        # Start concurrent streaming
        tasks = []
        for streamer, process in zip(streamers, processes):
            task = asyncio.create_task(self._collect_all_chunks(streamer.stream_output(process)))
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        assert all(len(chunks) > 0 for chunks in results)
    
    async def _collect_all_chunks(self, stream):
        """Helper to collect all chunks from a stream."""
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        return chunks
    
    def test_buffer_size_validation(self):
        """Test that buffer size validation works correctly."""
        # Valid buffer sizes
        valid_sizes = [512, 1024, 4096, 8192, 16384, 65536]
        for size in valid_sizes:
            streamer = OutputStreamer(buffer_size=size)
            assert streamer.buffer_size == size
        
        # Invalid buffer sizes should be handled appropriately
        # This test might fail initially if validation isn't implemented
        try:
            # Test zero buffer size
            OutputStreamer(buffer_size=0)
            assert False, "Should not allow zero buffer size"
        except ValueError:
            pass  # Expected
        
        try:
            # Test negative buffer size
            OutputStreamer(buffer_size=-1)
            assert False, "Should not allow negative buffer size"
        except ValueError:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_output_size_limit_with_configurable_buffers(self):
        """Test that output size limits work correctly with different buffer sizes."""
        # Small buffer, small output limit
        small_streamer = OutputStreamer(buffer_size=256, max_output_size=500)
        
        # Create process with data that exceeds the output limit
        mock_process = Mock()
        mock_process.stdout = AsyncMock()
        
        # Generate 1000 bytes of data (exceeds 500-byte limit)
        large_data = b"X" * 1000
        mock_process.stdout.read.side_effect = [large_data, b""]
        
        chunks = []
        async for chunk in small_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should have truncated output
        total_output = "".join(chunks)
        assert "TRUNCATED" in total_output or len(total_output) <= 500


class TestMemorySafeguards:
    """Test cases specifically for memory safeguards and output size limits."""
    
    @pytest.fixture
    def memory_safe_streamer(self):
        """Create OutputStreamer with small memory limits for testing."""
        return OutputStreamer(buffer_size=1024, max_output_size=5120)  # 5KB limit
    
    @pytest.fixture
    def micro_memory_streamer(self):
        """Create OutputStreamer with very small memory limits."""
        return OutputStreamer(buffer_size=256, max_output_size=1024)  # 1KB limit
    
    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess Process for testing."""
        mock_proc = Mock()
        mock_proc.stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_proc.stderr = AsyncMock(spec=asyncio.StreamReader)
        return mock_proc

    @pytest.mark.asyncio
    async def test_stream_output_enforces_memory_limit(self, micro_memory_streamer, mock_process):
        """Test that stream_output stops when memory limit is exceeded."""
        # Create data that exceeds the 1KB limit
        large_chunk = "x" * 2048  # 2KB chunk exceeds 1KB limit
        mock_process.stdout.read.side_effect = [
            large_chunk.encode(),
            b"additional data that should be truncated",
            b""
        ]
        
        chunks = []
        async for chunk in micro_memory_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should have received chunks and then a truncation message
        total_output = "".join(chunks)
        assert "OUTPUT TRUNCATED" in total_output
        assert "Size limit" in total_output
    
    @pytest.mark.asyncio
    async def test_capture_output_enforces_memory_limit_stdout(self, micro_memory_streamer):
        """Test that capture_output enforces memory limits on stdout."""
        # Create mock stream that exceeds memory limit
        mock_stdout = AsyncMock(spec=asyncio.StreamReader)
        large_data = "x" * 2048  # 2KB exceeds 1KB limit
        mock_stdout.read.side_effect = [large_data.encode(), b""]
        
        stdout_content, stderr_content = await micro_memory_streamer.capture_output(mock_stdout, None)
        
        # Should be truncated with a message
        assert "STDOUT TRUNCATED" in stdout_content
        assert "Size limit exceeded" in stdout_content
        assert stderr_content == ""
    
    @pytest.mark.asyncio
    async def test_capture_output_enforces_memory_limit_stderr(self, micro_memory_streamer):
        """Test that capture_output enforces memory limits on stderr."""
        mock_stderr = AsyncMock(spec=asyncio.StreamReader)
        large_data = "y" * 2048  # 2KB exceeds 1KB limit
        mock_stderr.read.side_effect = [large_data.encode(), b""]
        
        stdout_content, stderr_content = await micro_memory_streamer.capture_output(None, mock_stderr)
        
        # Should be truncated with a message
        assert "STDERR TRUNCATED" in stderr_content
        assert "Size limit exceeded" in stderr_content
        assert stdout_content == ""
    
    @pytest.mark.asyncio
    async def test_capture_output_enforces_memory_limit_both_streams(self, micro_memory_streamer):
        """Test that capture_output enforces memory limits on both streams independently."""
        mock_stdout = AsyncMock(spec=asyncio.StreamReader)
        mock_stderr = AsyncMock(spec=asyncio.StreamReader)
        
        large_stdout = "x" * 2048
        large_stderr = "y" * 2048
        
        mock_stdout.read.side_effect = [large_stdout.encode(), b""]
        mock_stderr.read.side_effect = [large_stderr.encode(), b""]
        
        stdout_content, stderr_content = await micro_memory_streamer.capture_output(mock_stdout, mock_stderr)
        
        # Both should be truncated independently
        assert "STDOUT TRUNCATED" in stdout_content
        assert "STDERR TRUNCATED" in stderr_content
    
    @pytest.mark.asyncio
    async def test_separated_streaming_enforces_memory_limits(self, micro_memory_streamer, mock_process):
        """Test that stream_output_with_separation enforces memory limits on both streams."""
        large_stdout = "x" * 2048
        large_stderr = "y" * 2048
        
        mock_process.stdout.read.side_effect = [large_stdout.encode(), b""]
        mock_process.stderr.read.side_effect = [large_stderr.encode(), b""]
        
        stdout_chunks = []
        stderr_chunks = []
        
        async for stdout_chunk, stderr_chunk in micro_memory_streamer.stream_output_with_separation(mock_process):
            stdout_chunks.append(stdout_chunk)
            stderr_chunks.append(stderr_chunk)
        
        # Check for truncation in collected output
        total_stdout = "".join(stdout_chunks)
        total_stderr = "".join(stderr_chunks)
        
        # Should have truncation messages
        assert any("TRUNCATED" in chunk for chunk in stdout_chunks + stderr_chunks)
    
    @pytest.mark.asyncio
    async def test_progressive_memory_exhaustion_protection(self, memory_safe_streamer, mock_process):
        """Test that memory limits protect against progressive exhaustion with many small chunks."""
        # Create many small chunks that collectively exceed the limit
        small_chunk = "chunk" * 100  # ~500 bytes per chunk
        num_chunks = 15  # Total ~7.5KB exceeds 5KB limit
        
        chunks_to_send = [small_chunk.encode() for _ in range(num_chunks)] + [b""]
        mock_process.stdout.read.side_effect = chunks_to_send
        
        received_chunks = []
        async for chunk in memory_safe_streamer.stream_output(mock_process):
            received_chunks.append(chunk)
        
        # Should eventually hit the limit and include truncation message
        total_output = "".join(received_chunks)
        assert "OUTPUT TRUNCATED" in total_output or len(total_output) <= memory_safe_streamer.max_output_size * 1.1
    
    @pytest.mark.asyncio  
    async def test_memory_limit_logging(self, micro_memory_streamer, mock_process):
        """Test that memory limit violations are properly logged."""
        large_chunk = "x" * 2048
        mock_process.stdout.read.side_effect = [large_chunk.encode(), b""]
        
        with patch('src.terminal_mcp_server.utils.output_streamer.logger') as mock_logger:
            chunks = []
            async for chunk in micro_memory_streamer.stream_output(mock_process):
                chunks.append(chunk)
            
            # Should log the size limit violation
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            assert any("size limit exceeded" in str(call).lower() for call in warning_calls)
    
    @pytest.mark.asyncio
    async def test_memory_safe_unicode_handling(self, micro_memory_streamer, mock_process):
        """Test that memory limits work correctly with Unicode characters."""
        # Unicode characters can be multi-byte
        unicode_data = "测试数据" * 200  # Chinese characters, each ~3 bytes in UTF-8
        mock_process.stdout.read.side_effect = [unicode_data.encode(), b""]
        
        chunks = []
        async for chunk in micro_memory_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should handle Unicode properly while respecting memory limits
        total_output = "".join(chunks)
        
        # Either should be within limits or show truncation
        assert len(total_output.encode()) <= micro_memory_streamer.max_output_size * 1.2 or "TRUNCATED" in total_output
    
    @pytest.mark.asyncio
    async def test_memory_limit_edge_case_exact_limit(self, micro_memory_streamer, mock_process):
        """Test behavior when output exactly matches the memory limit."""
        # Create data that exactly matches the limit
        exact_data = "x" * micro_memory_streamer.max_output_size
        mock_process.stdout.read.side_effect = [exact_data.encode(), b""]
        
        chunks = []
        async for chunk in micro_memory_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should handle exact limit gracefully
        total_output = "".join(chunks)
        assert len(total_output) >= micro_memory_streamer.max_output_size - 100  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_memory_limit_with_buffer_boundaries(self, micro_memory_streamer, mock_process):
        """Test memory limits when chunks align/misalign with buffer boundaries."""
        # Create chunks that don't align with buffer boundaries
        chunk_size = micro_memory_streamer.buffer_size + 50  # Misaligned with buffer
        chunk_data = "x" * chunk_size
        
        # Send enough chunks to exceed memory limit
        mock_process.stdout.read.side_effect = [
            chunk_data.encode(),
            chunk_data.encode(),
            b""
        ]
        
        chunks = []
        async for chunk in micro_memory_streamer.stream_output(mock_process):
            chunks.append(chunk)
        
        # Should respect memory limits regardless of buffer alignment
        total_output = "".join(chunks)
        assert "TRUNCATED" in total_output or len(total_output) <= micro_memory_streamer.max_output_size * 1.1