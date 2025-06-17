"""
Unit tests for VenvManager - Virtual environment detection and management utilities.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import os

from terminal_mcp_server.utils.venv_manager import VenvManager, VirtualEnvironmentInfo


@pytest.fixture
def venv_manager():
    """Create a VenvManager instance for testing."""
    return VenvManager()


class TestVirtualEnvironmentInfo:
    """Test VirtualEnvironmentInfo class."""
    
    def test_venv_info_initialization(self):
        """Test VirtualEnvironmentInfo initialization."""
        venv = VirtualEnvironmentInfo(
            name="my_env",
            path="/path/to/env",
            python_version="3.10.0",
            is_active=True
        )
        
        assert venv.name == "my_env"
        assert venv.path == "/path/to/env"
        assert venv.python_version == "3.10.0"
        assert venv.is_active is True
    
    def test_venv_info_default_active(self):
        """Test VirtualEnvironmentInfo with default is_active value."""
        venv = VirtualEnvironmentInfo(
            name="env",
            path="/path",
            python_version="3.11.0"
        )
        
        assert venv.is_active is False


class TestVenvManager:
    """Test VenvManager class."""
    
    def test_venv_manager_initialization(self, venv_manager):
        """Test VenvManager initialization."""
        assert venv_manager is not None
        assert hasattr(venv_manager, 'list_virtual_environments')
        assert hasattr(venv_manager, 'create_virtual_environment')
        assert hasattr(venv_manager, 'activate_virtual_environment')
        assert hasattr(venv_manager, 'install_package')
    
    @pytest.mark.asyncio
    async def test_list_virtual_environments_basic(self, venv_manager):
        """Test basic virtual environment listing."""
        venvs = await venv_manager.list_virtual_environments()
        
        assert isinstance(venvs, list)
        assert len(venvs) >= 1  # Should at least have system Python
        
        # Check first environment (system default)
        venv = venvs[0]
        assert isinstance(venv, VirtualEnvironmentInfo)
        assert venv.name == "system"
        assert venv.python_version is not None
        assert venv.is_active is True
    
    @pytest.mark.asyncio
    async def test_create_virtual_environment_basic(self, venv_manager):
        """Test basic virtual environment creation."""
        venv_info = await venv_manager.create_virtual_environment("test_env")
        
        assert isinstance(venv_info, VirtualEnvironmentInfo)
        assert venv_info.name == "test_env"
        assert venv_info.path is not None
        assert venv_info.python_version is not None
        assert venv_info.is_active is False
    
    @pytest.mark.asyncio
    async def test_activate_virtual_environment_success(self, venv_manager):
        """Test successful virtual environment activation."""
        result = await venv_manager.activate_virtual_environment("test_env")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_install_package_basic(self, venv_manager):
        """Test basic package installation."""
        result = await venv_manager.install_package("requests")
        
        assert result is True
