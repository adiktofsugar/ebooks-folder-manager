"""
This file contains shared fixtures and configuration for pytest.
Fixtures defined here are automatically available to all test files.
"""

import os
import pytest
import sys
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from efm.transaction import TransactionResult


# Add the project root directory to the Python path
# This ensures imports work correctly in test files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Define any shared fixtures here that might be used across multiple test files
@pytest.fixture
def project_root():
    """Return the project root directory path"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def sanitize_string(msg: str, temp_dirs=None) -> str:
    """Sanitize a string for consistent test snapshots.
    
    Replaces:
    - Timestamps (YYYY-MM-DD HH:MM:SS,mmm format)
    - Temporary directories (/tmp/...)
    - 40-character hex hashes
    - Backslashes with forward slashes
    
    Args:
        msg: The message to sanitize
        temp_dirs: Optional dict mapping temp directory paths to their replacements.
                   Paths are replaced from longest to shortest to handle nested paths correctly.
                   After custom replacements, the default /tmp/... pattern is applied.
    """
    # Regex patterns
    timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}')
    default_temp_dir_pattern = re.compile(r'/tmp/[a-zA-Z0-9_\-]+')
    hash_pattern = re.compile(r'[a-f0-9]{40}')  # 40-char hex hash
    
    # Replace timestamps
    msg = timestamp_pattern.sub('<TIMESTAMP>', msg)
    
    # Normalize path separators
    msg = msg.replace("\\", "/")
    
    # Replace custom temp directories from longest to shortest
    if temp_dirs:
        # Sort by length (longest first) to handle nested paths correctly
        sorted_paths = sorted(temp_dirs.keys(), key=len, reverse=True)
        for path in sorted_paths:
            replacement = temp_dirs[path]
            msg = msg.replace(path, replacement)
    
    # Apply default temp directory pattern
    msg = default_temp_dir_pattern.sub('/tmp/TEMP_DIR', msg)
    
    # Replace hashes in messages (e.g., in cache filenames)
    msg = hash_pattern.sub('HASH_PLACEHOLDER', msg)
    
    return msg


def sanitize_transaction(result:"TransactionResult", test_env=None):
    """Sanitize a TransactionResult (Success or Error) for consistent snapshots.
    
    Args:
        result: The TransactionSuccess or TransactionError to sanitize
        test_env: The test environment dictionary with keys that map to paths
    """
    
    # Build temp_dirs mapping for sanitize_string
    temp_dirs = {}
    if test_env:
        # Convert any Path values to "KEY_DIR" format
        for key, value in test_env.items():
            if isinstance(value, Path):
                temp_dirs[str(value)] = f"/{key.upper()}_DIR"
    
    # Convert to dict for easier manipulation
    result_dict = result.to_dict()
    
    # Sanitize paths
    if "original_filepath" in result_dict:
        path_str = str(result_dict["original_filepath"]).replace("\\", "/")
        if temp_dirs:
            sorted_paths = sorted(temp_dirs.keys(), key=len, reverse=True)
            for path in sorted_paths:
                path_str = path_str.replace(path, temp_dirs[path])
        # Replace test UUID in path
        path_str = re.sub(r'/test_[a-f0-9]+/', '/test_UUID/', path_str)
        result_dict["original_filepath"] = path_str
    
    if "original_filename" in result_dict:
        result_dict["original_filename"] = sanitize_string(str(result_dict["original_filename"]), temp_dirs)
    
    # Sanitize messages
    if "messages" in result_dict:
        result_dict["messages"] = [sanitize_string(msg, temp_dirs) for msg in result_dict["messages"]]
    
    # Sanitize error message
    if "error_message" in result_dict:
        result_dict["error_message"] = sanitize_string(result_dict["error_message"], temp_dirs)
    
    # Replace hash with placeholder
    if "hash" in result_dict:
        result_dict["hash"] = "HASH_PLACEHOLDER"
    
    # Remove traceback for consistency
    if "traceback" in result_dict:
        result_dict["traceback"] = "<TRACEBACK_REMOVED>"
    
    # Normalize filename paths
    if "filename" in result_dict and result_dict["filename"]:
        result_dict["filename"] = str(result_dict["filename"]).replace("\\", "/")
    
    # Sanitize temp_directory
    if "temp_directory" in result_dict and result_dict["temp_directory"]:
        result_dict["temp_directory"] = sanitize_string(str(result_dict["temp_directory"]), temp_dirs)
    
    return result_dict
