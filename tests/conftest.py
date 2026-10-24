"""
This file contains shared fixtures and configuration for pytest.
Fixtures defined here are automatically available to all test files.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest

# Add the project root directory to the Python path
# This ensures imports work correctly in test files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Define any shared fixtures here that might be used across multiple test files
@pytest.fixture
def project_root():
    """Return the project root directory path"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests out of the real ~/.cache and ~/.local/share."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.delenv("EFM_STORE", raising=False)
    return tmp_path


@pytest.fixture
def sample_books(tmp_path: Path) -> Path:
    """A writable copy of sample-books/."""
    src = Path(__file__).parent.parent / "sample-books"
    dst = tmp_path / "books"
    shutil.copytree(src, dst)
    return dst
