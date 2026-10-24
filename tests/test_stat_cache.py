import os
from pathlib import Path

import pytest

from efm.stat_cache import StatCache, default_stat_cache_root
from efm.store import Store


@pytest.fixture
def cache(tmp_path: Path) -> StatCache:
    return StatCache(tmp_path / "stat-cache")


@pytest.fixture
def book(tmp_path: Path) -> Path:
    p = tmp_path / "lib" / "Cats.epub"
    p.parent.mkdir()
    p.write_bytes(b"meow" * 100)
    return p


def test_hit_skips_hashing(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    h = store.hash_file(book)
    assert store.hash_file(book) == h
    assert store.stats.hashed == 1
    assert store.stats.cache_hits == 1


def test_hit_does_not_open_book(
    cache: StatCache, book: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    store = Store(tmp_path / "store", cache)
    h = store.hash_file(book)

    def fail(*_args: object, **_kwargs: object):
        raise AssertionError("xxhash used on a cache hit")

    monkeypatch.setattr("efm.store.xxhash.xxh3_128", fail)
    assert store.hash_file(book) == h


def test_mtime_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    store.hash_file(book)
    st = book.stat()
    os.utime(book, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    store.hash_file(book)
    assert store.stats.hashed == 2


def test_size_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    h1 = store.hash_file(book)
    book.write_bytes(b"woof")
    assert store.hash_file(book) != h1
    assert store.stats.hashed == 2


def test_ctime_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    store.hash_file(book)
    st = book.stat()
    # Same bytes and restored mtime: only ctime differs.
    book.write_bytes(book.read_bytes())
    os.utime(book, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert book.stat().st_ctime_ns != st.st_ctime_ns
    store.hash_file(book)
    assert store.stats.hashed == 2


def test_put_keeps_one_key_per_path(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    store.hash_file(book)
    book.write_bytes(b"changed")
    store.hash_file(book)
    book_dir = cache.root.joinpath(*book.resolve().parts[1:])
    assert len(list(book_dir.iterdir())) == 1


def test_garbage_key_file_is_a_miss(cache: StatCache, book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", cache)
    h = store.hash_file(book)
    st = book.stat()
    key = cache.root.joinpath(*book.resolve().parts[1:]) / (
        f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"
    )
    key.write_text("xx_not-a-hash")
    assert store.hash_file(book) == h
    assert store.stats.hashed == 2


def test_key_path_that_is_a_dir_is_a_miss(cache: StatCache, book: Path):
    st = book.stat()
    key = cache.root.joinpath(*book.resolve().parts[1:]) / (
        f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"
    )
    key.mkdir(parents=True)
    assert cache.get(book, st) is None


def test_unwritable_root_still_hashes(book: Path, tmp_path: Path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the cache dir should be")
    store = Store(tmp_path / "store", StatCache(blocker / "stat-cache"))
    assert store.hash_file(book).startswith("xx_")


def test_no_stat_cache_writes_nothing(book: Path, tmp_path: Path):
    store = Store(tmp_path / "store", None)
    store.hash_file(book)
    store.hash_file(book)
    assert store.stats.hashed == 2
    assert not default_stat_cache_root().exists()


def test_default_root_uses_xdg(tmp_path: Path):
    assert default_stat_cache_root() == tmp_path / "xdg-cache" / "efm" / "stat-cache"
