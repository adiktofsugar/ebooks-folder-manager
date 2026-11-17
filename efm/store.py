"""Content-addressed metadata store. See docs/store.md."""

import json
import logging
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, BinaryIO, final

from pydantic import ValidationError

from efm.atomic_util import write_json_atomic, write_text_atomic
from efm.content_store import BOOKS_DIRNAME, ContentStore
from efm.exceptions import InvalidStoreEntryError, UnsupportedSchemaError
from efm.hasher import HASH_PATTERN
from efm.metadata import (
    InternalMetadata,
    Metadata,
    extract,
    load_internal_metadata,
    load_metadata,
)

logger = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"
METADATA_INTERNAL_FILENAME = "metadata_internal.json"
METADATA_RAW_FILENAME = "metadata_raw.json"
ANCESTOR_FILENAME = "ancestor"


def default_store_dir() -> Path:
    if store_dirpath := os.environ.get("EFM_STORE"):
        return Path(store_dirpath)
    data_home_dir = Path(
        os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    )
    return data_home_dir / "efm" / "store"


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
    def from_book(cls, book_file: Path, ancestor: str | None = None) -> "StoreEntry":
        extracted = extract(book_file)
        return cls(
            extracted.metadata, extracted.internal, extracted.raw, ancestor=ancestor
        )

    def _read[T](self, name: str, loader: Callable[[object], T]) -> T:
        if self._dir is None:
            raise ValueError(
                f"StoreEntry has no {name} and no store dir to read it from"
            )
        file = self._dir / name
        try:
            return loader(json.loads(file.read_text()))
        except (
            OSError,
            json.JSONDecodeError,
            ValidationError,
            UnsupportedSchemaError,
        ) as e:
            raise InvalidStoreEntryError(file, e) from e

    @property
    def metadata(self) -> Metadata:
        if isinstance(self._metadata, _Unloaded):
            self._metadata = self._read(METADATA_FILENAME, load_metadata)
        return self._metadata

    @property
    def metadata_internal(self) -> InternalMetadata:
        if isinstance(self._metadata_internal, _Unloaded):
            self._metadata_internal = self._read(
                METADATA_INTERNAL_FILENAME, load_internal_metadata
            )
        return self._metadata_internal

    @property
    def metadata_raw(self) -> dict[str, Any] | None:
        if isinstance(self._metadata_raw, _Unloaded):
            self._metadata_raw = self._read(METADATA_RAW_FILENAME, _as_raw)
        return self._metadata_raw

    @property
    def ancestor(self) -> str | None:
        """Hash of the book version this one was derived from (e.g. the .acsm it was fulfilled from)."""
        if isinstance(self._ancestor, _Unloaded):
            assert self._dir is not None
            file = self._dir / ANCESTOR_FILENAME
            try:
                text = file.read_text().strip()
            except FileNotFoundError:
                text = None
            except OSError as e:
                raise InvalidStoreEntryError(file, e) from e
            if text is not None and not HASH_PATTERN.fullmatch(text):
                raise InvalidStoreEntryError(file, ValueError(f"not a hash: {text!r}"))
            self._ancestor = text
        return self._ancestor


def _as_raw(data: object) -> dict[str, Any] | None:
    if data is None or isinstance(data, dict):
        return data
    raise ValueError(f"expected an object or null, got {type(data).__name__}")


class Store:
    root_dir: Path
    books_dir: Path
    content: ContentStore

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.books_dir = root_dir / BOOKS_DIRNAME
        self.content = ContentStore(root_dir)

    def entry_dir(self, h: str) -> Path:
        if not HASH_PATTERN.fullmatch(h):
            raise ValueError(f"Not a store hash: {h!r}")
        return self.books_dir / h

    def hashes(self) -> Iterator[str]:
        if not self.books_dir.is_dir():
            return
        for entry_dir in sorted(self.books_dir.iterdir()):
            if HASH_PATTERN.fullmatch(entry_dir.name):
                yield entry_dir.name

    def load(self, h: str) -> StoreEntry | None:
        entry_dir = self.entry_dir(h)
        # metadata.json is written last by put(), so its presence means the entry is complete.
        if not (entry_dir / METADATA_FILENAME).is_file():
            return None
        return StoreEntry(dir=entry_dir)

    def put(self, h: str, entry: StoreEntry) -> None:
        """
        We write the various store files atomically, and metadata last, so that a partial entry is
        detectable. For instance, if there is no metadata.json file, that's the same as a
        nonexistent entry, except for maybe data recovery.
        """
        entry_dir = self.entry_dir(h)
        entry_dir.mkdir(parents=True, exist_ok=True)
        if entry.ancestor is not None:
            _ = self.entry_dir(entry.ancestor)  # validates
            write_text_atomic(entry_dir / ANCESTOR_FILENAME, entry.ancestor + "\n")
        write_json_atomic(entry_dir / METADATA_RAW_FILENAME, entry.metadata_raw)
        write_json_atomic(
            entry_dir / METADATA_INTERNAL_FILENAME,
            entry.metadata_internal.model_dump(mode="json"),
        )
        write_json_atomic(
            entry_dir / METADATA_FILENAME, entry.metadata.model_dump(mode="json")
        )

    def has_content(self, h: str) -> bool:
        return self.content.has(h)

    def put_content(self, h: str, book_file: Path) -> None:
        """
        Keep the book's bytes, so commands that replace a book can't lose it. Callers must do this
        before they delete the original.
        """
        self.content.put(h, book_file)

    def get_content(self, h: str, out: BinaryIO) -> None:
        self.content.get(h, out)

    def restore_content(self, h: str, dst_file: Path) -> None:
        self.content.restore(h, dst_file)
