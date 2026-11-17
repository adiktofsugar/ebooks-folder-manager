"""Tests for `efm store ...`, which works off hashes rather than paths."""

import json
import sys
from pathlib import Path

import pytest

from efm.__main__ import main
from efm.hasher import hash_contents
from efm.metadata import InternalMetadata, Metadata
from efm.store import Store, StoreEntry


def _run(monkeypatch: pytest.MonkeyPatch, store_dir: Path, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["efm", "--store", str(store_dir), "store", *args])
    return main()


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "store"


@pytest.fixture
def book(tmp_path: Path, store_dir: Path) -> tuple[Path, str]:
    book_file = tmp_path / "book.epub"
    book_file.write_bytes(b"pretend epub " * 5000)
    h = hash_contents(book_file)
    store = Store(store_dir)
    store.put(
        h, StoreEntry(Metadata(size=1, title="T", author="A"), InternalMetadata(), None)
    )
    store.put_content(h, book_file)
    return book_file, h


def test_show_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
    store_dir: Path,
    book: tuple[Path, str],
):
    book_file, h = book
    assert _run(monkeypatch, store_dir, "show", h) == 0
    assert capsysbinary.readouterr().out == book_file.read_bytes()


def test_show_to_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    store_dir: Path,
    book: tuple[Path, str],
):
    book_file, h = book
    out_file = tmp_path / "out.epub"
    assert _run(monkeypatch, store_dir, "show", h, "-o", str(out_file)) == 0
    assert out_file.read_bytes() == book_file.read_bytes()


@pytest.mark.parametrize("h", ["xx_" + "0" * 32, "not-a-hash"])
def test_show_unknown_hash_fails(
    monkeypatch: pytest.MonkeyPatch, store_dir: Path, h: str
):
    assert _run(monkeypatch, store_dir, "show", h) == 1


def test_ancestor_chain(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    store_dir: Path,
):
    store = Store(store_dir)
    h1, h2, h3 = ("xx_" + c * 32 for c in "123")
    store.put(h1, StoreEntry(Metadata(size=1), InternalMetadata(), None))
    store.put(h2, StoreEntry(Metadata(size=1), InternalMetadata(), None, ancestor=h1))
    store.put(h3, StoreEntry(Metadata(size=1), InternalMetadata(), None, ancestor=h2))

    assert _run(monkeypatch, store_dir, "ancestor", h3) == 0
    assert capsys.readouterr().out == h2 + "\n"
    assert _run(monkeypatch, store_dir, "ancestor", "-a", h3) == 0
    assert capsys.readouterr().out == f"{h2}\n{h1}\n"
    assert _run(monkeypatch, store_dir, "ancestor", h1) == 1
    assert capsys.readouterr().out == ""


def test_ls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    store_dir: Path,
    book: tuple[Path, str],
):
    _, h = book
    other = "xx_" + "9" * 32
    Store(store_dir).put(other, StoreEntry(Metadata(size=1), InternalMetadata(), None))

    assert _run(monkeypatch, store_dir, "ls") == 0
    assert capsys.readouterr().out.splitlines() == sorted(
        [f"{h}\tT\tA", f"{other}\t\t"]
    )
    assert _run(monkeypatch, store_dir, "ls", "--has-content", "-f", "json") == 0
    (item,) = json.loads(capsys.readouterr().out)
    assert item["hash"] == h


def test_store_without_subcommand_prints_help(
    monkeypatch: pytest.MonkeyPatch, store_dir: Path
):
    assert _run(monkeypatch, store_dir) == 1


def test_info(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    store_dir: Path,
    book: tuple[Path, str],
):
    assert _run(monkeypatch, store_dir, "info") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"path: {store_dir.resolve()}"
    assert lines[1] == "from: --store"
    assert lines[2] == "books: 1 (1 with content)"
    assert lines[3].startswith("blobs: ")


def test_info_from_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    store_dir: Path,
):
    monkeypatch.setenv("EFM_STORE", str(store_dir))
    monkeypatch.setattr(sys, "argv", ["efm", "store", "info"])
    assert main() == 0
    out = capsys.readouterr().out
    assert f"path: {store_dir.resolve()}\nfrom: $EFM_STORE\n" in out
    assert "doesn't exist yet" in out
