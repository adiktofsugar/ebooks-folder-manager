import argparse
import logging
import re
from pathlib import Path

from rich.console import Console

from efm.file_selection import get_files_from_dir
from efm.listing import (
    DEFAULT_EXCLUDES,
    Row,
    add_output_args,
    open_hasher,
    open_store,
    print_rows,
    read_rows,
)
from efm.metadata import Metadata

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "find",
        help="recursively find books, filtered by path or metadata",
        description="Recursively list books under a directory with metadata from the store, extracting it for books the store hasn't seen. Metadata filters are case-insensitive regexes; all given filters must match.",
        epilog="""
examples:
  efm find my-books                      # Every book under my-books
  efm find my-books 'cats.+epub'         # Only paths matching the given regex
  efm find my-books '!*.pdf'             # Exclude paths matching a pattern
  efm find my-books --author pratchett   # By author
  efm find my-books --format epub --encrypted
  efm find my-books --missing title      # Books with no title metadata
  efm find my-books -f json | jq .       # Machine-readable output
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("directory", help="directory (or single file) to search")
    parser.add_argument(
        "filters",
        nargs="*",
        help="optional pattern(s) to filter paths. can be glob (without **), regex, or substring; prefix with ! to exclude",
    )
    parser.add_argument("--title", type=_regex, help="title matches regex")
    parser.add_argument("--author", type=_regex, help="author matches regex")
    parser.add_argument(
        "--book-format",
        dest="book_format",
        metavar="REGEX",
        type=_regex,
        help="book format (e.g. epub, 'pdf 1.3') matches regex",
    )
    parser.add_argument(
        "--encrypted",
        action=argparse.BooleanOptionalAction,
        help="only books with (or, with --no-encrypted, without) DRM/encryption",
    )
    parser.add_argument(
        "--missing",
        action="append",
        choices=["title", "author"],
        default=[],
        help="only books lacking this metadata field (repeatable)",
    )
    add_output_args(parser)
    parser.set_defaults(run=run)


def _regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise argparse.ArgumentTypeError(f"invalid regex {pattern!r}: {e}")


def run(args: argparse.Namespace, console: Console) -> int:
    target_path = Path(args.directory).resolve()
    if not target_path.exists():
        logger.error(f"Does not exist: {args.directory}")
        return 1

    if target_path.is_file():
        base_dir = target_path.parent
        book_files = [target_path]
    else:
        base_dir = target_path
        book_files = sorted(
            get_files_from_dir(target_path, [*DEFAULT_EXCLUDES, *args.filters])
        )

    rows = [Row(path, str(path.relative_to(base_dir))) for path in book_files]
    read_rows(open_store(args), open_hasher(args), rows, console)
    print_rows([r for r in rows if _keep(r, args)], args)
    return 1 if any(r.error for r in rows) else 0


def _keep(r: Row, args: argparse.Namespace) -> bool:
    if r.entry is not None:
        return matches_metadata(r.entry.metadata, args)
    # Unreadable books have no metadata to match, so only show them when unfiltered.
    return not (
        args.title
        or args.author
        or args.book_format
        or args.encrypted is not None
        or args.missing
    )


def matches_metadata(m: Metadata, args: argparse.Namespace) -> bool:
    for pattern, value in (
        (args.title, m.title),
        (args.author, m.author),
        (args.book_format, m.format),
    ):
        if pattern and not (value and pattern.search(value)):
            return False
    if args.encrypted is not None and bool(m.encryption) != args.encrypted:
        return False
    return not any(getattr(m, field) for field in args.missing)
