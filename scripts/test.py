#!/usr/bin/env python3
"""Run tests for the project."""

import subprocess
import sys
import time
from pathlib import Path
from typing import List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from rich.console import Console
from rich.panel import Panel

# Get project root based on script location
script_dir = Path(__file__).parent
project_root = script_dir.parent

usage = """Usage: uv run test.py [options] [pytest_args]

Run pytest tests for the project.

Options:
  -w, --watch   Watch for file changes and re-run tests
  -h, --help    Show this help message
  
Additional arguments are passed directly to pytest.
Examples:
  uv run test.py                     # Run all tests
  uv run test.py -w                  # Watch mode
  uv run test.py -xvs                # Stop on first failure with verbose output
  uv run test.py tests/test_metadata.py  # Run specific test file
"""

console = Console()


class TestHandler(FileSystemEventHandler):
    """Handle file system events for testing."""

    def __init__(self, pytest_args: List[str]):
        self.pytest_args = pytest_args
        self.last_run = 0
        self.pending = False

    def on_modified(self, event):
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent):
            path = Path(event.src_path)
            # Watch Python files and test files
            if path.suffix == ".py" and not path.name.startswith("."):
                current_time = time.time()
                if current_time - self.last_run > 1:  # Debounce
                    self.pending = True


def run_tests(pytest_args: List[str]) -> int:
    """Run pytest with given arguments."""
    cmd = ["pytest"] + pytest_args

    if not any(arg in pytest_args for arg in ["-v", "--verbose", "-q", "--quiet"]):
        # Use pytest-rich for prettier output
        cmd.extend(["--rich"])

    console.clear()
    console.print(Panel.fit(f"🧪 Running: {' '.join(cmd)}", style="bold blue"))

    # Run pytest directly
    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print(Panel.fit("✅ All tests passed!", style="bold green"))
    else:
        console.print(Panel.fit("❌ Tests failed!", style="bold red"))

    return result.returncode


def watch_mode(pytest_args: List[str]):
    """Run tests in watch mode."""
    handler = TestHandler(pytest_args)
    observer = Observer()

    # Watch Python source and test files
    for path_name in ["efm", "tests"]:
        path = project_root / path_name
        if path.exists():
            observer.schedule(handler, str(path), recursive=True)
    
    # Also watch root directory for .py files
    observer.schedule(handler, str(project_root), recursive=False)

    observer.start()

    console.print(
        Panel.fit("👀 Watching for changes... (Ctrl+C to exit)", style="bold yellow")
    )

    try:
        # Initial run
        run_tests(pytest_args)

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
                run_tests(pytest_args)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[bold red]Stopped watching.[/bold red]")
    observer.join()


def main():
    """Main entry point."""
    # Custom argument parsing to handle pytest args
    watch = False
    show_help = False
    pytest_args = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ["-w", "--watch"]:
            watch = True
        elif arg in ["-h", "--help"]:
            show_help = True
        else:
            # Everything else goes to pytest
            pytest_args.extend(sys.argv[i:])
            break
        i += 1

    if show_help:
        print(usage)
        return 0

    # Default pytest args if none provided
    if not pytest_args:
        pytest_args = [str(project_root / "tests"), "-v"]

    if watch:
        watch_mode(pytest_args)
        return 0
    else:
        return run_tests(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
