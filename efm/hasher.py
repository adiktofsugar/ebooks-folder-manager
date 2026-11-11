"""File -> store hash, with a path+stat cache so unchanged files aren't re-read. See docs/store.md."""

import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import xxhash

logger = logging.getLogger(__name__)

HASH_PREFIX = "xx_"
HASH_PATTERN = re.compile(r"xx_[0-9a-f]{32}")
CHUNK_SIZE = 1 << 20


def hash_contents(file: Path) -> str:
    """Hash without the stat cache, for files that aren't books in place (scratch, store copies)."""
    hasher = xxhash.xxh3_128()
    with open(file, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hasher.update(chunk)
    return HASH_PREFIX + hasher.hexdigest()


def default_stat_cache_root() -> Path:
    cache_home_dir = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache_home_dir / "efm" / "stat-cache"


class StatCache:
    """path -> hash cache, keyed by the filesystem itself."""

    root_dir: Path

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def _entry_dir(self, file: Path) -> Path:
        return self.root_dir.joinpath(*file.resolve().parts[1:])

    def _key_file(self, file: Path, st: os.stat_result) -> Path:
        return self._entry_dir(file) / f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"

    def get(self, file: Path, st: os.stat_result) -> str | None:
        try:
            h = self._key_file(file, st).read_text().strip()
        except (OSError, UnicodeDecodeError):
            return None
        # A key file cut short by a crash, or written by something else, would otherwise be
        # returned as the file's hash and silently point it at the wrong store entry.
        return h if HASH_PATTERN.fullmatch(h) else None

    def put(self, file: Path, st: os.stat_result, h: str) -> None:
        entry_dir = self._entry_dir(file)
        try:
            # Only one stat key per path is ever valid, so drop older ones.
            if entry_dir.is_dir():
                shutil.rmtree(entry_dir)
            entry_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_filepath = tempfile.mkstemp(dir=entry_dir, prefix=".tmp-")
            with os.fdopen(fd, "w") as f:
                f.write(h)
            os.replace(tmp_filepath, self._key_file(file, st))
        except OSError as e:
            # The cache is optional; a failed write just means re-hashing next time.
            logger.debug(f"Couldn't write stat cache for {file}: {e}")


@dataclass
class HashStats:
    cache_hits: int = 0
    hashed: int = 0
    bytes_hashed: int = 0


class Hasher:
    stat_cache: StatCache | None
    stats: HashStats

    def __init__(self, stat_cache: StatCache | None | Literal["default"] = "default"):
        """`Hasher()` uses the default stat cache; `Hasher(None)` never caches."""
        if stat_cache == "default":
            stat_cache = StatCache(default_stat_cache_root())
        self.stat_cache = stat_cache
        self.stats = HashStats()

    def hash(self, file: Path) -> str:
        # Stat before reading, so a change during hashing makes the cached key stale.
        st = file.stat()
        if self.stat_cache and (h := self.stat_cache.get(file, st)):
            self.stats.cache_hits += 1
            return h

        h = hash_contents(file)
        self.stats.hashed += 1
        self.stats.bytes_hashed += st.st_size

        if self.stat_cache:
            self.stat_cache.put(file, st, h)
        return h

    def put_cache(self, file: Path, h: str) -> None:
        """Put an already-known hash for `file` in the stat cache, so the next hash() of it is a cache hit."""
        if self.stat_cache:
            self.stat_cache.put(file, file.stat(), h)
