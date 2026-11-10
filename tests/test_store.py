import json
from pathlib import Path

import pytest

from efm.exceptions import InvalidStoreEntryError
from efm.hasher import hash_contents
from efm.metadata import InternalMetadata, Metadata
from efm.store import Store, StoreEntry, default_store_dir


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


def test_load_unknown_hash(store: Store):
    assert store.load("xx_" + "0" * 32) is None


def test_load_rejects_non_hash(store: Store):
    with pytest.raises(ValueError):
        store.load("../etc")


def test_put_then_load_round_trips(store: Store, sample_books: Path):
    book = sample_books / "WorldUnbound.epub"
    h = hash_contents(book)
    created = StoreEntry.from_book(book)
    store.put(h, created)

    loaded = store.load(h)
    assert loaded is not None
    assert loaded.metadata == created.metadata
    assert loaded.metadata_internal == created.metadata_internal
    assert loaded.metadata_raw == created.metadata_raw


def test_loaded_entry_reads_lazily(store: Store):
    h = "xx_" + "1" * 32
    store.put(h, StoreEntry(Metadata(size=1), InternalMetadata(), None))
    entry_dir = store.root / h
    (entry_dir / "metadata_raw.json").write_text("{broken")

    entry = store.load(h)
    assert entry is not None
    assert entry.metadata.size == 1  # unaffected by the broken raw file
    with pytest.raises(InvalidStoreEntryError):
        _ = entry.metadata_raw


def test_unsupported_format_writes_null_raw(store: Store, tmp_path: Path):
    book = tmp_path / "x.acsm"
    book.write_text("<fulfillmentToken/>")
    h = hash_contents(book)
    store.put(h, StoreEntry.from_book(book))
    assert json.loads((store.root / h / "metadata_raw.json").read_text()) is None
    loaded = store.load(h)
    assert loaded is not None and loaded.metadata_raw is None


def test_internal_metadata_written(store: Store, sample_books: Path):
    book = sample_books / "Emotions.pdf"
    h = hash_contents(book)
    store.put(h, StoreEntry.from_book(book))
    data = json.loads((store.root / h / "metadata_internal.json").read_text())
    assert data == {
        "schema_version": 1,
        "is_k2pdfopt_version": False,
        "cover_image_hash": None,
    }


def test_incomplete_entry_counts_as_missing(store: Store):
    h = "xx_" + "2" * 32
    (store.root / h).mkdir(parents=True)
    (store.root / h / "metadata_raw.json").write_text("null")
    assert store.load(h) is None


def test_newer_schema_is_an_error_not_a_regen(store: Store):
    h = "xx_" + "3" * 32
    store.put(h, StoreEntry(Metadata(size=1), InternalMetadata(), None))
    path = store.root / h / "metadata.json"
    path.write_text(json.dumps({"schema_version": 99}))
    entry = store.load(h)
    assert entry is not None
    with pytest.raises(InvalidStoreEntryError):
        _ = entry.metadata
    assert json.loads(path.read_text()) == {"schema_version": 99}


def test_default_store_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    assert default_store_dir() == tmp_path / "xdg-data" / "efm" / "store"
    monkeypatch.setenv("EFM_STORE", str(tmp_path / "custom"))
    assert default_store_dir() == tmp_path / "custom"


def test_ancestor_round_trips(store: Store):
    parent = "xx_" + "2" * 32
    child = "xx_" + "3" * 32
    store.put(
        child, StoreEntry(Metadata(size=1), InternalMetadata(), None, ancestor=parent)
    )
    store.put(parent, StoreEntry(Metadata(size=1), InternalMetadata(), None))

    loaded_child = store.load(child)
    loaded_parent = store.load(parent)
    assert loaded_child is not None and loaded_child.ancestor == parent
    assert loaded_parent is not None and loaded_parent.ancestor is None


def test_put_rejects_bad_ancestor(store: Store):
    with pytest.raises(ValueError):
        store.put(
            "xx_" + "4" * 32,
            StoreEntry(Metadata(size=1), InternalMetadata(), None, ancestor="../x"),
        )


def test_invalid_ancestor_file(store: Store):
    h = "xx_" + "5" * 32
    store.put(h, StoreEntry(Metadata(size=1), InternalMetadata(), None))
    (store.root / h / "ancestor").write_text("garbage\n")
    entry = store.load(h)
    assert entry is not None
    with pytest.raises(InvalidStoreEntryError):
        _ = entry.ancestor


def test_put_content(store: Store, tmp_path: Path):
    book = tmp_path / "book"
    book.write_bytes(b"contents")
    h = hash_contents(book)
    assert not store.has_content(h)
    store.put_content(h, book)
    assert store.has_content(h)
    assert (store.root / h / "content").read_bytes() == b"contents"
    # Not a complete entry until metadata is put.
    assert store.load(h) is None


def test_put_content_rejects_mismatch(store: Store, tmp_path: Path):
    book = tmp_path / "book"
    book.write_bytes(b"contents")
    with pytest.raises(ValueError):
        store.put_content("xx_" + "6" * 32, book)
    assert not store.has_content("xx_" + "6" * 32)
