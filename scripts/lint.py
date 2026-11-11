#!/usr/bin/env python3
"""Run linting tools for the project."""

import argparse
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.events import DirModifiedEvent, FileModifiedEvent

# Add script directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # For efm imports

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from efm.file_selection import matches_filter

# Get project root based on script location
script_dir = Path(__file__).parent
project_root_dir = script_dir.parent

usage = """Usage: uv run lint.py [options] [filters...]

Run linting tools (ruff and ty) on the project.

Options:
  -w, --watch   Watch for file changes and re-run linting
  --fix         Auto-fix linting issues where possible
  -h, --help    Show this help message

Filters:
  Patterns to filter files (processed in order):
  - Substring match by default: 'metadata' matches any file containing 'metadata'
  - Glob patterns: '*.py', 'test_*.py' (if glob magic chars detected)
  - Regex patterns: '^test_.*.py$' (if not glob and valid regex)
  - Negation: prefix with ! or - to exclude: '!test_', '-old'

Examples:
  uv run lint.py                    # Lint entire project
  uv run lint.py metadata           # Files containing 'metadata'
  uv run lint.py test_ !test_old    # Test files except old tests
  uv run lint.py --fix action       # Auto-fix files containing 'action'
"""

console = Console(force_terminal=True)


class LintHandler(FileSystemEventHandler):
    """Handle file system events for linting."""

    def __init__(self, fix: bool, filters: list[str] | None = None):
        self.fix: bool = fix
        self.filters: list[str] | None = filters
        self.last_run: float = 0
        self.pending: bool = False

    def on_modified(self, event: "DirModifiedEvent | FileModifiedEvent") -> None:  # type: ignore[override]
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent):
            file = Path(str(event.src_path))
            if file.suffix == ".py" and not file.name.startswith("."):
                current_time = time.time()
                if current_time - self.last_run > 1:  # Debounce
                    self.pending = True


def get_python_filepaths(filters: list[str] | None = None) -> list[str]:
    """Get all Python files, optionally filtered by patterns."""
    python_files: list[Path] = []

    for dir_name in ["efm", "tests", "scripts"]:
        source_dir = project_root_dir / dir_name
        if source_dir.exists():
            for dir, _dirnames, filenames in source_dir.walk():
                for filename in filenames:
                    if filename.endswith(".py"):
                        python_files.append(dir / filename)

    # Add any .py files in root directory
    python_files.extend(
        file for file in project_root_dir.glob("*.py") if file.is_file()
    )

    if filters:
        python_files = [
            file
            for file in python_files
            if all(matches_filter(file, pattern) for pattern in filters)
        ]
    return sorted(str(file) for file in python_files)


def run_tool(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout + result.stderr


def run_ruff(filepaths: list[str], fix: bool = False) -> tuple[int, str]:
    """Run ruff linter."""
    if not filepaths:
        return 0, "No files to lint"
    return run_tool(["ruff", "check", *filepaths, *(["--fix"] if fix else [])])


def run_ruff_format(filepaths: list[str], fix: bool = False) -> tuple[int, str]:
    """Run ruff formatter."""
    if not filepaths:
        return 0, "No files to format"
    return run_tool(["ruff", "format", *filepaths, *([] if fix else ["--check"])])


def run_ty(filepaths: list[str], fix: bool = False) -> tuple[int, str]:
    """Run ty type checker. Rules are in pyproject.toml's [tool.ty]."""
    if not filepaths:
        return 0, "No files to type check"
    return run_tool(
        [
            "ty",
            "check",
            "--color",
            "always",
            "--no-progress",
            *filepaths,
            *(["--fix"] if fix else []),
        ]
    )


def display_results(
    ruff_result: tuple[int, str],
    format_result: tuple[int, str],
    ty_result: tuple[int, str],
    fix: bool,
) -> int:
    """Display linting results."""
    console.print()

    # Header
    if fix:
        console.print(
            "🔍 [bold blue]Linting Results[/bold blue] [italic yellow](--fix mode)[/italic yellow]"
        )
    else:
        console.print("🔍 [bold blue]Linting Results[/bold blue]")
    console.print()

    # Ruff check
    if ruff_result[0] == 0:
        console.print("✅ [green]Ruff Check[/green]: All checks passed!")
    else:
        console.print("❌ [red]Ruff Check[/red]:")
        if ruff_result[1].strip():
            console.print(Panel(ruff_result[1].strip(), style="red", box=box.MINIMAL))

    # Ruff format
    if format_result[0] == 0:
        if fix and format_result[1].strip():
            console.print("✅ [green]Ruff Format[/green]: Files formatted")
        else:
            console.print("✅ [green]Ruff Format[/green]: No formatting issues")
    else:
        console.print("❌ [red]Ruff Format[/red]:")
        if format_result[1].strip():
            console.print(Panel(format_result[1].strip(), style="red", box=box.MINIMAL))

    # ty. Its output is already formatted with code snippets; from_ansi so rich keeps its colors
    # and doesn't read `[rule-name]` as markup.
    if ty_result[0] == 0:
        console.print("✅ [green]ty[/green]: No type errors")
    else:
        console.print("❌ [red]ty[/red]:")
    if ty_result[1].strip() and "All checks passed" not in ty_result[1]:
        console.print(Text.from_ansi(ty_result[1].strip()))

    console.print()

    # Return non-zero if any tool failed
    return max(ruff_result[0], format_result[0], ty_result[0])


def run_lint(fix: bool = False, filters: list[str] | None = None) -> int:
    """Run all linting tools."""
    console.clear()

    filepaths = get_python_filepaths(filters)

    # Show which files will be linted if filters are provided
    if filters:
        if filepaths:
            console.print(
                f"[dim]Linting {len(filepaths)} files matching filters: {', '.join(filters)}[/dim]\n"
            )
        else:
            console.print(
                f"[yellow]No files found matching filters: {', '.join(filters)}[/yellow]"
            )
            return 0

    with console.status("[bold green]Running linters...", spinner="dots"):
        ruff_result = run_ruff(filepaths, fix)
        format_result = run_ruff_format(filepaths, fix)
        ty_result = run_ty(filepaths, fix)

    return display_results(ruff_result, format_result, ty_result, fix)


def watch_mode(fix: bool, filters: list[str] | None = None):
    """Run linting in watch mode."""
    handler = LintHandler(fix, filters)
    observer = Observer()

    for dir_name in ["efm", "tests", "scripts"]:
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
        run_lint(fix, filters)

        while True:
            time.sleep(0.5)
            if handler.pending:
                handler.pending = False
                handler.last_run = time.time()
                console.clear()
                console.print(
                    Panel.fit(
                        "🔄 Changes detected, re-running linters...",
                        style="bold blue",
                    )
                )
                run_lint(fix, filters)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[bold red]Stopped watching.[/bold red]")
    observer.join()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run linting tools", add_help=False)
    parser.add_argument(
        "-w", "--watch", action="store_true", help="Watch for file changes"
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix linting issues")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")
    parser.add_argument("filters", nargs="*", help="Patterns to filter files")

    args: Namespace = parser.parse_args()

    help_flag: bool = args.help  # type: ignore[assignment]
    if help_flag:
        print(usage)
        return 0

    watch_flag: bool = args.watch  # type: ignore[assignment]
    fix_flag: bool = args.fix  # type: ignore[assignment]
    filters: list[str] = args.filters  # type: ignore[assignment]

    if watch_flag:
        watch_mode(fix_flag, filters if filters else None)
        return 0
    else:
        return run_lint(fix_flag, filters if filters else None)


if __name__ == "__main__":
    sys.exit(main())
