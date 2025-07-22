import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Type, Any, ClassVar
from enum import Enum
import hashlib

from efm.cover import CoverImage, embed_cover

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class TaskResult:
    """Base class for task results"""

    key: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":  # type: ignore[misc]
        if data.get("error", False):
            return TaskError(**data)
        else:
            return TaskSuccess(**data)


@dataclass
class TaskSuccess(TaskResult):
    error: bool = False
    messages: list[str] = field(default_factory=list)


@dataclass
class TaskError(TaskResult):
    error: bool = True
    error_message: str = ""
    messages: list[str] = field(default_factory=list)


@dataclass
class Task:
    """Base task class with automatic registry"""

    key: ClassVar[str] = "unknown"
    _registry: ClassVar[dict[str, Type["Task"]]] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        """Automatically register subclasses that have a key"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "key") and cls.key is not None:
            Task._registry[cls.key] = cls

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["key"] = self.__class__.key
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":  # type: ignore[misc]
        """Deserialize a task from a dictionary (JSON data)"""
        key = data.get("key")
        if key not in cls._registry:
            raise ValueError(f"Unknown task type: {key}")

        task_class = cls._registry[key]
        return task_class._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Task":  # type: ignore[misc]
        """Override in subclasses for custom deserialization"""
        return cls(**data)


@dataclass
class TaskSetCover(Task):
    key: ClassVar[str] = "set_cover"
    book_filepath: Path
    cover_tmp_filepath: Path

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["book_filepath"] = str(self.book_filepath)
        data["cover_tmp_filepath"] = str(self.cover_tmp_filepath)
        return data

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "TaskSetCover":  # type: ignore[misc]
        return cls(
            book_filepath=Path(data["book_filepath"]),
            cover_tmp_filepath=Path(data["cover_tmp_filepath"]),
        )


class TasksFile:
    """Manages a JSONL file of tasks"""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def add_task(self, task: Task) -> None:
        """Append a new task to the end of the file."""
        with open(self.filepath, "a") as f:
            f.write(json.dumps(task.to_dict()) + "\n")

    def pop_task(self) -> Optional[Task]:
        """Remove and return the first task from the file."""
        if not self.filepath.exists():
            return None

        lines = self.filepath.read_text().strip().split("\n")
        if not lines or not lines[0]:
            return None

        # Parse first line as task
        try:
            task_data = json.loads(lines[0])
            task = Task.from_dict(task_data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse task from line: {lines[0]}")
            # Remove the corrupted line
            self.filepath.write_text("\n".join(lines[1:]) + "\n" if lines[1:] else "")
            return None

        # Write back remaining lines
        if len(lines) > 1:
            self.filepath.write_text("\n".join(lines[1:]) + "\n")
        else:
            self.filepath.write_text("")

        return task

    def get_task_count(self) -> int:
        """Get the number of pending tasks."""
        if not self.filepath.exists():
            return 0
        lines = self.filepath.read_text().strip().split("\n")
        return len([line for line in lines if line.strip()])


def process_task(task: Task) -> TaskSuccess | TaskError:
    """Process a single task and return result."""
    logger.info(f"Processing task: {task.__class__.key}")

    if isinstance(task, TaskSetCover):
        return handle_set_cover(task)

    # No handler found
    error_msg = f"No handler found for task: {task.__class__.key}"
    logger.warning(error_msg)
    return TaskError(
        key=task.__class__.key or "unknown",
        error_message=error_msg,
        messages=[],
    )


def handle_set_cover(task: TaskSetCover) -> TaskSuccess | TaskError:
    """Set cover image for a specific book file."""

    book_filepath = task.book_filepath
    cover_tmp_filepath = task.cover_tmp_filepath
    messages: list[str] = []
    messages.append(f"Setting cover of {book_filepath} to {cover_tmp_filepath}")

    if not book_filepath.exists():
        return TaskError(
            key=TaskSetCover.key,
            error_message=f"No book file at {book_filepath}",
            messages=messages,
        )

    try:
        if not book_filepath.exists():
            raise FileNotFoundError(f"Book file not found: {book_filepath}")

        if not cover_tmp_filepath.exists():
            raise FileNotFoundError(f"Cover image file not found: {cover_tmp_filepath}")

        # Load and validate cover image
        try:
            cover = CoverImage.from_file(cover_tmp_filepath)
            cover.validate()
        except Exception as e:
            raise ValueError(f"Invalid cover image: {e}")

        # Calculate file hash before modifying (for cache deletion)
        with open(book_filepath, "rb") as f:
            file_hash = hashlib.blake2b(f.read(), digest_size=20).hexdigest()

        # Embed the cover using the appropriate method
        embed_cover(book_filepath, cover)
        messages.append(f"Successfully set cover for {book_filepath}")

        # Delete book metadata cache if it exists
        metadata_cache_path = book_filepath.parent / "_cache" / f"{file_hash}.yaml"
        if metadata_cache_path.exists():
            metadata_cache_path.unlink()
            messages.append("Cleared metadata cache")

        return TaskSuccess(key=TaskSetCover.key, messages=messages)
    except Exception as e:
        return TaskError(key=TaskSetCover.key, error_message=str(e), messages=messages)
