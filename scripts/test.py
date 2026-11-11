#!/usr/bin/env python3
"""Run tests for the project."""

import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path for efm imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from efm.file_selection import matches_filter

# Get project root based on script location
script_dir = Path(__file__).parent
project_root_dir = script_dir.parent

usage = """Usage: uv run test.py [options] [filters...]

Run pytest tests for the project.

Options:
  -w, --watch   Watch for file changes and re-run tests
  -h, --help    Show this help message
  
Filters:
  Patterns to filter test files (processed in order):
  - Substring match by default: 'metadata' matches any file containing 'metadata'
  - Glob patterns: '*.py', 'test_*.py' (if glob magic chars detected)
  - Regex patterns: '^test_.*\\.py$' (if not glob and valid regex)
  - Negation: prefix with ! or - to exclude: '!test_old', '-integration'
  
Examples:
  uv run test.py                     # Run all tests
  uv run test.py -w                  # Watch mode
  uv run test.py metadata            # Run tests containing 'metadata'
  uv run test.py test_ !test_old     # Test files except old tests
  uv run test.py -w batch            # Watch mode for batch tests
"""

console = Console()


class TestHandler(FileSystemEventHandler):
    """Handle file system events for testing."""

    def __init__(self, test_paths: list[Path]):
        self.test_paths = test_paths
        self.last_run: float = 0
        self.pending = False

    def on_modified(self, event):
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent):
            file = Path(event.src_path)
            # Watch Python files and test files
            if file.suffix == ".py" and not file.name.startswith("."):
                current_time = time.time()
                if current_time - self.last_run > 1:  # Debounce
                    self.pending = True


def get_test_paths(filters: list[str] | None = None) -> list[Path]:
    """Test files matching the filters, or the whole tests dir when unfiltered."""
    test_files: list[Path] = []

    tests_dir = project_root_dir / "tests"
    if tests_dir.exists():
        for dir, _dirnames, filenames in tests_dir.walk():
            for filename in filenames:
                if filename.endswith(".py") and filename.startswith("test_"):
                    test_files.append(dir / filename)

    if filters:
        return sorted(
            file
            for file in test_files
            if all(matches_filter(file, pattern) for pattern in filters)
        )

    if test_files:
        return [tests_dir]
    return []


def run_tests(test_paths: list[Path]) -> int:
    """Run pytest with given test files or dirs."""
    if not test_paths:
        console.print("[yellow]No test files to run[/yellow]")
        return 0

    cmd = ["pytest", *map(str, test_paths), "-v", "--rich"]

    console.clear()
    console.print(Panel.fit(f"🧪 Running: {' '.join(cmd)}", style="bold blue"))

    # Run pytest directly
    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        console.print(Panel.fit("✅ All tests passed!", style="bold green"))
    else:
        console.print(Panel.fit("❌ Tests failed!", style="bold red"))

    return result.returncode


def watch_mode(test_paths: list[Path]):
    """Run tests in watch mode."""
    handler = TestHandler(test_paths)
    observer = Observer()

    # Watch Python source and test files
    for dir_name in ["efm", "tests"]:
        watch_dir = project_root_dir / dir_name
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)

    # Also watch root directory for .py files
    observer.schedule(handler, str(project_root_dir), recursive=False)

    observer.start()

    console.print(
        Panel.fit("👀 Watching for changes... (Ctrl+C to exit)", style="bold yellow")
    )

    try:
        # Initial run
        run_tests(test_paths)

        while True:
            time.sleep(0.5)
            if handler.pending:
                handler.pending = False
                handler.last_run = time.time()
                console.clear()
                console.print(
                    Panel.fit(
                        "🔄 Changes detected, re-running tests...",
                        style="bold blue",
                    )
                )
                run_tests(test_paths)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[bold red]Stopped watching.[/bold red]")
    observer.join()


def main():
    """Main entry point."""
    # Custom argument parsing to handle filters
    watch = False
    show_help = False
    filters = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ["-w", "--watch"]:
            watch = True
        elif arg in ["-h", "--help"]:
            show_help = True
        else:
            # Everything else is a filter
            filters.extend(sys.argv[i:])
            break
        i += 1

    if show_help:
        print(usage)
        return 0

    # Get test files based on filters
    test_paths = get_test_paths(filters if filters else None)

    # Show which files will be tested if filters are provided
    if filters and test_paths:
        console.print(
            f"[dim]Running {len(test_paths)} test files matching filters: {', '.join(filters)}[/dim]\n"
        )

    if watch:
        watch_mode(test_paths)
        return 0
    else:
        return run_tests(test_paths)


if __name__ == "__main__":
    sys.exit(main())
