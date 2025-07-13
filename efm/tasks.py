import logging
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = ""
    IN_PROGRESS = "in progress"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class Task:
    description: str
    status: TaskStatus

    def to_table_row(self) -> str:
        status_str = self.status.value if self.status != TaskStatus.PENDING else ""
        return f"| {self.description} | {status_str} |"


class TasksFile:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.tasks: list[Task] = []

    def read(self) -> None:
        """Read tasks from the markdown file."""
        if not self.filepath.exists():
            logger.debug(f"Tasks file {self.filepath} does not exist")
            return

        content = self.filepath.read_text()
        lines = content.strip().split("\n")

        # Find the table start (header row)
        table_start = -1
        for i, line in enumerate(lines):
            if (
                "|" in line
                and "description" in line.lower()
                and "status" in line.lower()
            ):
                table_start = i
                break

        if table_start == -1:
            logger.warning(f"No valid table header found in {self.filepath}")
            return

        # Skip the header and separator rows
        for i in range(table_start + 2, len(lines)):
            line = lines[i].strip()
            if not line or not line.startswith("|"):
                continue

            # Parse the table row
            parts = [
                p.strip() for p in line.split("|")[1:-1]
            ]  # Skip empty first/last elements
            if len(parts) >= 2:
                description = parts[0]
                status_str = parts[1].lower()

                # Map status string to enum
                if status_str == "in progress":
                    status = TaskStatus.IN_PROGRESS
                elif status_str == "success":
                    status = TaskStatus.SUCCESS
                elif status_str == "error":
                    status = TaskStatus.ERROR
                else:
                    status = TaskStatus.PENDING

                self.tasks.append(Task(description, status))

    def write(self) -> None:
        """Write tasks back to the markdown file."""
        lines = ["| description | status |", "|-------------|--------|"]
        for task in self.tasks:
            lines.append(task.to_table_row())

        self.filepath.write_text("\n".join(lines) + "\n")

    def get_pending_tasks(self) -> list[Task]:
        """Get all tasks with empty status."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def update_task_status(self, task: Task, status: TaskStatus) -> None:
        """Update the status of a task."""
        task.status = status


def process_task(task: Task, directory: Path) -> TaskStatus:
    """Process a single task based on its description."""
    logger.info(f"Processing task: {task.description}")

    # Map of task descriptions to processing functions
    task_handlers = {
        "generate_covers": handle_generate_covers,
        "update_metadata": handle_update_metadata,
        "check_duplicates": handle_check_duplicates,
        "validate_formats": handle_validate_formats,
    }

    # Find a matching handler
    for key, handler in task_handlers.items():
        if key in task.description.lower():
            try:
                handler(directory)
                return TaskStatus.SUCCESS
            except Exception as e:
                logger.error(f"Error processing task '{task.description}': {e}")
                return TaskStatus.ERROR

    logger.warning(f"No handler found for task: {task.description}")
    return TaskStatus.ERROR


def handle_generate_covers(directory: Path) -> None:
    """Generate covers for books without them."""
    logger.info("Generating covers...")
    # TODO: Implement actual cover generation for books in the directory
    # For now, this is a placeholder that succeeds
    logger.info(f"Would generate covers for books in {directory}")


def handle_update_metadata(directory: Path) -> None:
    """Update metadata for all books."""
    logger.info("Updating metadata...")
    # Placeholder for metadata update logic


def handle_check_duplicates(directory: Path) -> None:
    """Check for duplicate books."""
    logger.info("Checking for duplicates...")
    # Placeholder for duplicate checking logic


def handle_validate_formats(directory: Path) -> None:
    """Validate ebook formats."""
    logger.info("Validating formats...")
    # Placeholder for format validation logic
