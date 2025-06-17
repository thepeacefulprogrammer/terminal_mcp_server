"""Data models for Terminal MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ProcessStatus(str, Enum):
    """Status of a background process."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    UNKNOWN = "unknown"


class CommandRequest(BaseModel):
    """Request model for command execution."""
    command: str = Field(..., description="Command to execute")
    working_directory: Optional[str] = Field(None, description="Working directory")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    capture_output: bool = Field(True, description="Whether to capture output")


class CommandResult(BaseModel):
    """Result model for command execution."""
    command: str = Field(..., description="Command that was executed")
    exit_code: int = Field(..., description="Command exit code")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    execution_time: float = Field(..., description="Execution time in seconds")
    started_at: datetime = Field(..., description="When command started")
    completed_at: datetime = Field(..., description="When command completed")
    captured_chunks: Optional[List[str]] = Field(default=None, description="Captured streaming output chunks")


class ProcessInfo(BaseModel):
    """Information about a background process."""
    pid: int = Field(..., description="Process ID")
    process_id: str = Field(..., description="Internal process identifier")
    command: str = Field(..., description="Command being executed")
    status: ProcessStatus = Field(..., description="Current process status")
    started_at: datetime = Field(..., description="When process started")
    working_directory: Optional[str] = Field(None, description="Working directory")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables") 