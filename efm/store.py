"""Content-addressed metadata store. See docs/store.md."""

import json
import logging
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, final

import xxhash
from pydantic import ValidationError

from efm.exceptions import InvalidStoreEntryError, UnsupportedSchemaError
from efm.hasher import HASH_PATTERN, HASH_PREFIX
from efm.metadata import (
    InternalMetadata,
    Metadata,
    extract,
    load_internal_metadata,
    load_metadata,
)
from efm.stat_cache import StatCache

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1 << 20

METADATA_FILE = "metadata.json"
METADATA_INTERNAL_FILE = "metadata_internal.json"
METADATA_RAW_FILE = "metadata_raw.json"
ANCESTOR_FILE = "ancestor"
CONTENT_FILE = "content"


def default_store_dir() -> Path:
    if store := os.environ.get("EFM_STORE"):
        return Path(store)
    data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(data_home) / "efm" / "store"


def _write_json_atomic(path: Path, data: object) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _write_text_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _copy_atomic(src: Path, dst: Path) -> None:
    fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=".tmp-")
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@final
class _Unloaded:
    pass


_UNLOADED = _Unloaded()


class StoreEntry:
    """A book version's metadata. Either built in memory, or bound to a store dir and read lazily."""

    _dir: Path | None
    _metadata: Metadata | _Unloaded
    _metadata_internal: InternalMetadata | _Unloaded
    _metadata_raw: dict[str, Any] | None | _Unloaded
    _ancestor: str | None | _Unloaded

    def __init__(
        self,
        metadata: Metadata | _Unloaded = _UNLOADED,
        metadata_internal: InternalMetadata | _Unloaded = _UNLOADED,
        metadata_raw: dict[str, Any] | None | _Unloaded = _UNLOADED,
        dir: Path | None = None,
        ancestor: str | None | _Unloaded = _UNLOADED,
    ):
        self._dir = dir
        self._metadata = metadata
        self._metadata_internal = metadata_internal
        self._metadata_raw = metadata_raw
        # Unbound entries default to no ancestor; bound ones read the file.
        self._ancestor = None if dir is None and ancestor is _UNLOADED else ancestor

    @classmethod
    def from_book(cls, path: Path, ancestor: str | None = None) -> "StoreEntry":
        extracted = extract(path)
        return cls(
            extracted.metadata, extracted.internal, extracted.raw, ancestor=ancestor
        )

    def _read[T](self, name: str, loader: Callable[[object], T]) -> T:
        if self._dir is None:
            raise ValueError(
                f"StoreEntry has no {name} and no store dir to read it from"
            )
        path = self._dir / name
        try:
            return loader(json.loads(path.read_text()))
        except (
            OSError,
            json.JSONDecodeError,
            ValidationError,
            UnsupportedSchemaError,
        ) as e:
            raise InvalidStoreEntryError(path, e) from e

    @property
    def metadata(self) -> Metadata:
        if isinstance(self._metadata, _Unloaded):
            self._metadata = self._read(METADATA_FILE, load_metadata)
        return self._metadata

    @property
    def metadata_internal(self) -> InternalMetadata:
        if isinstance(self._metadata_internal, _Unloaded):
            self._metadata_internal = self._read(
                METADATA_INTERNAL_FILE, load_internal_metadata
            )
        return self._metadata_internal

    @property
    def metadata_raw(self) -> dict[str, Any] | None:
        if isinstance(self._metadata_raw, _Unloaded):
            self._metadata_raw = self._read(METADATA_RAW_FILE, _as_raw)
        return self._metadata_raw

    @property
    def ancestor(self) -> str | None:
        """Hash of the book version this one was derived from (e.g. the .acsm it was fulfilled from)."""
        if isinstance(self._ancestor, _Unloaded):
            assert self._dir is not None
            path = self._dir / ANCESTOR_FILE
            try:
                text = path.read_text().strip()
            except FileNotFoundError:
                text = None
            except OSError as e:
                raise InvalidStoreEntryError(path, e) from e
            if text is not None and not HASH_PATTERN.fullmatch(text):
                raise InvalidStoreEntryError(path, ValueError(f"not a hash: {text!r}"))
            self._ancestor = text
        return self._ancestor


def _as_raw(data: object) -> dict[str, Any] | None:
    if data is None or isinstance(data, dict):
        return data
    raise ValueError(f"expected an object or null, got {type(data).__name__}")


@dataclass
class HashStats:
    cache_hits: int = 0
    hashed: int = 0
    bytes_hashed: int = 0


class Store:
    root: Path
    stat_cache: StatCache | None
    stats: HashStats

    def __init__(self, root: Path, stat_cache: StatCache | None):
        self.root = root
        self.stat_cache = stat_cache
        self.stats = HashStats()

    # TODO: hash_file/hash_contents don't use the store; move them to a Hasher. See todo/hasher.md.
    def hash_file(self, path: Path) -> str:
        # Stat before reading, so a change during hashing makes the cached key stale.
        st = path.stat()
        if self.stat_cache and (h := self.stat_cache.get(path, st)):
            self.stats.cache_hits += 1
            return h

        h = self.hash_contents(path)
        self.stats.hashed += 1
        self.stats.bytes_hashed += st.st_size

        if self.stat_cache:
            self.stat_cache.put(path, st, h)
        return h

    @staticmethod
    def hash_contents(path: Path) -> str:
        """Hash without the stat cache, for files that aren't books in place (scratch, store copies)."""
        hasher = xxhash.xxh3_128()
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
        return HASH_PREFIX + hasher.hexdigest()

    def _entry_dir(self, h: str) -> Path:
        if not HASH_PATTERN.fullmatch(h):
            raise ValueError(f"Not a store hash: {h!r}")
        return self.root / h

    def load(self, h: str) -> StoreEntry | None:
        entry_dir = self._entry_dir(h)
        # metadata.json is written last by put(), so its presence means the entry is complete.
        if not (entry_dir / METADATA_FILE).is_file():
            return None
        return StoreEntry(dir=entry_dir)

    def put(self, h: str, entry: StoreEntry) -> None:
        """
        We write the various store files atomically, and metadata last, so that a partial entry is
        detectable. For instance, if there is no metadata.json file, that's the same as a
        nonexistent entry, except for maybe data recovery.
        """
        entry_dir = self._entry_dir(h)
        entry_dir.mkdir(parents=True, exist_ok=True)
        if entry.ancestor is not None:
            _ = self._entry_dir(entry.ancestor)  # validates
            _write_text_atomic(entry_dir / ANCESTOR_FILE, entry.ancestor + "\n")
        _write_json_atomic(entry_dir / METADATA_RAW_FILE, entry.metadata_raw)
        _write_json_atomic(
            entry_dir / METADATA_INTERNAL_FILE,
            entry.metadata_internal.model_dump(mode="json"),
        )
        _write_json_atomic(
            entry_dir / METADATA_FILE, entry.metadata.model_dump(mode="json")
        )

    def has_content(self, h: str) -> bool:
        return (self._entry_dir(h) / CONTENT_FILE).is_file()

    def put_content(self, h: str, src: Path) -> None:
        """
        Keep a copy of the book's bytes, so commands that replace a book can't lose it. Callers must
        do this before they delete the original.
        """
        entry_dir = self._entry_dir(h)
        if (entry_dir / CONTENT_FILE).is_file():
            return
        entry_dir.mkdir(parents=True, exist_ok=True)
        _copy_atomic(src, entry_dir / CONTENT_FILE)
        # Guards against src changing between hashing and copying.
        if self.hash_contents(entry_dir / CONTENT_FILE) != h:
            (entry_dir / CONTENT_FILE).unlink()
            raise ValueError(f"{src} no longer matches {h}")
