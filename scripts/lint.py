#!/usr/bin/env python3
"""Run linting tools for the project."""

import argparse
from argparse import Namespace
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import cast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.events import DirModifiedEvent, FileModifiedEvent

# Add script directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.text import Text

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from rich.console import Console
from rich.panel import Panel
from rich import box

from interfaces import PyrightOutput, Diagnostic  # type: ignore[import]

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

console = Console(force_terminal=True)


class LintHandler(FileSystemEventHandler):
    """Handle file system events for linting."""

    def __init__(self, fix: bool):
        self.fix: bool = fix
        self.last_run: float = 0
        self.pending: bool = False

    def on_modified(self, event: "DirModifiedEvent | FileModifiedEvent") -> None:  # type: ignore[override]
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent):
            path = Path(str(event.src_path))
            if path.suffix == ".py" and not path.name.startswith("."):
                current_time = time.time()
                if current_time - self.last_run > 1:  # Debounce
                    self.pending = True


def run_ruff(fix: bool = False) -> tuple[int, str]:
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


def run_ruff_format(fix: bool = False) -> tuple[int, str]:
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


def run_basedpyright() -> tuple[int, str]:
    """Run basedpyright type checker."""
    cmd = [
        "basedpyright",
        "--outputjson",
        str(project_root / "efm"),
        str(project_root / "tests"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


def get_code_snippet(
    file_path: Path, line_num: int, start_col: int, end_col: int
) -> Text | None:
    """Get a code snippet from the file with highlighting."""
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        if line_num < 1 or line_num > len(lines):
            return None

        # Get the problematic line (0-indexed)
        line = lines[line_num - 1].rstrip()

        # Create a marker line with squiggles
        marker = " " * start_col + "^" * max(1, end_col - start_col)
        indent = "    "
        empty_line_num = " " * len(str(line_num))
        text = Text()
        text.append(f"{indent}{line_num} | {line}\n")
        text.append(f"{indent}{empty_line_num} | {marker}\n")
        return text
    except:
        return None


def format_pyright_output(json_output: str, console: Console) -> None:
    """Format basedpyright JSON output and print it."""
    try:
        data = cast(PyrightOutput, json.loads(json_output))
        if "generalDiagnostics" not in data:
            console.print(json_output)
            return

        diagnostics = data.get("generalDiagnostics", [])
        if not diagnostics:
            console.print("No type errors")
            return

        # Group diagnostics by file
        by_file: dict[str, list[Diagnostic]] = {}
        for diag in diagnostics:
            file_path = diag.get("file", "unknown")
            # Make path relative to project root
            try:
                rel_path = Path(file_path).relative_to(project_root)
                file_path = str(rel_path)
            except ValueError:
                pass

            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(diag)

        # Print diagnostics for each file
        for file_path, file_diags in by_file.items():
            console.print()
            console.print(file_path, style="bold cyan")

            # Sort diagnostics by line number
            file_diags.sort(
                key=lambda d: (
                    d.get("range", {}).get("start", {}).get("line", 0),
                    d.get("range", {}).get("start", {}).get("character", 0),
                )
            )

            # Show all errors
            for diag in file_diags:
                severity = diag.get("severity", "error")
                message = diag.get("message", "unknown error")
                rule = diag.get("rule", "")

                range_info = diag.get("range", {})
                start = range_info.get("start", {})
                end = range_info.get("end", {})
                line = start.get("line", 0) + 1  # Convert to 1-based
                col = start.get("character", 0)
                end_col = end.get("character", col + 1)

                # Color based on severity
                if severity == "error":
                    style = "bold red"
                    symbol = "❌"
                else:
                    style = "bold yellow"
                    symbol = "⚠️"

                console.print(f"\n  {symbol} ", end="")
                console.print(f"{line}:{col}", style=style, end="")
                console.print(f" - {message}")

                if rule:
                    console.print(f"     ({rule})", style="dim")

                # Add code snippet
                full_path = project_root / file_path
                snippet = get_code_snippet(full_path, line, col, end_col)
                if snippet:
                    console.print(snippet, style="dim", overflow="ignore")

        # Add summary
        total = len(diagnostics)
        errors = sum(1 for d in diagnostics if d.get("severity") == "error")
        warnings = total - errors

        console.print()
        console.print("[bold]Summary:[/bold] ", end="")
        console.print(f"{errors} errors, {warnings} warnings in {len(by_file)} files")

    except (json.JSONDecodeError, KeyError, TypeError):
        # If we can't parse JSON, print original output
        console.print(json_output)


def display_results(
    ruff_result: tuple[int, str],
    format_result: tuple[int, str],
    pyright_result: tuple[int, str],
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

    # Basedpyright
    if pyright_result[0] == 0:
        console.print("✅ [green]Basedpyright[/green]: No type errors")
    else:
        console.print("❌ [red]Basedpyright[/red]:")
        if pyright_result[1].strip():
            # Format and print the pyright output
            format_pyright_output(pyright_result[1].strip(), console)

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


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run linting tools", add_help=False)
    parser.add_argument(
        "-w", "--watch", action="store_true", help="Watch for file changes"
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix linting issues")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    args: Namespace = parser.parse_args()

    help_flag: bool = args.help  # type: ignore[assignment]
    if help_flag:
        print(usage)
        return 0

    watch_flag: bool = args.watch  # type: ignore[assignment]
    fix_flag: bool = args.fix  # type: ignore[assignment]
    
    if watch_flag:
        watch_mode(fix_flag)
        return 0
    else:
        return run_lint(fix_flag)


if __name__ == "__main__":
    sys.exit(main())
