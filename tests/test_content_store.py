import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from efm.content_store import ContentStore
from efm.exceptions import ContentError
from efm.hasher import hash_contents


@pytest.fixture
def content(tmp_path: Path) -> ContentStore:
    return ContentStore(tmp_path / "store")


def _random_bytes(n: int, seed: int = 0) -> bytes:
    return random.Random(seed).randbytes(n)


def _put(content: ContentStore, file: Path) -> str:
    h = hash_contents(file)
    content.put(h, file)
    return h


def _blob_names(content: ContentStore) -> set[str]:
    return {f.name for f in content.blobs_dir.iterdir()}


def _get(content: ContentStore, h: str) -> bytes:
    out = io.BytesIO()
    content.get(h, out)
    return out.getvalue()


def test_round_trip(content: ContentStore, tmp_path: Path):
    data = _random_bytes(300_000)
    book_file = tmp_path / "book"
    book_file.write_bytes(data)
    h = _put(content, book_file)
    assert content.has(h)
    assert _get(content, h) == data
    assert len(_blob_names(content)) > 1


def test_empty_file_round_trips(content: ContentStore, tmp_path: Path):
    book_file = tmp_path / "empty"
    book_file.write_bytes(b"")
    h = _put(content, book_file)
    assert _get(content, h) == b""


def test_mismatched_hash_writes_no_manifest(content: ContentStore, tmp_path: Path):
    book_file = tmp_path / "book"
    book_file.write_bytes(b"contents")
    h = "xx_" + "6" * 32
    with pytest.raises(ValueError):
        content.put(h, book_file)
    assert not content.has(h)


def test_put_again_is_a_no_op(content: ContentStore, tmp_path: Path):
    book_file = tmp_path / "book"
    book_file.write_bytes(_random_bytes(100_000))
    h = _put(content, book_file)
    manifest_file = content.books_dir / h / "content.json"
    before = manifest_file.stat().st_mtime_ns
    content.put(h, book_file)
    assert manifest_file.stat().st_mtime_ns == before


def test_unknown_hash_raises(content: ContentStore):
    with pytest.raises(ContentError):
        _get(content, "xx_" + "0" * 32)


def test_missing_blob_raises(content: ContentStore, tmp_path: Path):
    book_file = tmp_path / "book"
    book_file.write_bytes(_random_bytes(100_000))
    h = _put(content, book_file)
    next(content.blobs_dir.iterdir()).unlink()
    with pytest.raises(ContentError):
        _get(content, h)


def test_corrupt_blob_raises_and_restore_keeps_dst(
    content: ContentStore, tmp_path: Path
):
    book_file = tmp_path / "book"
    book_file.write_bytes(_random_bytes(100_000))
    h = _put(content, book_file)
    blob_file = (
        content.blobs_dir
        / json.loads((content.books_dir / h / "content.json").read_text())["chunks"][-1]
    )
    blob_file.write_bytes(b"not the chunk")

    dst_file = tmp_path / "dst"
    dst_file.write_bytes(b"keep me")
    with pytest.raises(ContentError):
        content.restore(h, dst_file)
    assert dst_file.read_bytes() == b"keep me"
    assert [f.name for f in tmp_path.iterdir() if f.name.startswith(".tmp-")] == []


def test_restore_writes_file(content: ContentStore, tmp_path: Path):
    data = _random_bytes(100_000)
    book_file = tmp_path / "book"
    book_file.write_bytes(data)
    h = _put(content, book_file)
    dst_file = tmp_path / "dst"
    content.restore(h, dst_file)
    assert dst_file.read_bytes() == data


def test_inserted_byte_reuses_most_chunks(content: ContentStore, tmp_path: Path):
    data = _random_bytes(2_000_000)
    a_file, b_file = tmp_path / "a", tmp_path / "b"
    a_file.write_bytes(data)
    b_file.write_bytes(data[:1_000_000] + b"!" + data[1_000_000:])
    _put(content, a_file)
    before = _blob_names(content)
    h = _put(content, b_file)
    new = _blob_names(content) - before
    assert len(new) <= 3, f"{len(new)} new of {len(before)}"
    assert _get(content, h) == b_file.read_bytes()


def _epub(file: Path, description: str, body: bytes) -> Path:
    # The OPF comes first, so a change to it shifts every byte after it.
    opf = f'<package version="2.0"><metadata><dc:description>{description}</dc:description></metadata></package>'
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/images/cover.jpg", body, compress_type=zipfile.ZIP_STORED)
    return file


def test_description_edit_dedups(content: ContentStore, tmp_path: Path):
    body = _random_bytes(1_000_000)
    _put(content, _epub(tmp_path / "v1.epub", "A book.", body))
    before = _blob_names(content)
    v2_file = _epub(tmp_path / "v2.epub", "A slightly longer description.", body)
    h = _put(content, v2_file)
    new = _blob_names(content) - before
    # The start (with the OPF), the end (central directory), and maybe one resync chunk.
    assert len(new) <= 4, f"{len(new)} new of {len(before)}"
    assert _get(content, h) == v2_file.read_bytes()
