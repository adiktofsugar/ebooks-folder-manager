# Tasks JSONL Format Guide

The task processing system now uses JSONL (JSON Lines) format instead of markdown tables.

## File Format

Each line in `tasks.jsonl` is a complete JSON object representing one task:

```json
{"description": "task_name", "parameters": "optional_parameters"}
```

## How It Works

1. Tasks are processed from top to bottom (FIFO - First In, First Out)
2. When a task is processed, it's removed from the file
3. New tasks are appended to the end of the file
4. Failed tasks are not retried automatically

## Task Types

### generate_covers
Generate covers for books that don't have them.
```json
{"description": "generate_covers", "parameters": ""}
```

### update_metadata
Update metadata for all books.
```json
{"description": "update_metadata", "parameters": ""}
```

### set_cover
Set a specific cover image for a book.
Parameters format: `cover_source,book_path`
```json
{"description": "set_cover", "parameters": "cover.png,book.pdf"}
{"description": "set_cover", "parameters": "https://example.com/cover.jpg,ebook.epub"}
```

### check_duplicates
Check for duplicate books in the collection.
```json
{"description": "check_duplicates", "parameters": ""}
```

### validate_formats
Validate ebook file formats.
```json
{"description": "validate_formats", "parameters": ""}
```

## Adding Tasks Programmatically

```python
from efm.tasks import TasksFile, Task
from pathlib import Path

tasks_file = TasksFile(Path("tasks.jsonl"))
tasks_file.add_task(Task("generate_covers"))
tasks_file.add_task(Task("set_cover", "mycover.png,mybook.pdf"))
```

## Error Handling

- Failed tasks are logged with error messages
- Corrupted JSON lines are skipped and removed
- Task results include success/error status and messages
- Errors are displayed in the summary output