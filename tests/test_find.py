import json
import sys
from pathlib import Path

import pytest

from efm.__main__ import main
from efm.store import StoreEntry


def run_find(
    monkeypatch: pytest.MonkeyPatch,
    store: Path,
    *args: str,
    global_args: tuple[str, ...] = (),
) -> int:
    monkeypatch.setattr(
        sys, "argv", ["efm", "--store", str(store), *global_args, "find", *args]
    )
    # Wide enough that titles aren't folded across lines.
    monkeypatch.setenv("COLUMNS", "200")
    return main()


def test_default_is_one_line_per_book(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    assert run_find(monkeypatch, tmp_path / "store", str(sample_books)) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 4
    assert "InterestingTimes.epub\tInteresting Times\tTerry Pratchett" in lines
    assert len(list((tmp_path / "store").iterdir())) == 4


def test_table_lists_titles(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books), "-f", "table")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    out = capsys.readouterr().out
    assert "Interesting Times" in out
    assert "Terry Pratchett" in out
    assert "encryption: none" in out
    assert len(list((tmp_path / "store").iterdir())) == 4


def test_second_run_uses_store(
    monkeypatch: pytest.MonkeyPatch, sample_books: Path, tmp_path: Path
):
    assert run_find(monkeypatch, tmp_path / "store", str(sample_books)) == 0

    def fail(_path: Path) -> StoreEntry:
        raise AssertionError("re-extracted a book already in the store")

    monkeypatch.setattr(StoreEntry, "from_book", fail)
    assert run_find(monkeypatch, tmp_path / "store", str(sample_books)) == 0
    # Without the stat cache it re-hashes, but still finds the entries.
    assert (
        run_find(
            monkeypatch,
            tmp_path / "store",
            str(sample_books),
            global_args=("--no-stat-cache",),
        )
        == 0
    )


def test_json_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    assert (
        run_find(monkeypatch, tmp_path / "store", str(sample_books), "-f", "json") == 0
    )
    data = json.loads(capsys.readouterr().out)
    by_name = {Path(d["path"]).name: d for d in data}
    assert set(by_name) == {
        "1Q84.epub",
        "Emotions.pdf",
        "InterestingTimes.epub",
        "WorldUnbound.epub",
    }
    assert by_name["InterestingTimes.epub"]["metadata"]["title"] == "Interesting Times"
    assert by_name["InterestingTimes.epub"]["hash"].startswith("xx_")


def test_raw_json_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    (sample_books / "token.acsm").write_text("<fulfillmentToken/>")
    args = (str(sample_books), "--raw", "-f", "json")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    by_name = {Path(d["path"]).name: d for d in json.loads(capsys.readouterr().out)}
    assert by_name["Emotions.pdf"]["metadata"]["metadata"]["format"] == "PDF 1.3"
    assert by_name["token.acsm"]["metadata"] is None


def test_raw_table(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books), "--raw", "-f", "table")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    out = capsys.readouterr().out
    assert "creationDate" in out  # raw pymupdf key name, not normalized


def test_filters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books), "Interesting", "-f", "json")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    data = json.loads(capsys.readouterr().out)
    assert [Path(d["path"]).name for d in data] == ["InterestingTimes.epub"]


def test_single_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books / "Emotions.pdf"), "-f", "json")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1


def test_broken_store_entry_reported(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    store = tmp_path / "store"
    assert run_find(monkeypatch, store, str(sample_books / "Emotions.pdf")) == 0
    (entry_dir,) = store.iterdir()
    (entry_dir / "metadata.json").write_text("{broken")
    _ = capsys.readouterr()
    args = (str(sample_books / "Emotions.pdf"), "-f", "json")
    assert run_find(monkeypatch, store, *args) == 1
    (item,) = json.loads(capsys.readouterr().out)
    assert "Invalid store file" in item["error"]


def test_recurses(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    nested = sample_books / "a" / "b"
    nested.mkdir(parents=True)
    (sample_books / "Emotions.pdf").rename(nested / "Emotions.pdf")
    assert (
        run_find(monkeypatch, tmp_path / "store", str(sample_books), "-f", "json") == 0
    )
    paths = [Path(d["path"]) for d in json.loads(capsys.readouterr().out)]
    assert nested / "Emotions.pdf" in paths
    assert len(paths) == 4


@pytest.mark.parametrize(
    ("filter_args", "expected"),
    [
        (("--author", "pratchett"), {"InterestingTimes.epub"}),
        (("--title", "^interesting"), {"InterestingTimes.epub"}),
        (("--book-format", "pdf"), {"Emotions.pdf"}),
        (("--book-format", "epub", "--author", "pratchett"), {"InterestingTimes.epub"}),
        (("--no-encrypted", "--book-format", "pdf"), {"Emotions.pdf"}),
    ],
)
def test_metadata_filters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
    filter_args: tuple[str, ...],
    expected: set[str],
):
    args = (str(sample_books), *filter_args, "-f", "json")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    names = {Path(d["path"]).name for d in json.loads(capsys.readouterr().out)}
    assert names == expected


def test_missing_filter(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    (sample_books / "token.acsm").write_text("<fulfillmentToken/>")
    args = (str(sample_books), "--missing", "title", "-f", "json")
    assert run_find(monkeypatch, tmp_path / "store", *args) == 0
    names = {Path(d["path"]).name for d in json.loads(capsys.readouterr().out)}
    assert "token.acsm" in names
    assert "InterestingTimes.epub" not in names


def test_line_fields_stay_on_one_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    store = tmp_path / "store"
    assert run_find(monkeypatch, store, str(sample_books / "Emotions.pdf")) == 0
    (entry_dir,) = store.iterdir()
    meta = json.loads((entry_dir / "metadata.json").read_text())
    meta["title"] = "Two\nLines\tand a tab"
    (entry_dir / "metadata.json").write_text(json.dumps(meta))
    _ = capsys.readouterr()
    assert run_find(monkeypatch, store, str(sample_books / "Emotions.pdf")) == 0
    (line,) = capsys.readouterr().out.splitlines()
    assert line.split("\t")[:2] == ["Emotions.pdf", "Two Lines and a tab"]
