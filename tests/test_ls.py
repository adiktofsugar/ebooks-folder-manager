import json
import sys
from pathlib import Path

import pytest

from efm.__main__ import main
from efm.store import StoreEntry


def run_ls(
    monkeypatch: pytest.MonkeyPatch,
    store: Path,
    *args: str,
    global_args: tuple[str, ...] = (),
) -> int:
    monkeypatch.setattr(
        sys, "argv", ["efm", "--store", str(store), *global_args, "ls", *args]
    )
    # Wide enough that titles aren't folded across lines.
    monkeypatch.setenv("COLUMNS", "200")
    return main()


def test_table_lists_titles(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    assert run_ls(monkeypatch, tmp_path / "store", str(sample_books)) == 0
    out = capsys.readouterr().out
    assert "Interesting Times" in out
    assert "Terry Pratchett" in out
    assert "encryption: none" in out
    assert len(list((tmp_path / "store").iterdir())) == 4


def test_second_run_uses_store(
    monkeypatch: pytest.MonkeyPatch, sample_books: Path, tmp_path: Path
):
    assert run_ls(monkeypatch, tmp_path / "store", str(sample_books)) == 0

    def fail(_path: Path) -> StoreEntry:
        raise AssertionError("re-extracted a book already in the store")

    monkeypatch.setattr(StoreEntry, "from_book", fail)
    assert run_ls(monkeypatch, tmp_path / "store", str(sample_books)) == 0
    # Without the stat cache it re-hashes, but still finds the entries.
    assert (
        run_ls(
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
    assert run_ls(monkeypatch, tmp_path / "store", str(sample_books), "-f", "json") == 0
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
    assert run_ls(monkeypatch, tmp_path / "store", *args) == 0
    by_name = {Path(d["path"]).name: d for d in json.loads(capsys.readouterr().out)}
    assert by_name["Emotions.pdf"]["metadata"]["metadata"]["format"] == "PDF 1.3"
    assert by_name["token.acsm"]["metadata"] is None


def test_raw_table(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    assert run_ls(monkeypatch, tmp_path / "store", str(sample_books), "--raw") == 0
    out = capsys.readouterr().out
    assert "creationDate" in out  # raw pymupdf key name, not normalized


def test_filters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books), "Interesting", "-f", "json")
    assert run_ls(monkeypatch, tmp_path / "store", *args) == 0
    data = json.loads(capsys.readouterr().out)
    assert [Path(d["path"]).name for d in data] == ["InterestingTimes.epub"]


def test_single_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (str(sample_books / "Emotions.pdf"), "-f", "json")
    assert run_ls(monkeypatch, tmp_path / "store", *args) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1


def test_broken_store_entry_reported(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    store = tmp_path / "store"
    assert run_ls(monkeypatch, store, str(sample_books / "Emotions.pdf")) == 0
    (entry_dir,) = store.iterdir()
    (entry_dir / "metadata.json").write_text("{broken")
    _ = capsys.readouterr()
    args = (str(sample_books / "Emotions.pdf"), "-f", "json")
    assert run_ls(monkeypatch, store, *args) == 1
    (item,) = json.loads(capsys.readouterr().out)
    assert "Invalid store file" in item["error"]
