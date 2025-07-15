import pytest
from pathlib import Path
import tempfile
import json
from efm.tasks import TasksFile, Task, TaskStatus, process_task, TaskSuccess, TaskError


def test_add_task():
    """Test adding tasks to JSONL file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        tasks_file = TasksFile(Path(f.name))
        
        # Add some tasks
        task1 = Task("generate_covers")
        task2 = Task("set_cover", "cover.png,book.pdf")
        
        tasks_file.add_task(task1)
        tasks_file.add_task(task2)
        
        # Read file contents
        content = Path(f.name).read_text()
        lines = content.strip().split('\n')
        
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"description": "generate_covers", "parameters": ""}
        assert json.loads(lines[1]) == {"description": "set_cover", "parameters": "cover.png,book.pdf"}
        
        Path(f.name).unlink()


def test_pop_task():
    """Test popping tasks from JSONL file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write some tasks
        f.write('{"description": "task1", "parameters": ""}\n')
        f.write('{"description": "task2", "parameters": "param2"}\n')
        f.write('{"description": "task3", "parameters": "param3"}\n')
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        
        # Pop first task
        task = tasks_file.pop_task()
        assert task is not None
        assert task.description == "task1"
        assert task.parameters == ""
        
        # Check remaining content
        content = Path(f.name).read_text()
        lines = content.strip().split('\n')
        assert len(lines) == 2
        
        # Pop second task
        task = tasks_file.pop_task()
        assert task.description == "task2"
        assert task.parameters == "param2"
        
        # Pop third task
        task = tasks_file.pop_task()
        assert task.description == "task3"
        assert task.parameters == "param3"
        
        # Try to pop from empty file
        task = tasks_file.pop_task()
        assert task is None
        
        Path(f.name).unlink()


def test_pop_task_corrupted_line():
    """Test popping tasks handles corrupted lines."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write some tasks with a corrupted line
        f.write('not valid json\n')
        f.write('{"description": "valid_task", "parameters": ""}\n')
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        
        # Pop should skip corrupted line
        task = tasks_file.pop_task()
        assert task is None  # Corrupted line returns None
        
        # Next pop should get valid task
        task = tasks_file.pop_task()
        assert task is not None
        assert task.description == "valid_task"
        
        Path(f.name).unlink()


def test_get_task_count():
    """Test counting tasks in file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        tasks_file = TasksFile(Path(f.name))
        
        # Empty file
        assert tasks_file.get_task_count() == 0
        
        # Add tasks
        tasks_file.add_task(Task("task1"))
        tasks_file.add_task(Task("task2"))
        tasks_file.add_task(Task("task3"))
        
        assert tasks_file.get_task_count() == 3
        
        # Pop one
        tasks_file.pop_task()
        assert tasks_file.get_task_count() == 2
        
        Path(f.name).unlink()


def test_process_task_with_handler():
    """Test processing a task with a matching handler."""
    task = Task("generate_covers", "")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = process_task(task, Path(tmpdir))
        assert isinstance(result, TaskSuccess)
        assert result.description == "generate_covers"
        assert len(result.messages) > 0


def test_process_task_without_handler():
    """Test processing a task without a matching handler."""
    task = Task("unknown_task", "")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = process_task(task, Path(tmpdir))
        assert isinstance(result, TaskError)
        assert result.description == "unknown_task"
        assert "No handler found" in result.error_message


def test_nonexistent_tasks_file():
    """Test handling of non-existent tasks file."""
    tasks_file = TasksFile(Path("/tmp/nonexistent_tasks.jsonl"))
    assert tasks_file.get_task_count() == 0
    assert tasks_file.pop_task() is None


def test_set_cover_task():
    """Test processing set_cover task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create a test book and cover
        book_path = tmppath / "test_book.pdf"
        book_path.write_bytes(b"PDF content")
        
        cover_path = tmppath / "test_cover.png"
        # Create a simple 1x1 PNG
        from PIL import Image
        img = Image.new('RGB', (1, 1), color='red')
        img.save(cover_path)
        
        # Create task with parameters
        task = Task("set_cover", f"{cover_path},{book_path}")
        
        # Process should succeed
        result = process_task(task, tmppath)
        assert isinstance(result, TaskSuccess)
        assert result.description == "set_cover"
        assert len(result.messages) > 0
        
        # Check that cover was saved
        cache_dir = tmppath / "_cache" / "covers"
        assert cache_dir.exists()
        assert len(list(cache_dir.glob("*.png"))) > 0


def test_set_cover_task_error():
    """Test set_cover task with invalid parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test missing comma
        task = Task("set_cover", "no_comma_here")
        result = process_task(task, Path(tmpdir))
        assert isinstance(result, TaskError)
        assert "must be in format" in result.error_message
        
        # Test missing book file
        task = Task("set_cover", "cover.png,nonexistent_book.pdf")
        result = process_task(task, Path(tmpdir))
        assert isinstance(result, TaskError)
        assert "not found" in result.error_message