"""
Unit tests for requirements.txt dependencies.

Tests to ensure all required dependencies for terminal operations are present.
"""

import re
from pathlib import Path
from typing import List


def test_terminal_dependencies_present():
    """Test that all required terminal operation dependencies are in requirements.txt."""
    # Define required dependencies for terminal operations
    required_dependencies = [
        "psutil",    # Process monitoring and management
        "aiofiles",  # Async file operations for process output handling
    ]
    
    # Read requirements.txt
    requirements_path = Path(__file__).parent.parent.parent / "requirements.txt"
    with open(requirements_path, 'r') as f:
        requirements_content = f.read()
    
    # Extract package names from requirements.txt (handle >= version constraints)
    package_pattern = r'^([a-zA-Z0-9\-_]+)'
    packages = []
    for line in requirements_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            match = re.match(package_pattern, line)
            if match:
                packages.append(match.group(1).lower())
    
    # Check that all required dependencies are present
    missing_dependencies = []
    for dep in required_dependencies:
        if dep.lower() not in packages:
            missing_dependencies.append(dep)
    
    assert not missing_dependencies, f"Missing required dependencies: {missing_dependencies}"


def test_requirements_file_exists():
    """Test that requirements.txt file exists."""
    requirements_path = Path(__file__).parent.parent.parent / "requirements.txt"
    assert requirements_path.exists(), "requirements.txt file not found"


def test_requirements_file_readable():
    """Test that requirements.txt file is readable and well-formed."""
    requirements_path = Path(__file__).parent.parent.parent / "requirements.txt"
    
    with open(requirements_path, 'r') as f:
        content = f.read()
    
    # Should not be empty
    assert content.strip(), "requirements.txt should not be empty"
    
    # Should have some package dependencies
    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
    assert len(lines) > 0, "requirements.txt should contain at least one dependency" 