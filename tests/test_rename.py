import shutil
import sys
from pathlib import Path

import pytest

from efm.__main__ import main
from efm.hasher import Hasher
from tests.book_builders import make_epub

SERIES_META = """
    <meta name="calibre:series" content="Discworld"/>
    <meta name="calibre:series_index" content="17"/>"""


def run_rename(
    monkeypatch: pytest.MonkeyPatch, store_dir: Path, *args: str | Path
) -> int:
    monkeypatch.setattr(
        sys, "argv", ["efm", "--store", str(store_dir), "rename", *map(str, args)]
    )
    return main()


@pytest.fixture
def books_dir(tmp_path: Path) -> Path:
    books_dir = tmp_path / "books"
    (books_dir / "inbox").mkdir(parents=True)
    make_epub(
        books_dir / "inbox" / "a.epub",
        title="Interesting Times",
        author="Terry Pratchett",
        extra_meta=SERIES_META,
    )
    make_epub(books_dir / "b.epub", title="Standalone", author="Someone")
    return books_dir


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "store"


def _files(dir: Path) -> set[str]:
    return {str(p.relative_to(dir)) for p in dir.rglob("*") if p.is_file()}


def test_dry_run_changes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    books_dir: Path,
    store_dir: Path,
):
    before = _files(books_dir)
    assert (
        run_rename(
            monkeypatch, store_dir, "-n", "-f", "{author}/{title}{ext}", books_dir
        )
        == 0
    )
    assert _files(books_dir) == before
    assert capsys.readouterr().out.splitlines() == [
        "b.epub -> Someone/Standalone.epub",
        "inbox/a.epub -> Terry Pratchett/Interesting Times.epub",
    ]


def test_moves_and_cleans_up_empty_dirs(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    assert (
        run_rename(monkeypatch, store_dir, "-f", "{author}/{title}{ext}", books_dir)
        == 0
    )
    assert _files(books_dir) == {
        "Someone/Standalone.epub",
        "Terry Pratchett/Interesting Times.epub",
    }
    assert not (books_dir / "inbox").exists()
    assert books_dir.is_dir()


def test_stat_cache_hit_after_move(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    assert run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", books_dir) == 0
    hasher = Hasher()
    hasher.hash(books_dir / "Standalone.epub")
    assert hasher.stats.cache_hits == 1


def test_second_run_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    books_dir: Path,
    store_dir: Path,
):
    assert run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", books_dir) == 0
    capsys.readouterr()
    assert (
        run_rename(monkeypatch, store_dir, "-n", "-f", "{title}{ext}", books_dir) == 0
    )
    assert capsys.readouterr().out == ""


def test_missing_value_skips_only_that_book(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    assert (
        run_rename(monkeypatch, store_dir, "-f", "{series}/{title}{ext}", books_dir)
        == 1
    )
    assert _files(books_dir) == {"b.epub", "Discworld/Interesting Times.epub"}


def test_yaml_preset_with_variants(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    (books_dir / "efm.yaml").write_text("""
rename:
  default_preset: series_first
  presets:
    series_first:
      - if: series
        value: |
          {series}/{series_index:02} - {title}{ext}
      - '{title} - {author}{ext}'
""")
    assert run_rename(monkeypatch, store_dir, books_dir) == 0
    assert _files(books_dir) == {
        "efm.yaml",
        "Discworld/17 - Interesting Times.epub",
        "Standalone - Someone.epub",
    }


def test_toml_named_preset_and_default_name(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    (books_dir / "efm.toml").write_text("""
[rename.presets]
default = "{title}{ext}"
by_author = [{if = "author", value = "{author}/{title}{ext}"}, "{title}{ext}"]
""")
    assert run_rename(monkeypatch, store_dir, "-p", "by_author", books_dir) == 0
    assert "Someone/Standalone.epub" in _files(books_dir)
    assert run_rename(monkeypatch, store_dir, books_dir) == 0
    assert _files(books_dir) == {
        "efm.toml",
        "Standalone.epub",
        "Interesting Times.epub",
    }


def test_format_overrides_preset(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    (books_dir / "efm.toml").write_text('[rename.presets]\ndefault = "{author}{ext}"\n')
    assert run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", books_dir) == 0
    assert "Standalone.epub" in _files(books_dir)


def test_unknown_preset_is_an_error(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    before = _files(books_dir)
    assert run_rename(monkeypatch, store_dir, "-p", "nope", books_dir) == 1
    assert _files(books_dir) == before


def test_bad_template_moves_nothing(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    before = _files(books_dir)
    assert run_rename(monkeypatch, store_dir, "-f", "{title", books_dir) == 1
    assert _files(books_dir) == before


def test_collision_with_different_file_is_skipped(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    (books_dir / "Standalone.epub").write_text("some other book")
    assert (
        run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", books_dir / "b.epub")
        == 1
    )
    assert (books_dir / "b.epub").exists()
    assert (books_dir / "Standalone.epub").read_text() == "some other book"


def test_collision_with_identical_content_replaces(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    shutil.copyfile(books_dir / "b.epub", books_dir / "Standalone.epub")
    assert (
        run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", books_dir / "b.epub")
        == 0
    )
    assert not (books_dir / "b.epub").exists()
    assert (books_dir / "Standalone.epub").exists()


def test_two_books_to_one_target(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    before = _files(books_dir)
    assert run_rename(monkeypatch, store_dir, "-f", "same{ext}", books_dir) == 1
    assert _files(books_dir) == before


def test_single_file_with_folders_needs_root(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    book_file = books_dir / "inbox" / "a.epub"
    assert (
        run_rename(monkeypatch, store_dir, "-f", "{series}/{title}{ext}", book_file)
        == 1
    )
    assert book_file.exists()
    assert run_rename(monkeypatch, store_dir, "-f", "{title}{ext}", book_file) == 0
    assert (books_dir / "inbox" / "Interesting Times.epub").exists()


def test_root_for_a_subdirectory(
    monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path
):
    args = ("-f", "{series}/{title}{ext}", books_dir / "inbox", "--root", books_dir)
    assert run_rename(monkeypatch, store_dir, *args) == 0
    assert _files(books_dir) == {"b.epub", "Discworld/Interesting Times.epub"}
    assert not (books_dir / "inbox").exists()


def test_rnm_alias(monkeypatch: pytest.MonkeyPatch, books_dir: Path, store_dir: Path):
    monkeypatch.setattr(
        sys,
        "argv",
        ["efm", "--store", str(store_dir), "rnm", "-f", "{title}{ext}", str(books_dir)],
    )
    assert main() == 0
    assert "Standalone.epub" in _files(books_dir)
