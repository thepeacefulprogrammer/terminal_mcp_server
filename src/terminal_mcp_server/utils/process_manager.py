"""Background process tracking and management utilities for Terminal MCP Server."""

import asyncio
import logging
import os
import signal
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from ..models.terminal_models import ProcessInfo, ProcessStatus

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages background processes and their lifecycle."""
    
    def __init__(self):
        """Initialize process manager."""
        self.processes: Dict[str, ProcessInfo] = {}
        self._process_handles: Dict[str, asyncio.subprocess.Process] = {}
        self._process_outputs: Dict[str, Dict[str, str]] = {}
        logger.info("ProcessManager initialized")
    
    async def start_process(
        self,
        command: str,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        capture_output: bool = False
    ) -> ProcessInfo:
        """Start a background process."""
        process_id = f"proc_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        # Prepare environment
        env = os.environ.copy() if environment_variables else None
        if environment_variables:
            if env is None:
                env = os.environ.copy()
            env.update(environment_variables)
        
        # Prepare subprocess arguments
        kwargs = {
            'shell': True,
            'preexec_fn': os.setsid if hasattr(os, 'setsid') else None,
        }
        
        if working_directory:
            kwargs['cwd'] = working_directory
            
        if env:
            kwargs['env'] = env
            
        if capture_output:
            kwargs['stdout'] = asyncio.subprocess.PIPE
            kwargs['stderr'] = asyncio.subprocess.PIPE
        
        try:
            # Start the subprocess
            process = await asyncio.create_subprocess_shell(command, **kwargs)
            
            # Create process info
            process_info = ProcessInfo(
                pid=process.pid,
                process_id=process_id,
                command=command,
                status=ProcessStatus.RUNNING,
                started_at=datetime.now(),
                working_directory=working_directory,
                environment_variables=environment_variables or {}
            )
            
            # Track the process
            self.processes[process_id] = process_info
            self._process_handles[process_id] = process
            
            # Initialize output storage if capturing
            if capture_output:
                self._process_outputs[process_id] = {"stdout": "", "stderr": ""}
                # Start background tasks to capture output
                asyncio.create_task(self._capture_output(process_id, process))
            
            logger.info(f"Started process {process_id}: {command} (PID: {process.pid})")
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to start process {process_id}: {e}")
            raise
    
    async def _capture_output(self, process_id: str, process: asyncio.subprocess.Process):
        """Capture output from a background process."""
        try:
            stdout, stderr = await process.communicate()
            if process_id in self._process_outputs:
                self._process_outputs[process_id]["stdout"] = stdout.decode('utf-8', errors='ignore')
                self._process_outputs[process_id]["stderr"] = stderr.decode('utf-8', errors='ignore')
                
            # Update process status
            if process_id in self.processes:
                if process.returncode == 0:
                    self.processes[process_id].status = ProcessStatus.COMPLETED
                else:
                    self.processes[process_id].status = ProcessStatus.FAILED
                    
        except Exception as e:
            logger.error(f"Error capturing output for process {process_id}: {e}")
    
    async def list_processes(self) -> List[ProcessInfo]:
        """List all tracked processes."""
        await self._update_process_statuses()
        return list(self.processes.values())
    
    async def get_process_status(self, process_id: str) -> ProcessInfo:
        """Get process status by ID."""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not found")
        
        await self._update_process_status(process_id)
        return self.processes[process_id]
    
    async def kill_process(self, process_id: str) -> bool:
        """Kill a process by ID."""
        if process_id not in self.processes:
            return False
        
        process_handle = self._process_handles.get(process_id)
        if not process_handle:
            return False
        
        try:
            # Try to kill the process group
            if hasattr(os, 'killpg') and process_handle.pid:
                try:
                    os.killpg(os.getpgid(process_handle.pid), signal.SIGTERM)
                    # Give process time to terminate gracefully
                    await asyncio.sleep(0.1)
                    
                    # Force kill if still running
                    if process_handle.returncode is None:
                        os.killpg(os.getpgid(process_handle.pid), signal.SIGKILL)
                        
                except (ProcessLookupError, OSError):
                    # Process might already be dead
                    pass
            
            # Update status
            self.processes[process_id].status = ProcessStatus.KILLED
            logger.info(f"Killed process {process_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error killing process {process_id}: {e}")
            return False
    
    async def restart_process(self, process_id: str) -> ProcessInfo:
        """Restart a process by its ID."""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not found")
        
        original_process = self.processes[process_id]
        
        # Kill the old process if still running
        if original_process.status == ProcessStatus.RUNNING:
            await self.kill_process(process_id)
        
        # Start a new process with the same parameters
        new_process = await self.start_process(
            command=original_process.command,
            working_directory=original_process.working_directory,
            environment_variables=original_process.environment_variables
        )
        
        logger.info(f"Restarted process {process_id} as {new_process.process_id}")
        return new_process
    
    async def get_process_output(self, process_id: str) -> Dict[str, str]:
        """Get captured output from a process."""
        if process_id not in self._process_outputs:
            raise ValueError(f"No output captured for process {process_id}")
        
        return self._process_outputs[process_id].copy()
    
    async def update_process_status(self, process_id: str):
        """Update the status of a specific process."""
        await self._update_process_status(process_id)
    
    async def _update_process_status(self, process_id: str):
        """Internal method to update process status."""
        if process_id not in self.processes:
            return
        
        # Don't update status if process was manually killed
        if self.processes[process_id].status == ProcessStatus.KILLED:
            return
        
        process_handle = self._process_handles.get(process_id)
        if not process_handle:
            return
        
        # Check if process is still running
        if process_handle.returncode is not None:
            if process_handle.returncode == 0:
                self.processes[process_id].status = ProcessStatus.COMPLETED
            else:
                self.processes[process_id].status = ProcessStatus.FAILED
        elif process_handle.pid:
            try:
                # Check if process is still alive
                os.kill(process_handle.pid, 0)
                # Process is still running
                self.processes[process_id].status = ProcessStatus.RUNNING
            except (ProcessLookupError, OSError):
                # Process is dead
                self.processes[process_id].status = ProcessStatus.FAILED
    
    async def _update_process_statuses(self):
        """Update statuses for all tracked processes."""
        for process_id in list(self.processes.keys()):
            await self._update_process_status(process_id)
    
    async def cleanup_completed_processes(self, max_age_hours: int = 24):
        """Clean up old completed/failed processes."""
        now = datetime.now()
        to_remove = []
        
        for process_id, process_info in self.processes.items():
            if process_info.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.KILLED]:
                age = (now - process_info.started_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(process_id)
        
        for process_id in to_remove:
            self._cleanup_process(process_id)
            logger.info(f"Cleaned up old process {process_id}")
    
    def _cleanup_process(self, process_id: str):
        """Clean up resources for a process."""
        self.processes.pop(process_id, None)
        self._process_handles.pop(process_id, None)
        self._process_outputs.pop(process_id, None)
    
    async def shutdown(self):
        """Shutdown process manager and clean up all processes."""
        logger.info("Shutting down ProcessManager")
        
        # Kill all running processes
        running_processes = [
            process_id for process_id, process_info in self.processes.items()
            if process_info.status == ProcessStatus.RUNNING
        ]
        
        for process_id in running_processes:
            await self.kill_process(process_id)
        
        # Clear all tracking data
        self.processes.clear()
        self._process_handles.clear()
        self._process_outputs.clear()
        
        logger.info("ProcessManager shutdown complete") 