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

SAMPLE_EPUB = Path(__file__).parent.parent / "sample-books" / "WorldUnbound.epub"


@pytest.fixture(autouse=True)
def isolated_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """So kept scratch dirs land somewhere the test can see and pytest cleans up."""
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))


@pytest.fixture
def token(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    path = books / "URLLink.acsm"
    path.write_text("<fulfillmentToken/>")
    return path


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "store"


def _scratch_dirs() -> list[Path]:
    return list(Path(tempfile.gettempdir()).glob("efm-acsm-*"))


def _run(store: Path, *files: Path) -> int:
    sys.argv = ["efm", "--store", str(store), "acsm", *map(str, files)]
    return main()


def _fake_fulfill(acsm_path: Path, out_dir: Path, config: object) -> Path:
    out = out_dir / "Some Title.epub"
    shutil.copyfile(SAMPLE_EPUB, out)
    return out


def _failing_fulfill(acsm_path: Path, out_dir: Path, config: object) -> Path:
    (out_dir / "partial").write_text("debris")
    raise BookError(acsm_path, message="boom")


def test_replaces_token_and_links_ancestor(
    monkeypatch: pytest.MonkeyPatch, token: Path, store: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    token_hash = hash_contents(token)

    assert _run(store, token) == 0

    target = token.with_suffix(".epub")
    assert not token.exists()
    assert target.read_bytes() == SAMPLE_EPUB.read_bytes()
    assert [p.name for p in token.parent.iterdir()] == [target.name]

    s = Store(store)
    entry = s.load(hash_contents(target))
    assert entry is not None
    assert entry.ancestor == token_hash
    assert entry.metadata.format is not None
    # The deleted token is recoverable from the store.
    assert (store / token_hash / "content").read_text() == "<fulfillmentToken/>"
    original = s.load(token_hash)
    assert original is not None and original.ancestor is None

    assert _scratch_dirs() == []


def test_failure_keeps_token_and_scratch(
    monkeypatch: pytest.MonkeyPatch, token: Path, store: Path
):
    monkeypatch.setattr(acsm, "fulfill", _failing_fulfill)

    assert _run(store, token) == 1

    assert token.exists()
    assert not token.with_suffix(".epub").exists()
    [kept] = _scratch_dirs()
    assert (kept / "partial").read_text() == "debris"
    assert (kept / token.name).exists()


def test_replaces_existing_epub(
    monkeypatch: pytest.MonkeyPatch, token: Path, store: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    token.with_suffix(".epub").write_text("existing")

    assert _run(store, token) == 0

    assert not token.exists()
    assert token.with_suffix(".epub").read_bytes() == SAMPLE_EPUB.read_bytes()


def test_rejects_non_acsm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, store: Path):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    book = tmp_path / "book.epub"
    shutil.copyfile(SAMPLE_EPUB, book)

    assert _run(store, book) == 1
    assert book.read_bytes() == SAMPLE_EPUB.read_bytes()


def test_one_failure_doesnt_stop_the_rest(
    monkeypatch: pytest.MonkeyPatch, token: Path, store: Path
):
    monkeypatch.setattr(acsm, "fulfill", _fake_fulfill)
    missing = token.parent / "missing.acsm"

    assert _run(store, missing, token) == 1
    assert token.with_suffix(".epub").exists()


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
