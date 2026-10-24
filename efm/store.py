"""Content-addressed metadata store. See docs/store.md."""

import json
import logging
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, final

import xxhash
from pydantic import ValidationError

from efm.exceptions import InvalidStoreEntryError, UnsupportedSchemaError
from efm.metadata import (
    InternalMetadata,
    Metadata,
    extract,
    load_internal_metadata,
    load_metadata,
)
from efm.stat_cache import StatCache

logger = logging.getLogger(__name__)

HASH_PREFIX = "xx_"
HASH_PATTERN = re.compile(r"xx_[0-9a-f]{32}")
CHUNK_SIZE = 1 << 20

METADATA_FILE = "metadata.json"
METADATA_INTERNAL_FILE = "metadata_internal.json"
METADATA_RAW_FILE = "metadata_raw.json"


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

    def __init__(
        self,
        metadata: Metadata | _Unloaded = _UNLOADED,
        metadata_internal: InternalMetadata | _Unloaded = _UNLOADED,
        metadata_raw: dict[str, Any] | None | _Unloaded = _UNLOADED,
        dir: Path | None = None,
    ):
        self._dir = dir
        self._metadata = metadata
        self._metadata_internal = metadata_internal
        self._metadata_raw = metadata_raw

    @classmethod
    def from_book(cls, path: Path) -> "StoreEntry":
        extracted = extract(path)
        return cls(extracted.metadata, extracted.internal, extracted.raw)

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

    def hash_file(self, path: Path) -> str:
        # Stat before reading, so a change during hashing makes the cached key stale.
        st = path.stat()
        if self.stat_cache:
            h = self.stat_cache.get(path, st)
            # A partial or foreign key file must never pass as a hash.
            if h and HASH_PATTERN.fullmatch(h):
                self.stats.cache_hits += 1
                return h

        hasher = xxhash.xxh3_128()
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
        h = HASH_PREFIX + hasher.hexdigest()
        self.stats.hashed += 1
        self.stats.bytes_hashed += st.st_size

        if self.stat_cache:
            self.stat_cache.put(path, st, h)
        return h

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
        entry_dir = self._entry_dir(h)
        entry_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(entry_dir / METADATA_RAW_FILE, entry.metadata_raw)
        _write_json_atomic(
            entry_dir / METADATA_INTERNAL_FILE,
            entry.metadata_internal.model_dump(mode="json"),
        )
        _write_json_atomic(
            entry_dir / METADATA_FILE, entry.metadata.model_dump(mode="json")
        )
