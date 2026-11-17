"""Reading books through the store and rendering them, shared by `ls` and `find`."""

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
from efm.hasher import Hasher
from efm.metadata import EXTRACTOR_VERSION
from efm.number_util import format_bytes
from efm.store import Store, StoreEntry, default_store_dir

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDES = ["!*.bak", "!efm.toml", "!efm.yaml", "!efm.yml", "!efm.json"]


@dataclass
class Row:
    path: Path
    name: str
    hash: str | None = None
    entry: StoreEntry | None = None
    error: str | None = None
    is_dir: bool = False


def add_output_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--raw", action="store_true", help="show raw pymupdf metadata instead"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["line", "table", "json"],
        default="line",
        help="output format: line (tab-separated file, title, author; default), table, or json",
    )


def open_store(args: argparse.Namespace) -> Store:
    store_dir = Path(args.store) if args.store else default_store_dir()
    logger.debug(f"Using store {store_dir}")
    # MuPDF prints recoverable parse noise (bad CSS etc.) straight to stderr.
    pymupdf.TOOLS.mupdf_display_errors(False)
    return Store(store_dir)


def open_hasher(args: argparse.Namespace) -> Hasher:
    return Hasher(None) if args.no_stat_cache else Hasher()


def load_or_create_entry(
    store: Store, h: str, book_file: Path
) -> tuple[StoreEntry, bool]:
    """The book's store entry, extracting it on a miss or when an older extractor made it.

    Returns the entry and whether it was (re-)extracted.
    """
    entry = store.load(h)
    if entry is not None:
        if entry.metadata_internal.extractor_version >= EXTRACTOR_VERSION:
            return entry, False
        logger.debug(f"Re-extracting {book_file}: made by an older extractor")
        entry = StoreEntry.from_book(book_file, ancestor=entry.ancestor)
    else:
        entry = StoreEntry.from_book(book_file)
    store.put(h, entry)
    return entry, True


def read_rows(store: Store, hasher: Hasher, rows: list[Row], console: Console):
    """Fill in hash and store entry for each non-directory row, extracting on a miss."""
    books = [r for r in rows if not r.is_dir]
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
        task = progress.add_task("Reading", total=len(books))
        for r in books:
            progress.update(task, description=r.path.name)
            try:
                r.hash = hasher.hash(r.path)
                entry, created = load_or_create_entry(store, r.hash, r.path)
                extracted += created
                # Surface a broken store entry here rather than mid-render.
                _ = entry.metadata
                r.entry = entry
            except (OSError, InvalidStoreEntryError) as e:
                logger.error(f"{r.path}: {e}")
                r.hash = None
                r.error = str(e)
            progress.advance(task)

    s = hasher.stats
    logger.debug(
        f"{len(books)} files in {time.perf_counter() - started:.3f}s: "
        + f"{s.cache_hits} stat-cache hits, {s.hashed} hashed ({format_bytes(s.bytes_hashed)}), "
        + f"{extracted} extracted"
    )


def print_rows(rows: list[Row], args: argparse.Namespace):
    if args.format == "json":
        sys.stdout.write(json.dumps(to_json(rows, args.raw), indent=2) + "\n")
    elif args.format == "table":
        Console().print(to_table(rows, args.raw))
    else:
        sys.stdout.writelines(line + "\n" for line in to_lines(rows, args.raw))


def to_lines(rows: list[Row], raw: bool) -> list[str]:
    """One line per row, so output pipes into wc, cut, grep, etc."""
    lines: list[str] = []
    for r in rows:
        if r.is_dir:
            lines.append(_field(r.name + "/"))
            continue
        title, author = "", ""
        if r.entry is not None and raw:
            meta = _raw_pymupdf_metadata(r.entry.metadata_raw)
            title, author = str(meta.get("title") or ""), str(meta.get("author") or "")
        elif r.entry is not None:
            title = r.entry.metadata.title or ""
            author = r.entry.metadata.author or ""
        # Empty fields are kept so `cut -f` columns line up.
        lines.append("\t".join(_field(v) for v in (r.name, title, author)))
    return lines


def _raw_pymupdf_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    return ((raw or {}).get("pymupdf_fields") or {}).get("metadata") or {}


def _field(value: str) -> str:
    # A tab or newline inside a value would break the one-line-per-book contract.
    return " ".join(value.split())


def to_json(rows: list[Row], raw: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.is_dir:
            out.append({"path": str(r.path), "directory": True})
            continue
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


def to_table(rows: list[Row], raw: bool) -> Table:
    table = Table(show_lines=True)
    table.add_column("File", overflow="fold")
    table.add_column("Title", overflow="fold")
    table.add_column("Author", overflow="fold")
    table.add_column("Details", overflow="fold")

    for r in rows:
        if r.is_dir:
            table.add_row(Text(r.name + "/", style="bold blue"), "", "", "")
        elif r.entry is None:
            table.add_row(r.name, "", "", _details([], r.error))
        elif raw:
            table.add_row(r.name, *_raw_cells(r.entry.metadata_raw, r.hash))
        else:
            m = r.entry.metadata
            pairs: list[tuple[str, object]] = [
                ("series", m.series),
                ("series_index", m.series_index),
                ("kind", m.kind),
                ("format", m.format),
                # Spelled out so DRM-free is visible, not just absent.
                ("encryption", m.encryption or (None if m.error else "none")),
                ("size", format_bytes(m.size)),
                ("page_count", m.page_count),
                ("subject", m.subject),
                ("keywords", m.keywords),
                ("creator", m.creator),
                ("producer", m.producer),
                ("creation_date", m.creation_date),
                ("mod_date", m.mod_date),
                ("hash", r.hash),
            ]
            table.add_row(
                r.name, m.title or "", m.author or "", _details(pairs, m.error)
            )
    return table


def _raw_cells(raw: dict[str, Any] | None, h: str | None) -> tuple[str, str, Text]:
    if raw is None:
        return "", "", Text("(no raw metadata)", style="dim")
    pymupdf_fields: dict[str, Any] = raw.get("pymupdf_fields") or {}
    meta = _raw_pymupdf_metadata(raw)
    pairs: list[tuple[str, object]] = [
        (k, v) for k, v in meta.items() if k not in ("title", "author")
    ]
    pairs += [(k, v) for k, v in pymupdf_fields.items() if k != "metadata"]
    for section, fields in raw.items():
        if section != "pymupdf_fields" and isinstance(fields, dict):
            pairs += [(f"{section}.{k}", v) for k, v in fields.items()]
    pairs.append(("hash", h))
    return str(meta.get("title") or ""), str(meta.get("author") or ""), _details(pairs)
