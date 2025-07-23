from pathlib import Path
import tempfile
import subprocess


def test_main_processes_tasks_file():
    """Test that the main function processes tasks.md files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a sample ebook file
        sample_book = tmppath / "test.txt"
        sample_book.write_text("This is a test book")
        
        # Create a tasks.jsonl file
        tasks_file = tmppath / "tasks.jsonl"
        tasks_file.write_text("""{"description": "generate_covers", "parameters": ""}
{"description": "validate_formats", "parameters": ""}
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
        
        # Should see task summary in stdout
        assert "Processed 2 tasks" in result.stdout
        
        # Check that tasks.jsonl was processed (should be empty now)
        updated_content = tasks_file.read_text()
        assert updated_content.strip() == ""  # All tasks should be consumed
        
        # Check that the sample book was processed
        # Note: It shows "2 files" because it counts tasks.jsonl initially, but then skips it
        assert "Processed 2 files" in result.stdout
        assert "✓ 1 successful" in result.stdout