import argparse
import errno
import logging
import os
import shutil
import tempfile
from pathlib import Path

from rich.console import Console

from efm.acsm import fulfill
from efm.config import get_config
from efm.exceptions import BookError, InvalidStoreEntryError
from efm.hasher import Hasher, hash_contents
from efm.listing import open_hasher, open_store
from efm.scratch import scratch_dir
from efm.store import Store, StoreEntry

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "acsm",
        help="fulfill .acsm files, replacing each with the book it stands for",
        description="Download the book each Adobe .acsm token stands for and put it in the token's place (same name, new extension). The token is kept in the store, and the new book's store entry records it as its ancestor. Needs adobe_user and adobe_password in efm.toml (searched for upwards from the token's directory).",
        epilog="""
examples:
  efm acsm my-books/URLLink.acsm    # -> my-books/URLLink.epub
  efm acsm my-books/*.acsm
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="+", type=Path, help=".acsm files to fulfill")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace, console: Console) -> int:
    store = open_store(args)
    hasher = open_hasher(args)
    failed = False
    for acsm_file in args.files:
        try:
            book_file = fulfill_in_place(store, hasher, acsm_file)
            logger.info(f"{acsm_file} -> {book_file}")
        except (OSError, BookError, InvalidStoreEntryError) as e:
            logger.error(f"{acsm_file}: {e}")
            failed = True
    return 1 if failed else 0


def fulfill_in_place(store: Store, hasher: Hasher, acsm_file: Path) -> Path:
    if acsm_file.suffix.lower() != ".acsm":
        raise BookError(acsm_file, message="not an .acsm file")

    # The token is about to be deleted, so the store must hold it first.
    original = hasher.hash(acsm_file)
    if store.load(original) is None:
        store.put(original, StoreEntry.from_book(acsm_file))
    store.put_content(original, acsm_file)

    config = get_config(acsm_file.parent)
    with scratch_dir("acsm") as work_dir:
        token_file = work_dir / acsm_file.name
        shutil.copyfile(acsm_file, token_file)
        downloaded_file = fulfill(token_file, work_dir, config)

        book_file = acsm_file.with_suffix(downloaded_file.suffix)
        h = hash_contents(downloaded_file)
        store.put(h, StoreEntry.from_book(downloaded_file, ancestor=original))

        _install(downloaded_file, book_file)
        hasher.put_cache(book_file, h)
        acsm_file.unlink()
    return book_file


def _install(src_file: Path, target_file: Path) -> None:
    try:
        os.replace(src_file, target_file)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
    # Scratch is on another fs; copy next to the target so the final rename is still atomic.
    fd, tmp_filepath = tempfile.mkstemp(
        dir=target_file.parent, prefix=".efm-", suffix=target_file.suffix
    )
    os.close(fd)
    try:
        shutil.copyfile(src_file, tmp_filepath)
        os.replace(tmp_filepath, target_file)
    except BaseException:
        Path(tmp_filepath).unlink(missing_ok=True)
        raise
