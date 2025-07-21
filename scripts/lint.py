#!/usr/bin/env python3
"""Run linting tools for the project."""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from rich.console import Console
from rich.panel import Panel
from rich import box

# Get project root based on script location
script_dir = Path(__file__).parent
project_root = script_dir.parent

usage = """Usage: uv run lint.py [options]

Run linting tools (ruff and basedpyright) on the project.

Options:
  -w, --watch   Watch for file changes and re-run linting
  --fix         Auto-fix linting issues where possible
  -h, --help    Show this help message
"""

console = Console()


class LintHandler(FileSystemEventHandler):
    """Handle file system events for linting."""

    def __init__(self, fix: bool):
        self.fix = fix
        self.last_run = 0
        self.pending = False

    def on_modified(self, event):
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent):
            path = Path(event.src_path)
            if path.suffix == ".py" and not path.name.startswith("."):
                current_time = time.time()
                if current_time - self.last_run > 1:  # Debounce
                    self.pending = True


def run_ruff(fix: bool = False) -> Tuple[int, str]:
    """Run ruff linter."""
    cmd = ["ruff", "check", str(project_root / "efm"), str(project_root / "tests")]
    # Add any .py files in root directory
    root_py_files = list(project_root.glob("*.py"))
    cmd.extend(str(f) for f in root_py_files)

    if fix:
        cmd.append("--fix")

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


def run_ruff_format(fix: bool = False) -> Tuple[int, str]:
    """Run ruff formatter."""
    cmd = ["ruff", "format", str(project_root / "efm"), str(project_root / "tests")]
    # Add any .py files in root directory
    root_py_files = list(project_root.glob("*.py"))
    cmd.extend(str(f) for f in root_py_files)

    if not fix:
        cmd.append("--check")

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


def run_basedpyright() -> Tuple[int, str]:
    """Run basedpyright type checker."""
    cmd = ["basedpyright", str(project_root / "efm"), str(project_root / "tests")]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


def display_results(
    ruff_result: Tuple[int, str],
    format_result: Tuple[int, str],
    pyright_result: Tuple[int, str],
    fix: bool,
) -> int:
    """Display linting results."""
    console.print()
    
    # Header
    if fix:
        console.print("🔍 [bold blue]Linting Results[/bold blue] [italic yellow](--fix mode)[/italic yellow]")
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

    # Basedpyright
    if pyright_result[0] == 0:
        console.print("✅ [green]Basedpyright[/green]: No type errors")
    else:
        console.print("❌ [red]Basedpyright[/red]:")
        if pyright_result[1].strip():
            console.print(Panel(pyright_result[1].strip(), style="yellow", box=box.MINIMAL))

    console.print()
    
    # Return non-zero if any tool failed
    return max(ruff_result[0], format_result[0], pyright_result[0])


def run_lint(fix: bool = False) -> int:
    """Run all linting tools."""
    console.clear()
    with console.status("[bold green]Running linters...", spinner="dots"):
        ruff_result = run_ruff(fix)
        format_result = run_ruff_format(fix)
        pyright_result = run_basedpyright()

    return display_results(ruff_result, format_result, pyright_result, fix)


def watch_mode(fix: bool):
    """Run linting in watch mode."""
    handler = LintHandler(fix)
    observer = Observer()

    # Watch Python files
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
        run_lint(fix)

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
                run_lint(fix)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[bold red]Stopped watching.[/bold red]")
    observer.join()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run linting tools", add_help=False)
    parser.add_argument(
        "-w", "--watch", action="store_true", help="Watch for file changes"
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix linting issues")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    args = parser.parse_args()

    if args.help:
        print(usage)
        return 0

    if args.watch:
        watch_mode(args.fix)
        return 0
    else:
        return run_lint(args.fix)


if __name__ == "__main__":
    sys.exit(main())
