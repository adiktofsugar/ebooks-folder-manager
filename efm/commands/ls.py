import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from efm.exceptions import InvalidStoreEntryError
from efm.file_selection import get_files_from_dirpath
from efm.stat_cache import StatCache, default_stat_cache_root
from efm.store import Store, StoreEntry, default_store_dir

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDES = ["!*.bak", "!efm.toml", "!efm.yaml", "!efm.yml", "!efm.json"]


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "ls",
        help="list books in a directory with their metadata",
        description="List books in a directory (recursively) with metadata from the store, extracting it for books the store hasn't seen.",
        epilog="""
examples:
  efm ls my-books                  # Table of all books in my-books
  efm ls my-books 'cats.+epub'     # Only books matching the given regex
  efm ls my-books -f json | jq .   # Machine-readable output
  efm ls my-books --raw            # Show what pymupdf reported, unnormalized
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("directory", help="directory (or single file) to list")
    parser.add_argument(
        "filters",
        nargs="*",
        help="optional pattern(s) to filter files. can be glob (without **), regex, or substring",
    )
    parser.add_argument(
        "--raw", action="store_true", help="show raw pymupdf metadata instead"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )
    parser.set_defaults(run=run)


@dataclass
class Row:
    path: Path
    hash: str | None
    entry: StoreEntry | None
    error: str | None = None


def run(args: argparse.Namespace, console: Console) -> int:
    target = Path(args.directory).resolve()
    if not target.exists():
        logger.error(f"Does not exist: {args.directory}")
        return 1

    if target.is_file():
        base = target.parent
        filepaths = [target]
    else:
        base = target
        filepaths = sorted(
            get_files_from_dirpath(target, [*DEFAULT_EXCLUDES, *args.filters])
        )

    store_dir = Path(args.store) if args.store else default_store_dir()
    stat_cache = None if args.no_stat_cache else StatCache(default_stat_cache_root())
    store = Store(store_dir, stat_cache)
    logger.debug(f"Using store {store_dir}")

    # MuPDF prints recoverable parse noise (bad CSS etc.) straight to stderr.
    pymupdf.TOOLS.mupdf_display_errors(False)

    rows = collect_rows(store, filepaths, console)

    if args.format == "json":
        sys.stdout.write(json.dumps(to_json(rows, args.raw), indent=2) + "\n")
    else:
        Console().print(to_table(rows, base, args.raw))

    return 1 if any(r.error for r in rows) else 0


def collect_rows(store: Store, filepaths: list[Path], console: Console) -> list[Row]:
    rows: list[Row] = []
    extracted = 0
    started = time.perf_counter()
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Reading", total=len(filepaths))
        for path in filepaths:
            progress.update(task, description=path.name)
            try:
                h = store.hash_file(path)
                entry = store.load(h)
                if entry is None:
                    entry = StoreEntry.from_book(path)
                    store.put(h, entry)
                    extracted += 1
                # Surface a broken store entry here rather than mid-render.
                _ = entry.metadata
                rows.append(Row(path, h, entry))
            except (OSError, InvalidStoreEntryError) as e:
                logger.error(f"{path}: {e}")
                rows.append(Row(path, None, None, error=str(e)))
            progress.advance(task)

    s = store.stats
    logger.debug(
        f"{len(filepaths)} files in {time.perf_counter() - started:.3f}s: "
        + f"{s.cache_hits} stat-cache hits, {s.hashed} hashed ({s.bytes_hashed / 1e6:.1f} MB), "
        + f"{extracted} extracted"
    )
    return rows


def to_json(rows: list[Row], raw: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        item: dict[str, Any] = {"path": str(r.path), "hash": r.hash}
        if r.entry is None:
            item["error"] = r.error
        elif raw:
            item["metadata"] = r.entry.metadata_raw
        else:
            item["metadata"] = r.entry.metadata.model_dump(mode="json")
        out.append(item)
    return out


def _format_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)  # pyright: ignore[reportUnknownArgumentType]
    return str(value)


def _format_size(size: int) -> str:
    if size < 1000:
        return f"{size} B"
    n = size / 1000
    for unit in ("KB", "MB"):
        if n < 1000:
            return f"{n:.1f} {unit}"
        n /= 1000
    return f"{n:.1f} GB"


def _details(pairs: list[tuple[str, object]], error: str | None = None) -> Text:
    text = Text()
    if error:
        text.append(f"error: {error}", style="red")
    for key, value in pairs:
        if value is None or value == "" or value == []:
            continue
        if text:
            text.append("\n")
        text.append(f"{key}: ", style="dim")
        text.append(_format_value(value))
    return text


def to_table(rows: list[Row], base: Path, raw: bool) -> Table:
    table = Table(show_lines=True)
    table.add_column("File", overflow="fold")
    table.add_column("Title", overflow="fold")
    table.add_column("Author", overflow="fold")
    table.add_column("Details", overflow="fold")

    for r in rows:
        name = str(r.path.relative_to(base))
        if r.entry is None:
            table.add_row(name, "", "", _details([], r.error))
        elif raw:
            table.add_row(name, *_raw_cells(r.entry.metadata_raw, r.hash))
        else:
            m = r.entry.metadata
            pairs: list[tuple[str, object]] = [
                ("format", m.format),
                # Spelled out so DRM-free is visible, not just absent.
                ("encryption", m.encryption or (None if m.error else "none")),
                ("size", _format_size(m.size)),
                ("page_count", m.page_count),
                ("subject", m.subject),
                ("keywords", m.keywords),
                ("creator", m.creator),
                ("producer", m.producer),
                ("creation_date", m.creation_date),
                ("mod_date", m.mod_date),
                ("hash", r.hash),
            ]
            table.add_row(name, m.title or "", m.author or "", _details(pairs, m.error))
    return table


def _raw_cells(raw: dict[str, Any] | None, h: str | None) -> tuple[str, str, Text]:
    if raw is None:
        return "", "", Text("(no raw metadata)", style="dim")
    meta: dict[str, Any] = raw.get("metadata") or {}
    pairs: list[tuple[str, object]] = [
        (k, v) for k, v in meta.items() if k not in ("title", "author")
    ]
    pairs += [(k, v) for k, v in raw.items() if k != "metadata"]
    pairs.append(("hash", h))
    return str(meta.get("title") or ""), str(meta.get("author") or ""), _details(pairs)
