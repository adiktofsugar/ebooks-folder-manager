"""
This file contains shared fixtures and configuration for pytest.
Fixtures defined here are automatically available to all test files.
"""

import os
import pytest
import sys

# Add the project root directory to the Python path
# This ensures imports work correctly in test files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Define any shared fixtures here that might be used across multiple test files
@pytest.fixture
def project_root():
    """Return the project root directory path"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
