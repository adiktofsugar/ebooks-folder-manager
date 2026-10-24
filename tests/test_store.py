import json
from pathlib import Path

import pytest

from efm.exceptions import InvalidStoreEntryError
from efm.metadata import InternalMetadata, Metadata
from efm.store import Store, StoreEntry, default_store_dir


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store", None)


def test_hash_file_is_stable_and_prefixed(store: Store, tmp_path: Path):
    a = tmp_path / "a"
    a.write_bytes(b"hello")
    b = tmp_path / "b"
    b.write_bytes(b"hello")
    h = store.hash_file(a)
    assert h.startswith("xx_") and len(h) == 35
    assert store.hash_file(b) == h
    b.write_bytes(b"hello!")
    assert store.hash_file(b) != h


def test_load_unknown_hash(store: Store):
    assert store.load("xx_" + "0" * 32) is None


def test_load_rejects_non_hash(store: Store):
    with pytest.raises(ValueError):
        store.load("../etc")


def test_put_then_load_round_trips(store: Store, sample_books: Path):
    book = sample_books / "WorldUnbound.epub"
    h = store.hash_file(book)
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
    h = store.hash_file(book)
    store.put(h, StoreEntry.from_book(book))
    assert json.loads((store.root / h / "metadata_raw.json").read_text()) is None
    loaded = store.load(h)
    assert loaded is not None and loaded.metadata_raw is None


def test_internal_metadata_written(store: Store, sample_books: Path):
    book = sample_books / "Emotions.pdf"
    h = store.hash_file(book)
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
