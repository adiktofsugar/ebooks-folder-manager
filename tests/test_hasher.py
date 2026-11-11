import os
from pathlib import Path

import pytest

from efm.hasher import Hasher, StatCache, default_stat_cache_root, hash_contents


@pytest.fixture
def cache(tmp_path: Path) -> StatCache:
    return StatCache(tmp_path / "stat-cache")


@pytest.fixture
def book_file(tmp_path: Path) -> Path:
    book_file = tmp_path / "lib" / "Cats.epub"
    book_file.parent.mkdir()
    book_file.write_bytes(b"meow" * 100)
    return book_file


def test_hit_skips_hashing(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    h = hasher.hash(book_file)
    assert hasher.hash(book_file) == h
    assert hasher.stats.hashed == 1
    assert hasher.stats.cache_hits == 1


def test_hit_does_not_open_book(
    cache: StatCache, book_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    hasher = Hasher(cache)
    h = hasher.hash(book_file)

    def fail(*_args: object, **_kwargs: object):
        raise AssertionError("xxhash used on a cache hit")

    monkeypatch.setattr("efm.hasher.xxhash.xxh3_128", fail)
    assert hasher.hash(book_file) == h


def test_mtime_change_misses(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book_file)
    st = book_file.stat()
    os.utime(book_file, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    hasher.hash(book_file)
    assert hasher.stats.hashed == 2


def test_size_change_misses(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    h1 = hasher.hash(book_file)
    book_file.write_bytes(b"woof")
    assert hasher.hash(book_file) != h1
    assert hasher.stats.hashed == 2


def test_ctime_change_misses(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book_file)
    st = book_file.stat()
    # Same bytes and restored mtime: only ctime differs.
    book_file.write_bytes(book_file.read_bytes())
    os.utime(book_file, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert book_file.stat().st_ctime_ns != st.st_ctime_ns
    hasher.hash(book_file)
    assert hasher.stats.hashed == 2


def test_put_keeps_one_key_per_path(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    hasher.hash(book_file)
    book_file.write_bytes(b"changed")
    hasher.hash(book_file)
    book_dir = cache.root_dir.joinpath(*book_file.resolve().parts[1:])
    assert len(list(book_dir.iterdir())) == 1


def test_garbage_key_file_is_a_miss(cache: StatCache, book_file: Path, tmp_path: Path):
    hasher = Hasher(cache)
    h = hasher.hash(book_file)
    st = book_file.stat()
    key_file = cache.root_dir.joinpath(*book_file.resolve().parts[1:]) / (
        f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"
    )
    key_file.write_text("xx_not-a-hash")
    assert cache.get(book_file, st) is None
    assert hasher.hash(book_file) == h
    assert hasher.stats.hashed == 2


def test_key_path_that_is_a_dir_is_a_miss(cache: StatCache, book_file: Path):
    st = book_file.stat()
    key_path = cache.root_dir.joinpath(*book_file.resolve().parts[1:]) / (
        f"{st.st_size}-{st.st_mtime_ns}-{st.st_ctime_ns}"
    )
    key_path.mkdir(parents=True)
    assert cache.get(book_file, st) is None


def test_unwritable_root_still_hashes(book_file: Path, tmp_path: Path):
    blocker_file = tmp_path / "blocker"
    blocker_file.write_text("a file where the cache dir should be")
    hasher = Hasher(StatCache(blocker_file / "stat-cache"))
    assert hasher.hash(book_file).startswith("xx_")


def test_no_stat_cache_writes_nothing(book_file: Path, tmp_path: Path):
    hasher = Hasher(None)
    hasher.hash(book_file)
    hasher.hash(book_file)
    assert hasher.stats.hashed == 2
    assert not default_stat_cache_root().exists()


def test_default_root_uses_xdg(tmp_path: Path):
    assert default_stat_cache_root() == tmp_path / "xdg-cache" / "efm" / "stat-cache"


def test_hash_is_stable_and_prefixed(tmp_path: Path):
    a_file = tmp_path / "a"
    a_file.write_bytes(b"hello")
    b_file = tmp_path / "b"
    b_file.write_bytes(b"hello")
    h = hash_contents(a_file)
    assert h.startswith("xx_") and len(h) == 35
    assert hash_contents(b_file) == h
    b_file.write_bytes(b"hello!")
    assert hash_contents(b_file) != h


def test_default_hasher_uses_default_cache(book_file: Path):
    Hasher().hash(book_file)
    assert default_stat_cache_root().exists()


def test_put_cache(cache: StatCache, book_file: Path):
    hasher = Hasher(cache)
    hasher.put_cache(book_file, "xx_" + "a" * 32)
    assert hasher.hash(book_file) == "xx_" + "a" * 32
    assert hasher.stats.hashed == 0
