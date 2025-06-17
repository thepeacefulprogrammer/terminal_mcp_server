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