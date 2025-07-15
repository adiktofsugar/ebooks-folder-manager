import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class TaskResult:
    """Base class for task results"""
    description: str
    parameters: str
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        if data.get("error", False):
            return TaskError(**data)
        else:
            return TaskSuccess(**data)


@dataclass
class TaskSuccess(TaskResult):
    """Successful task execution"""
    error: bool = False
    messages: List[str] = field(default_factory=list)


@dataclass 
class TaskError(TaskResult):
    """Failed task execution"""
    error: bool = True
    error_message: str = ""
    messages: List[str] = field(default_factory=list)


@dataclass
class Task:
    """A task to be processed"""
    description: str
    parameters: str = ""
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class TasksFile:
    """Manages a JSONL file of tasks"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        
    def add_task(self, task: Task) -> None:
        """Append a new task to the end of the file."""
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(task.to_dict()) + '\n')
            
    def pop_task(self) -> Optional[Task]:
        """Remove and return the first task from the file."""
        if not self.filepath.exists():
            return None
            
        lines = self.filepath.read_text().strip().split('\n')
        if not lines or not lines[0]:
            return None
            
        # Parse first line as task
        try:
            task_data = json.loads(lines[0])
            task = Task.from_dict(task_data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse task from line: {lines[0]}")
            # Remove the corrupted line
            self.filepath.write_text('\n'.join(lines[1:]) + '\n' if lines[1:] else '')
            return None
            
        # Write back remaining lines
        if len(lines) > 1:
            self.filepath.write_text('\n'.join(lines[1:]) + '\n')
        else:
            self.filepath.write_text('')
            
        return task
        
    def get_task_count(self) -> int:
        """Get the number of pending tasks."""
        if not self.filepath.exists():
            return 0
        lines = self.filepath.read_text().strip().split('\n')
        return len([line for line in lines if line.strip()])


def process_task(task: Task, directory: Path) -> TaskResult:
    """Process a single task and return result."""
    logger.info(f"Processing task: {task.description}")
    messages = []
    
    # Map of task descriptions to processing functions
    task_handlers = {
        "generate_covers": handle_generate_covers,
        "update_metadata": handle_update_metadata,
        "check_duplicates": handle_check_duplicates,
        "validate_formats": handle_validate_formats,
        "set_cover": handle_set_cover,
    }
    
    # Find a matching handler
    for key, handler in task_handlers.items():
        if key in task.description.lower():
            try:
                # Pass task parameters for handlers that need them
                if key == "set_cover":
                    messages = handler(directory, task.parameters)
                else:
                    messages = handler(directory)
                    
                return TaskSuccess(
                    description=task.description,
                    parameters=task.parameters,
                    messages=messages
                )
            except Exception as e:
                error_msg = f"Error processing task '{task.description}': {e}"
                logger.error(error_msg)
                return TaskError(
                    description=task.description,
                    parameters=task.parameters,
                    error_message=str(e),
                    messages=messages
                )
    
    # No handler found
    error_msg = f"No handler found for task: {task.description}"
    logger.warning(error_msg)
    return TaskError(
        description=task.description,
        parameters=task.parameters,
        error_message=error_msg,
        messages=[]
    )


def handle_generate_covers(directory: Path) -> List[str]:
    """Generate covers for books without them."""
    logger.info("Generating covers...")
    # TODO: Implement actual cover generation for books in the directory
    # For now, this is a placeholder that succeeds
    return [f"Would generate covers for books in {directory}"]


def handle_update_metadata(directory: Path) -> List[str]:
    """Update metadata for all books."""
    logger.info("Updating metadata...")
    # Placeholder for metadata update logic
    return ["Metadata update placeholder"]


def handle_check_duplicates(directory: Path) -> List[str]:
    """Check for duplicate books."""
    logger.info("Checking for duplicates...")
    # Placeholder for duplicate checking logic
    return ["Duplicate check placeholder"]


def handle_validate_formats(directory: Path) -> List[str]:
    """Validate ebook formats."""
    logger.info("Validating formats...")
    # Placeholder for format validation logic
    return ["Format validation placeholder"]


def handle_set_cover(directory: Path, parameters: str) -> List[str]:
    """Set cover image for a specific book file.
    
    Parameters format: "cover_path,book_path"
    Where:
    - cover_path can be a relative path, absolute path, or URL
    - book_path is the path to the book file relative to the directory
    """
    messages = []
    messages.append(f"Setting cover with parameters: {parameters}")
    
    if not parameters or "," not in parameters:
        raise ValueError("Parameters must be in format: cover_path,book_path")
    
    parts = parameters.split(",", 1)
    if len(parts) != 2:
        raise ValueError("Parameters must be in format: cover_path,book_path")
    
    cover_source = parts[0].strip()
    book_path_str = parts[1].strip()
    
    if not cover_source or not book_path_str:
        raise ValueError("Both cover path and book path must be provided")
    
    # Resolve book path relative to directory
    book_path = directory / book_path_str
    if not book_path.exists():
        # Try absolute path
        book_path = Path(book_path_str)
        if not book_path.exists():
            raise FileNotFoundError(f"Book file not found: {book_path_str}")
    
    # Import the set_cover_image function
    from efm.metadata import set_cover_image
    
    # Set the cover
    set_cover_image(book_path, cover_source)
    messages.append(f"Successfully set cover for {book_path}")
    
    return messages