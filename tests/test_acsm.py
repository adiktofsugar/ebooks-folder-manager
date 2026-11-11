"""Tests for `efm acsm`. Fulfillment itself is mocked; it needs a real Adobe account."""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from efm.__main__ import main
from efm.commands import acsm
from efm.exceptions import BookError
from efm.hasher import hash_contents
from efm.store import Store

SAMPLE_EPUB_FILE = Path(__file__).parent.parent / "sample-books" / "WorldUnbound.epub"


@pytest.fixture(autouse=True)
def isolated_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """So kept scratch dirs land somewhere the test can see and pytest cleans up."""
    tmp_dir = tmp_path / "tmp"
    tmp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_dir))


@pytest.fixture
def token_file(tmp_path: Path) -> Path:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    token_file = books_dir / "URLLink.acsm"
    token_file.write_text("<fulfillmentToken/>")
    return token_file


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "store"


def _scratch_dirs() -> list[Path]:
    return list(Path(tempfile.gettempdir()).glob("efm-acsm-*"))


def _run(store_dir: Path, *files: Path) -> int:
    sys.argv = ["efm", "--store", str(store_dir), "acsm", *map(str, files)]
    return main()


def _fake_fulfill(acsm_file: Path, out_dir: Path, config: object) -> Path:
    out_file = out_dir / "Some Title.epub"
    shutil.copyfile(SAMPLE_EPUB_FILE, out_file)
    return out_file


def _failing_fulfill(acsm_file: Path, out_dir: Path, config: object) -> Path:
    (out_dir / "partial").write_text("debris")
    raise BookError(acsm_file, message="boom")


def test_replaces_token_and_links_ancestor(
    monkeypatch: pytest.MonkeyPatch, token_file: Path, store_dir: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    token_hash = hash_contents(token_file)

    assert _run(store_dir, token_file) == 0

    book_file = token_file.with_suffix(".epub")
    assert not token_file.exists()
    assert book_file.read_bytes() == SAMPLE_EPUB_FILE.read_bytes()
    assert [path.name for path in token_file.parent.iterdir()] == [book_file.name]

    s = Store(store_dir)
    entry = s.load(hash_contents(book_file))
    assert entry is not None
    assert entry.ancestor == token_hash
    assert entry.metadata.format is not None
    # The deleted token is recoverable from the store.
    assert (store_dir / token_hash / "content").read_text() == "<fulfillmentToken/>"
    original = s.load(token_hash)
    assert original is not None and original.ancestor is None

    assert _scratch_dirs() == []


def test_failure_keeps_token_and_scratch(
    monkeypatch: pytest.MonkeyPatch, token_file: Path, store_dir: Path
):
    monkeypatch.setattr(acsm, "fulfill", _failing_fulfill)

    assert _run(store_dir, token_file) == 1

    assert token_file.exists()
    assert not token_file.with_suffix(".epub").exists()
    [kept_dir] = _scratch_dirs()
    assert (kept_dir / "partial").read_text() == "debris"
    assert (kept_dir / token_file.name).exists()


def test_replaces_existing_epub(
    monkeypatch: pytest.MonkeyPatch, token_file: Path, store_dir: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    token_file.with_suffix(".epub").write_text("existing")

    assert _run(store_dir, token_file) == 0

    assert not token_file.exists()
    assert token_file.with_suffix(".epub").read_bytes() == SAMPLE_EPUB_FILE.read_bytes()


def test_rejects_non_acsm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, store_dir: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    book_file = tmp_path / "book.epub"
    shutil.copyfile(SAMPLE_EPUB_FILE, book_file)

    assert _run(store_dir, book_file) == 1
    assert book_file.read_bytes() == SAMPLE_EPUB_FILE.read_bytes()


def test_one_failure_doesnt_stop_the_rest(
    monkeypatch: pytest.MonkeyPatch, token_file: Path, store_dir: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    missing_file = token_file.parent / "missing.acsm"

    assert _run(store_dir, missing_file, token_file) == 1
    assert token_file.with_suffix(".epub").exists()


def test_needs_adobe_credentials(tmp_path: Path):
    from efm.acsm import fulfill

    with pytest.raises(BookError, match="adobe_user"):
        fulfill(tmp_path / "x.acsm", tmp_path, None)


def test_adl_sign_in_error_becomes_book_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    # Importing adl creates ~/.adl, so keep that out of the real home.
    monkeypatch.setenv("HOME", str(tmp_path))
    import adl.login

    from efm.acsm import fulfill
    from efm.config import Config

    def rejected(user: str, password: str) -> None:
        raise adl.AdeptResetPWRequiredError("E_ADEPT_RESET_PW_REQUIRED x/SignInDirect")

    monkeypatch.setattr(adl.login, "login", rejected)
    config = Config(adobe_user="nobody@example.com", adobe_password="pw")
    with pytest.raises(BookError, match="transition-help"):
        fulfill(tmp_path / "x.acsm", tmp_path, config)
