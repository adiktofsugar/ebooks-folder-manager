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
from efm.listing import open_store
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
    failed = False
    for path in args.files:
        try:
            target = fulfill_in_place(store, path)
            logger.info(f"{path} -> {target}")
        except (OSError, BookError, InvalidStoreEntryError) as e:
            logger.error(f"{path}: {e}")
            failed = True
    return 1 if failed else 0


def fulfill_in_place(store: Store, path: Path) -> Path:
    if path.suffix.lower() != ".acsm":
        raise BookError(path, message="not an .acsm file")

    # The token is about to be deleted, so the store must hold it first.
    original = store.hash_file(path)
    if store.load(original) is None:
        store.put(original, StoreEntry.from_book(path))
    store.put_content(original, path)

    config = get_config(path.parent)
    with scratch_dir("acsm") as scratch:
        token = scratch / path.name
        shutil.copyfile(path, token)
        downloaded = fulfill(token, scratch, config)

        target = path.with_suffix(downloaded.suffix)
        h = store.hash_contents(downloaded)
        store.put(h, StoreEntry.from_book(downloaded, ancestor=original))

        _install(downloaded, target)
        if store.stat_cache:
            store.stat_cache.put(target, target.stat(), h)
        path.unlink()
    return target


def _install(src: Path, target: Path) -> None:
    try:
        os.replace(src, target)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
    # Scratch is on another fs; copy next to the target so the final rename is still atomic.
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".efm-", suffix=target.suffix)
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
