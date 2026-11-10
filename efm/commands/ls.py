import argparse
import logging
from pathlib import Path

from rich.console import Console

from efm.file_selection import matches_filter
from efm.listing import (
    DEFAULT_EXCLUDES,
    Row,
    add_output_args,
    open_hasher,
    open_store,
    print_rows,
    read_rows,
)

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "ls",
        help="list books in a directory with their metadata",
        description="List the books directly in a directory (not recursively) with metadata from the store, extracting it for books the store hasn't seen. Use `efm find` to recurse.",
        epilog="""
examples:
  efm ls                           # Books in the current directory
  efm ls my-books                  # Books in my-books (subdirectories shown, not entered)
  efm ls my-books/*.epub           # Just these files
  efm ls my-books -f json | jq .   # Machine-readable output
  efm ls my-books --raw            # Show what pymupdf reported, unnormalized
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="files or directories to list (default: current directory)",
    )
    add_output_args(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace, console: Console) -> int:
    rows: list[Row] = []
    missing = False
    # Like ls: a lone directory's entries are shown bare, otherwise prefixed by the operand.
    bare = len(args.paths) == 1
    for operand in args.paths:
        target = Path(operand)
        if not target.exists():
            logger.error(f"Does not exist: {operand}")
            missing = True
        elif target.is_dir():
            rows += _dir_rows(target, operand, bare)
        else:
            rows.append(Row(target.absolute(), operand))

    if rows or not missing:
        read_rows(open_store(args), open_hasher(args), rows, console)
        print_rows(rows, args)
    return 1 if missing or any(r.error for r in rows) else 0


def _dir_rows(directory: Path, operand: str, bare: bool) -> list[Row]:
    rows: list[Row] = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith("."):
            continue
        name = child.name if bare else str(Path(operand) / child.name)
        if child.is_dir():
            rows.append(Row(child.absolute(), name, is_dir=True))
        elif all(matches_filter(child, f) for f in DEFAULT_EXCLUDES):
            rows.append(Row(child.absolute(), name))
    return rows
