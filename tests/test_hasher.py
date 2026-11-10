import os
from pathlib import Path

import pytest

from efm.hasher import Hasher, StatCache, default_stat_cache_root, hash_contents


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
    hasher = Hasher(cache)
    h = hasher.hash(book)
    assert hasher.hash(book) == h
    assert hasher.stats.hashed == 1
    assert hasher.stats.cache_hits == 1


def test_hit_does_not_open_book(
    cache: StatCache, book: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    hasher = Hasher(cache)
    h = hasher.hash(book)

    def fail(*_args: object, **_kwargs: object):
        raise AssertionError("xxhash used on a cache hit")

    monkeypatch.setattr("efm.hasher.xxhash.xxh3_128", fail)
    assert hasher.hash(book) == h


def test_mtime_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book)
    st = book.stat()
    os.utime(book, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    hasher.hash(book)
    assert hasher.stats.hashed == 2


def test_size_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    hasher = Hasher(cache)
    h1 = hasher.hash(book)
    book.write_bytes(b"woof")
    assert hasher.hash(book) != h1
    assert hasher.stats.hashed == 2


def test_ctime_change_misses(cache: StatCache, book: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book)
    st = book.stat()
    # Same bytes and restored mtime: only ctime differs.
    book.write_bytes(book.read_bytes())
    os.utime(book, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert book.stat().st_ctime_ns != st.st_ctime_ns
    hasher.hash(book)
    assert hasher.stats.hashed == 2


def test_put_keeps_one_key_per_path(cache: StatCache, book: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book)
    book.write_bytes(b"changed")
    hasher.hash(book)
    book_dir = cache.root.joinpath(*book.resolve().parts[1:])
    assert len(list(book_dir.iterdir())) == 1


def test_garbage_key_file_is_a_miss(cache: StatCache, book: Path, tmp_path: Path):
    hasher = Hasher(cache)
    h = hasher.hash(book)
    st = book.stat()
    key = cache.root.joinpath(*book.resolve().parts[1:]) / (
        f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"
    )
    key.write_text("xx_not-a-hash")
    assert cache.get(book, st) is None
    assert hasher.hash(book) == h
    assert hasher.stats.hashed == 2


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
    hasher = Hasher(StatCache(blocker / "stat-cache"))
    assert hasher.hash(book).startswith("xx_")


def test_no_stat_cache_writes_nothing(book: Path, tmp_path: Path):
    hasher = Hasher(None)
    hasher.hash(book)
    hasher.hash(book)
    assert hasher.stats.hashed == 2
    assert not default_stat_cache_root().exists()


def test_default_root_uses_xdg(tmp_path: Path):
    assert default_stat_cache_root() == tmp_path / "xdg-cache" / "efm" / "stat-cache"


def test_hash_is_stable_and_prefixed(tmp_path: Path):
    a = tmp_path / "a"
    a.write_bytes(b"hello")
    b = tmp_path / "b"
    b.write_bytes(b"hello")
    h = hash_contents(a)
    assert h.startswith("xx_") and len(h) == 35
    assert hash_contents(b) == h
    b.write_bytes(b"hello!")
    assert hash_contents(b) != h


def test_default_hasher_uses_default_cache(book: Path):
    Hasher().hash(book)
    assert default_stat_cache_root().exists()


def test_put_cache(cache: StatCache, book: Path):
    hasher = Hasher(cache)
    hasher.put_cache(book, "xx_" + "a" * 32)
    assert hasher.hash(book) == "xx_" + "a" * 32
    assert hasher.stats.hashed == 0
