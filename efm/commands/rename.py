import argparse
import errno
import logging
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from rich.console import Console

from efm.config import get_config
from efm.exceptions import TemplateError
from efm.file_selection import get_files_from_dir
from efm.hasher import Hasher
from efm.listing import DEFAULT_EXCLUDES, Row, open_hasher, open_store, read_rows
from efm.template import Variant, choose, compile_preset, parse, render, template_vars

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "rename",
        aliases=["rnm"],
        help="move books to paths built from their metadata",
        description="Move each book to a path built from a template over its metadata, relative to the root: the directory operand, or --root. Directories are searched recursively. The template comes from -f, else the -p preset, else rename.default_preset, else the preset named 'default' in efm.toml (searched for upwards from the root). See docs/rename.md.",
        epilog="""
examples:
  efm rename -n ~/ebooks                                # Dry run with the default preset
  efm rename -p comic ~/ebooks/comics
  efm rename -f '{author}/{title}{ext}' ~/ebooks
  efm rename -f '{series}/{title}{ext}' ~/ebooks/George --root ~/ebooks
  efm rename ~/ebooks/my-book.epub                      # Only templates without folders
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", type=Path, help="books or directories")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--preset", help="preset name from the config")
    group.add_argument(
        "-f",
        "--format",
        dest="template",
        metavar="TEMPLATE",
        help="template, e.g. '{author}/{title}{ext}'",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="directory templates are relative to (default: the directory operand)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="print the moves without making them",
    )
    parser.set_defaults(run=run)


@dataclass
class Move:
    src_file: Path
    target_file: Path
    root_dir: Path
    hash: str


def run(args: argparse.Namespace, console: Console) -> int:
    store = open_store(args)
    hasher = open_hasher(args)
    root_arg_dir: Path | None = args.root.expanduser().absolute() if args.root else None
    failed = False
    moves: list[Move] = []

    for operand_path in args.paths:
        path = Path(operand_path).expanduser().absolute()
        if not path.exists():
            logger.error(f"Does not exist: {operand_path}")
            failed = True
            continue
        is_dir = path.is_dir()
        root_dir = root_arg_dir or (path if is_dir else path.parent)
        try:
            variants = _variants(args, root_dir)
        except (TemplateError, ValidationError, ValueError) as e:
            logger.error(f"{operand_path}: {e}")
            failed = True
            continue

        book_files = (
            sorted(get_files_from_dir(path, DEFAULT_EXCLUDES)) if is_dir else [path]
        )
        rows = [Row(f, f.name) for f in book_files]
        read_rows(store, hasher, rows, console)
        for r in rows:
            if r.entry is None or r.hash is None:
                failed = True  # read_rows logged it
                continue
            try:
                variables = template_vars(r.path, r.entry.metadata)
                rel_path = render(choose(variants, variables), variables)
            except TemplateError as e:
                logger.error(f"{r.path}: {e}")
                failed = True
                continue
            if not is_dir and root_arg_dir is None and len(rel_path.parts) > 1:
                logger.error(
                    f"{r.path}: {rel_path} has folders, but a single file has no clear root; pass --root"
                )
                failed = True
                continue
            moves.append(Move(r.path, root_dir / rel_path, root_dir, r.hash))

    # Two books at one path would mean one silently replacing the other.
    counts = Counter(m.target_file for m in moves)
    for m in moves:
        if counts[m.target_file] > 1:
            logger.error(f"{m.src_file}: another book also renames to {m.target_file}")
            failed = True
    moves = [m for m in moves if counts[m.target_file] == 1]

    for m in moves:
        if m.src_file == m.target_file:
            logger.debug(f"Already named: {m.src_file}")
            continue
        line = f"{_display(m.src_file, m.root_dir)} -> {_display(m.target_file, m.root_dir)}"
        if args.dry_run:
            sys.stdout.write(line + "\n")
            continue
        try:
            _move(hasher, m)
            logger.info(line)
        except (OSError, ValueError) as e:
            logger.error(f"{m.src_file}: {e}")
            failed = True
    return 1 if failed else 0


def _variants(args: argparse.Namespace, root_dir: Path) -> list[Variant]:
    if args.template is not None:
        return [Variant(None, parse(args.template))]
    config = get_config(root_dir)
    rename = config.rename if config else None
    presets = rename.presets if rename else {}
    name = args.preset or (rename.default_preset if rename else None) or "default"
    if name not in presets:
        known = ", ".join(sorted(presets)) or "none"
        raise TemplateError(
            f"no rename preset {name!r} in efm config at or above {root_dir} (known: {known}); pass -f or -p"
        )
    try:
        return compile_preset(presets[name])
    except TemplateError as e:
        raise TemplateError(f"preset {name!r}: {e}") from e


def _move(hasher: Hasher, m: Move) -> None:
    if m.target_file.exists() and not os.path.samefile(m.src_file, m.target_file):
        if hasher.hash(m.target_file) != m.hash:
            raise ValueError(f"{m.target_file} already exists and is a different file")
        logger.debug(f"{m.target_file} has the same content; replacing it")
    m.target_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(m.src_file, m.target_file)
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
        shutil.move(m.src_file, m.target_file)
    # A rename changes ctime, so the old stat-cache key no longer matches.
    hasher.put_cache(m.target_file, m.hash)
    _remove_empty_parents(m.src_file.parent, m.root_dir)


def _remove_empty_parents(dir: Path, root_dir: Path) -> None:
    while dir != root_dir and dir.is_relative_to(root_dir):
        try:
            dir.rmdir()
        except OSError:
            return
        dir = dir.parent


def _display(path: Path, root_dir: Path) -> str:
    return (
        str(path.relative_to(root_dir)) if path.is_relative_to(root_dir) else str(path)
    )
