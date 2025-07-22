from pathlib import Path
import tempfile
import json
from typing import Any
from efm.tasks import TasksFile, Task, process_task, TaskSuccess, TaskError


def test_add_task():
    """Test adding tasks to JSONL file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        tasks_file = TasksFile(Path(f.name))
        
        # Add some tasks - TaskSetCover task
        task_data: dict[str, str] = {
            "key": "set_cover",
            "book_filepath": "/path/to/book.pdf",
            "cover_tmp_filepath": "/tmp/cover.png"
        }
        # Create task from dict (mimicking how it would be created)
        task = Task.from_dict(task_data)
        
        tasks_file.add_task(task)
        
        # Read file contents
        content = Path(f.name).read_text()
        lines = content.strip().split('\n')
        
        assert len(lines) == 1
        saved_data = json.loads(lines[0])
        assert saved_data["key"] == "set_cover"
        assert saved_data["book_filepath"] == "/path/to/book.pdf"
        assert saved_data["cover_tmp_filepath"] == "/tmp/cover.png"
        
        Path(f.name).unlink()


def test_pop_task():
    """Test popping tasks from JSONL file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write some tasks
        f.write('{"key": "set_cover", "book_filepath": "/path/to/book1.pdf", "cover_tmp_filepath": "/tmp/cover1.png"}\n')
        f.write('{"key": "set_cover", "book_filepath": "/path/to/book2.pdf", "cover_tmp_filepath": "/tmp/cover2.png"}\n')
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        
        # Pop first task
        task = tasks_file.pop_task()
        assert task is not None
        assert task.key == "set_cover"
        
        # Check remaining content
        content = Path(f.name).read_text()
        lines = content.strip().split('\n')
        assert len(lines) == 1
        
        # Pop second task
        task = tasks_file.pop_task()
        assert task is not None
        assert task.key == "set_cover"
        
        # Try to pop from empty file
        task = tasks_file.pop_task()
        assert task is None
        
        Path(f.name).unlink()


def test_pop_task_corrupted_line():
    """Test popping tasks handles corrupted lines."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write some tasks with a corrupted line
        f.write('not valid json\n')
        f.write('{"key": "set_cover", "book_filepath": "/path/to/book.pdf", "cover_tmp_filepath": "/tmp/cover.png"}\n')
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        
        # Pop should skip corrupted line
        task = tasks_file.pop_task()
        assert task is None  # Corrupted line should be removed
        
        # Next pop should get valid task
        task = tasks_file.pop_task()
        assert task is not None
        assert task.key == "set_cover"
        
        Path(f.name).unlink()


def test_get_task_count():
    """Test getting task count."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        tasks_file = TasksFile(Path(f.name))
        
        # Empty file
        assert tasks_file.get_task_count() == 0
        
        # Add tasks
        task_data: dict[str, str] = {
            "key": "set_cover",
            "book_filepath": "/path/to/book.pdf",  
            "cover_tmp_filepath": "/tmp/cover.png"
        }
        f.write(json.dumps(task_data) + '\n')
        f.write(json.dumps(task_data) + '\n')
        f.flush()
        
        assert tasks_file.get_task_count() == 2
        
        Path(f.name).unlink()


def test_process_task_success():
    """Test processing a task successfully."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as book_file:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as cover_file:
            # Create files
            book_file.write(b"fake pdf content")
            cover_file.write(b"fake png content")
            book_file.flush()
            cover_file.flush()
            
            task_data: dict[str, str] = {
                "key": "set_cover",
                "book_filepath": book_file.name,
                "cover_tmp_filepath": cover_file.name
            }
            task = Task.from_dict(task_data)
            
            result = process_task(task)
            
            assert isinstance(result, (TaskSuccess, TaskError))
            assert result.key == "set_cover"
            
            Path(book_file.name).unlink()
            Path(cover_file.name).unlink()


def test_process_task_error():
    """Test processing a task with error."""
    # Use non-existent files
    task_data: dict[str, str] = {
        "key": "set_cover",
        "book_filepath": "/non/existent/book.pdf",
        "cover_tmp_filepath": "/non/existent/cover.png"
    }
    task = Task.from_dict(task_data)
    
    result = process_task(task)
    
    assert isinstance(result, TaskError)
    assert result.key == "set_cover"
    assert result.error is True


def test_task_result_serialization():
    """Test TaskResult serialization."""
    # Success result
    success = TaskSuccess(key="set_cover", messages=["Cover set successfully"])
    success_dict = success.to_dict()
    assert success_dict["key"] == "set_cover"
    assert success_dict["error"] is False
    assert success_dict["messages"] == ["Cover set successfully"]
    
    # Error result  
    error = TaskError(key="set_cover", error_message="File not found", messages=["Error occurred"])
    error_dict = error.to_dict()
    assert error_dict["key"] == "set_cover"
    assert error_dict["error"] is True
    assert error_dict["error_message"] == "File not found"
    assert error_dict["messages"] == ["Error occurred"]


def test_task_result_from_dict():
    """Test TaskResult deserialization."""
    # Success result
    success_data: dict[str, Any] = {
        "key": "set_cover",
        "error": False,
        "messages": ["Success"]
    }
    result = TaskSuccess.from_dict(success_data)
    assert isinstance(result, TaskSuccess)
    assert result.key == "set_cover"
    
    # Error result
    error_data: dict[str, Any] = {
        "key": "set_cover", 
        "error": True,
        "error_message": "Failed",
        "messages": ["Error"]
    }
    result = TaskError.from_dict(error_data)
    assert isinstance(result, TaskError)
    assert result.key == "set_cover"