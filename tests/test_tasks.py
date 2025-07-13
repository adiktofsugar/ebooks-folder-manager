import pytest
from pathlib import Path
import tempfile
from efm.tasks import TasksFile, Task, TaskStatus, process_task


def test_read_tasks_file():
    """Test reading a tasks.md file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Tasks

| description | parameters | status |
|-------------|------------|--------|
| generate_covers | | |
| update_metadata | | in progress |
| check_duplicates | | success |
| validate_formats | | error |
| set_cover | cover.png,book.pdf | |
""")
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        tasks_file.read()
        
        assert len(tasks_file.tasks) == 5
        
        # Check first task (empty status)
        assert tasks_file.tasks[0].description == "generate_covers"
        assert tasks_file.tasks[0].parameters == ""
        assert tasks_file.tasks[0].status == TaskStatus.PENDING
        
        # Check second task (in progress)
        assert tasks_file.tasks[1].description == "update_metadata"
        assert tasks_file.tasks[1].parameters == ""
        assert tasks_file.tasks[1].status == TaskStatus.IN_PROGRESS
        
        # Check third task (success)
        assert tasks_file.tasks[2].description == "check_duplicates"
        assert tasks_file.tasks[2].parameters == ""
        assert tasks_file.tasks[2].status == TaskStatus.SUCCESS
        
        # Check fourth task (error)
        assert tasks_file.tasks[3].description == "validate_formats"
        assert tasks_file.tasks[3].parameters == ""
        assert tasks_file.tasks[3].status == TaskStatus.ERROR
        
        # Check fifth task (with parameters)
        assert tasks_file.tasks[4].description == "set_cover"
        assert tasks_file.tasks[4].parameters == "cover.png,book.pdf"
        assert tasks_file.tasks[4].status == TaskStatus.PENDING
        
        Path(f.name).unlink()


def test_write_tasks_file():
    """Test writing tasks back to file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        tasks_file = TasksFile(Path(f.name))
        
        # Add some tasks
        tasks_file.tasks = [
            Task("generate_covers", "", TaskStatus.PENDING),
            Task("update_metadata", "", TaskStatus.IN_PROGRESS),
            Task("check_duplicates", "", TaskStatus.SUCCESS),
            Task("set_cover", "cover.png,book.pdf", TaskStatus.PENDING),
        ]
        
        tasks_file.write()
        
        # Read the file back
        content = Path(f.name).read_text()
        
        assert "| description | parameters | status |" in content
        assert "|-------------|------------|--------|" in content
        assert "| generate_covers |  |  |" in content
        assert "| update_metadata |  | in progress |" in content
        assert "| check_duplicates |  | success |" in content
        assert "| set_cover | cover.png,book.pdf |  |" in content
        
        Path(f.name).unlink()


def test_get_pending_tasks():
    """Test getting pending tasks."""
    tasks_file = TasksFile(Path("dummy.md"))
    tasks_file.tasks = [
        Task("task1", "", TaskStatus.PENDING),
        Task("task2", "", TaskStatus.IN_PROGRESS),
        Task("task3", "", TaskStatus.PENDING),
        Task("task4", "", TaskStatus.SUCCESS),
    ]
    
    pending = tasks_file.get_pending_tasks()
    assert len(pending) == 2
    assert pending[0].description == "task1"
    assert pending[1].description == "task3"


def test_update_task_status():
    """Test updating task status."""
    tasks_file = TasksFile(Path("dummy.md"))
    task = Task("test_task", "", TaskStatus.PENDING)
    tasks_file.tasks = [task]
    
    tasks_file.update_task_status(task, TaskStatus.SUCCESS)
    assert task.status == TaskStatus.SUCCESS


def test_process_task_with_handler():
    """Test processing a task with a matching handler."""
    task = Task("generate_covers", "", TaskStatus.PENDING)
    with tempfile.TemporaryDirectory() as tmpdir:
        status = process_task(task, Path(tmpdir))
        # Since the handler is a placeholder, it should succeed
        assert status == TaskStatus.SUCCESS


def test_process_task_without_handler():
    """Test processing a task without a matching handler."""
    task = Task("unknown_task", "", TaskStatus.PENDING)
    with tempfile.TemporaryDirectory() as tmpdir:
        status = process_task(task, Path(tmpdir))
        # Should return error for unknown task
        assert status == TaskStatus.ERROR


def test_nonexistent_tasks_file():
    """Test handling of non-existent tasks file."""
    tasks_file = TasksFile(Path("/tmp/nonexistent_tasks.md"))
    tasks_file.read()
    assert len(tasks_file.tasks) == 0


def test_invalid_table_format():
    """Test handling of invalid table format."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Tasks

This is not a valid table.
""")
        f.flush()
        
        tasks_file = TasksFile(Path(f.name))
        tasks_file.read()
        
        assert len(tasks_file.tasks) == 0
        
        Path(f.name).unlink()



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
        task = Task("set_cover", f"{cover_path},{book_path}", TaskStatus.PENDING)
        
        # Process should succeed
        status = process_task(task, tmppath)
        assert status == TaskStatus.SUCCESS
        
        # Check that cover was saved
        cache_dir = tmppath / "_cache" / "covers"
        assert cache_dir.exists()
        assert len(list(cache_dir.glob("*.png"))) > 0