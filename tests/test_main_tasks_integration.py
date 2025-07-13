import pytest
from pathlib import Path
import tempfile
import subprocess
import sys


def test_main_processes_tasks_file():
    """Test that the main function processes tasks.md files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a sample ebook file
        sample_book = tmppath / "test.txt"
        sample_book.write_text("This is a test book")
        
        # Create a tasks.md file
        tasks_file = tmppath / "tasks.md"
        tasks_file.write_text("""| description | parameters | status |
|-------------|------------|--------|
| generate_covers | | |
| validate_formats | | |
""")
        
        # Run efm on the directory
        result = subprocess.run(
            ["uv", "run", "efm", str(tmppath), "--loglevel", "info"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent  # Run from project root
        )
        
        # Check that it processed successfully
        assert result.returncode == 0
        assert "Found tasks file" in result.stderr
        assert "Processing 2 pending tasks" in result.stderr
        assert "Processing task: generate_covers" in result.stderr
        assert "Processing task: validate_formats" in result.stderr
        
        # Check that tasks.md was updated
        updated_content = tasks_file.read_text()
        assert "success" in updated_content
        
        # Check that the sample book was processed
        # Note: It shows "2 files" because it counts tasks.md initially, but then skips it
        assert "Processed 2 files" in result.stdout
        assert "✓ 1 successful" in result.stdout