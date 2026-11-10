"""path -> hash cache, keyed by the filesystem itself. See docs/store.md."""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from efm.hasher import HASH_PATTERN

logger = logging.getLogger(__name__)


def default_stat_cache_root() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache_home) / "efm" / "stat-cache"


class StatCache:
    root: Path

    def __init__(self, root: Path):
        self.root = root

    def _book_dir(self, book: Path) -> Path:
        return self.root.joinpath(*book.resolve().parts[1:])

    def _key_file(self, book: Path, st: os.stat_result) -> Path:
        return self._book_dir(book) / f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"

    def get(self, book: Path, st: os.stat_result) -> str | None:
        try:
            h = self._key_file(book, st).read_text().strip()
        except (OSError, UnicodeDecodeError):
            return None
        # A key file cut short by a crash, or written by something else, would otherwise be
        # returned as the book's hash and silently point it at the wrong store entry.
        return h if HASH_PATTERN.fullmatch(h) else None

    def put(self, book: Path, st: os.stat_result, h: str) -> None:
        book_dir = self._book_dir(book)
        try:
            # Only one stat key per path is ever valid, so drop older ones.
            if book_dir.is_dir():
                shutil.rmtree(book_dir)
            book_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=book_dir, prefix=".tmp-")
            with os.fdopen(fd, "w") as f:
                f.write(h)
            os.replace(tmp, self._key_file(book, st))
        except OSError as e:
            # The cache is optional; a failed write just means re-hashing next time.
            logger.debug(f"Couldn't write stat cache for {book}: {e}")
