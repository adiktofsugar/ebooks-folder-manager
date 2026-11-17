"""`efm store ...`: inspect the store by hash. Every other command takes paths."""

import argparse
import logging
import os
import sys
from pathlib import Path

from rich.console import Console

from efm.exceptions import ContentError, InvalidStoreEntryError
from efm.listing import Row, add_output_args, open_store, print_rows
from efm.number_util import format_bytes

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "store",
        help="inspect the metadata store by hash",
        description="Look up store entries by hash, rather than by book path.",
    )
    parser.set_defaults(run=lambda _args, _console: _print_help(parser))
    store_subparsers = parser.add_subparsers(
        title="store commands", metavar="<store command>"
    )

    show = store_subparsers.add_parser(
        "show",
        help="write a stored version's content to stdout or a file",
        description="Write the stored content of HASH, like `git show <hash>`.",
    )
    show.add_argument("hash", help="store hash (xx_...)")
    show.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write to this file (replaced only if the content verifies) instead of stdout",
    )
    show.set_defaults(run=run_show)

    ancestor = store_subparsers.add_parser(
        "ancestor",
        help="print the hash a version was derived from",
        description="Print the ancestor of HASH. Exits 1 if it has none.",
    )
    ancestor.add_argument("hash", help="store hash (xx_...)")
    ancestor.add_argument(
        "-a", "--all", action="store_true", help="walk the chain, one hash per line"
    )
    ancestor.set_defaults(run=run_ancestor)

    ls = store_subparsers.add_parser(
        "ls",
        help="list every entry in the store",
        description="List store entries: hash, title, author.",
    )
    ls.add_argument(
        "--has-content",
        action="store_true",
        help="only entries whose content is stored",
    )
    add_output_args(ls)
    ls.set_defaults(run=run_ls)

    info = store_subparsers.add_parser(
        "info",
        help="show where the store is and what's in it",
        description="Show the store's path, which setting chose it, and entry/blob counts.",
    )
    info.set_defaults(run=run_info)


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 1


def run_show(args: argparse.Namespace, _console: Console) -> int:
    store = open_store(args)
    try:
        if args.output is None:
            store.get_content(args.hash, sys.stdout.buffer)
            sys.stdout.buffer.flush()
        else:
            store.restore_content(args.hash, args.output)
    except (ValueError, ContentError, OSError) as e:
        logger.error(str(e))
        return 1
    return 0


def run_ancestor(args: argparse.Namespace, _console: Console) -> int:
    store = open_store(args)
    h = args.hash
    seen = {h}
    found = False
    try:
        while True:
            entry = store.load(h)
            if entry is None:
                logger.error(f"No store entry for {h}")
                return 1
            if entry.ancestor is None:
                break
            h = entry.ancestor
            if h in seen:
                logger.error(f"Ancestor chain loops at {h}")
                return 1
            seen.add(h)
            sys.stdout.write(h + "\n")
            found = True
            if not args.all:
                break
    except (ValueError, InvalidStoreEntryError) as e:
        logger.error(str(e))
        return 1
    return 0 if found else 1


def _store_source(args: argparse.Namespace) -> str:
    # Mirrors the precedence in open_store / default_store_dir.
    if args.store:
        return "--store"
    if os.environ.get("EFM_STORE"):
        return "$EFM_STORE"
    return "default ($XDG_DATA_HOME/efm/store)"


def run_info(args: argparse.Namespace, _console: Console) -> int:
    store = open_store(args)
    lines = [f"path: {store.root_dir.resolve()}", f"from: {_store_source(args)}"]
    if not store.root_dir.is_dir():
        lines.append("(doesn't exist yet; created on first write)")
    else:
        hashes = list(store.hashes())
        with_content = sum(store.has_content(h) for h in hashes)
        blob_files = (
            list(store.content.blobs_dir.iterdir())
            if store.content.blobs_dir.is_dir()
            else []
        )
        blob_bytes = sum(f.stat().st_size for f in blob_files)
        lines.append(f"books: {len(hashes)} ({with_content} with content)")
        lines.append(f"blobs: {len(blob_files)} ({format_bytes(blob_bytes)})")
    sys.stdout.writelines(line + "\n" for line in lines)
    return 0


def run_ls(args: argparse.Namespace, _console: Console) -> int:
    store = open_store(args)
    rows: list[Row] = []
    failed = False
    for h in store.hashes():
        if args.has_content and not store.has_content(h):
            continue
        row = Row(path=store.entry_dir(h), name=h, hash=h)
        try:
            row.entry = store.load(h)
            if row.entry is None:
                row.error = "incomplete entry (no metadata.json)"
            else:
                # Read now, so a broken file is reported here instead of while printing.
                _ = row.entry.metadata_raw if args.raw else row.entry.metadata
        except InvalidStoreEntryError as e:
            row.entry, row.error = None, str(e)
        if row.error:
            logger.error(f"{h}: {row.error}")
            failed = True
        rows.append(row)
    print_rows(rows, args)
    return 1 if failed else 0
