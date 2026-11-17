"""Book bytes as manifests of content-defined chunks, deduplicated across versions. See docs/store.md."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, ClassVar, Literal, assert_never

import xxhash
from fastcdc import fastcdc
from pydantic import BaseModel, ConfigDict, ValidationError

from efm.atomic_util import open_atomic, write_bytes_atomic, write_json_atomic
from efm.exceptions import ContentError, UnsupportedSchemaError
from efm.hasher import HASH_PATTERN, HASH_PREFIX, hash_bytes
from efm.metadata import load_versioned

BOOKS_DIRNAME = "books"
BLOBS_DIRNAME = "blobs"
MANIFEST_FILENAME = "content.json"


class ChunkerParams(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    algo: Literal["fastcdc"]
    min: int
    avg: int
    max: int


# Small next to restic's ~1 MiB, so an edit to a few-MB book only costs a few chunks.
CHUNKER = ChunkerParams(algo="fastcdc", min=4096, avg=16384, max=65536)


class ContentManifestV1(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    size: int
    chunker: ChunkerParams
    chunks: list[str]


ContentManifest = ContentManifestV1
AnyContentManifest = ContentManifestV1
CONTENT_MANIFEST_MODELS: dict[int, type[AnyContentManifest]] = {1: ContentManifestV1}


def migrate_content_manifest(m: AnyContentManifest) -> ContentManifest:
    match m:
        case ContentManifestV1():
            return m
        case _:
            assert_never(m)


def _chunks(file: Path) -> Iterator[bytes]:
    # fastcdc mmaps the file, and an empty file can't be mmapped.
    if file.stat().st_size == 0:
        return
    for chunk in fastcdc(
        str(file), CHUNKER.min, CHUNKER.avg, CHUNKER.max, fat=True, hf=None
    ):
        yield chunk.data


class ContentStore:
    """`books/<hash>/content.json` lists chunk ids; `blobs/<chunk id>` holds each chunk once."""

    books_dir: Path
    blobs_dir: Path

    def __init__(self, root_dir: Path):
        self.books_dir = root_dir / BOOKS_DIRNAME
        self.blobs_dir = root_dir / BLOBS_DIRNAME

    def _manifest_file(self, h: str) -> Path:
        if not HASH_PATTERN.fullmatch(h):
            raise ValueError(f"Not a store hash: {h!r}")
        return self.books_dir / h / MANIFEST_FILENAME

    def has(self, h: str) -> bool:
        return self._manifest_file(h).is_file()

    def put(self, h: str, book_file: Path) -> None:
        manifest_file = self._manifest_file(h)
        if manifest_file.is_file():
            return
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        total = xxhash.xxh3_128()
        chunk_ids: list[str] = []
        size = 0
        for data in _chunks(book_file):
            total.update(data)
            size += len(data)
            chunk_id = hash_bytes(data)
            blob_file = self.blobs_dir / chunk_id
            if not blob_file.is_file():
                write_bytes_atomic(blob_file, data)
            chunk_ids.append(chunk_id)
        # Guards against the book changing between hashing and chunking. Blobs already written
        # are just unreferenced.
        if HASH_PREFIX + total.hexdigest() != h:
            raise ValueError(f"{book_file} no longer matches {h}")
        manifest = ContentManifest(size=size, chunker=CHUNKER, chunks=chunk_ids)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        # Last, so a manifest never points at blobs that weren't written.
        write_json_atomic(manifest_file, manifest.model_dump(mode="json"))

    def _load_manifest(self, h: str) -> ContentManifest:
        manifest_file = self._manifest_file(h)
        try:
            data = json.loads(manifest_file.read_text())
        except FileNotFoundError:
            raise ContentError(f"No content stored for {h}") from None
        except (OSError, json.JSONDecodeError) as e:
            raise ContentError(f"Invalid content manifest {manifest_file} - {e}") from e
        try:
            return migrate_content_manifest(
                load_versioned(data, CONTENT_MANIFEST_MODELS)
            )
        except (ValidationError, UnsupportedSchemaError) as e:
            raise ContentError(f"Invalid content manifest {manifest_file} - {e}") from e

    def get(self, h: str, out: BinaryIO) -> None:
        """
        Write the content of `h` to `out`. Raises ContentError if a chunk is missing or the result
        isn't `h`; by then some bytes may already be written, so use `restore` for files.
        """
        manifest = self._load_manifest(h)
        total = xxhash.xxh3_128()
        for chunk_id in manifest.chunks:
            if not HASH_PATTERN.fullmatch(chunk_id):
                raise ContentError(f"Invalid chunk id {chunk_id!r} in {h}")
            try:
                data = (self.blobs_dir / chunk_id).read_bytes()
            except OSError as e:
                raise ContentError(f"Missing chunk {chunk_id} of {h} - {e}") from e
            if hash_bytes(data) != chunk_id:
                raise ContentError(f"Corrupt chunk {chunk_id} of {h}")
            total.update(data)
            out.write(data)
        if HASH_PREFIX + total.hexdigest() != h:
            raise ContentError(f"Content of {h} doesn't reassemble to {h}")

    def restore(self, h: str, dst_file: Path) -> None:
        """Write the content of `h` to `dst_file`, which is left untouched on failure."""
        with open_atomic(dst_file) as f:
            self.get(h, f)
