import json
import sys
from pathlib import Path

import pytest

from efm.__main__ import main


def run_ls(monkeypatch: pytest.MonkeyPatch, store: Path, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["efm", "--store", str(store), "ls", *args])
    # Wide enough that titles aren't folded across lines.
    monkeypatch.setenv("COLUMNS", "200")
    return main()


@pytest.fixture
def nested_books(sample_books: Path) -> Path:
    sub = sample_books / "sub"
    sub.mkdir()
    (sample_books / "Emotions.pdf").rename(sub / "Emotions.pdf")
    (sample_books / ".hidden.epub").write_bytes(b"")
    return sample_books


def test_does_not_recurse(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nested_books: Path,
    tmp_path: Path,
):
    assert run_ls(monkeypatch, tmp_path / "store", str(nested_books), "-f", "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert [Path(d["path"]).name for d in data] == [
        "1Q84.epub",
        "InterestingTimes.epub",
        "WorldUnbound.epub",
        "sub",
    ]
    assert data[-1] == {"path": str(nested_books / "sub"), "directory": True}
    # The subdirectory's book was never read.
    assert len(list((tmp_path / "store").iterdir())) == 3


def test_table_shows_dirs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nested_books: Path,
    tmp_path: Path,
):
    args = (str(nested_books), "-f", "table")
    assert run_ls(monkeypatch, tmp_path / "store", *args) == 0
    out = capsys.readouterr().out
    assert "sub/" in out
    assert "Interesting Times" in out
    assert "Emotions" not in out


def test_lines_show_dirs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nested_books: Path,
    tmp_path: Path,
):
    assert run_ls(monkeypatch, tmp_path / "store", str(nested_books)) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "sub/"


def test_defaults_to_cwd(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nested_books: Path,
    tmp_path: Path,
):
    monkeypatch.chdir(nested_books / "sub")
    assert run_ls(monkeypatch, tmp_path / "store", "-f", "json") == 0
    (item,) = json.loads(capsys.readouterr().out)
    assert Path(item["path"]).name == "Emotions.pdf"


def test_multiple_operands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nested_books: Path,
    tmp_path: Path,
):
    monkeypatch.chdir(nested_books)
    assert run_ls(monkeypatch, tmp_path / "store", "1Q84.epub", "sub") == 0
    names = [line.split("\t")[0] for line in capsys.readouterr().out.splitlines()]
    assert names == ["1Q84.epub", "sub/Emotions.pdf"]


def test_missing_operand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sample_books: Path,
    tmp_path: Path,
):
    args = (
        str(sample_books / "nope"),
        str(sample_books / "Emotions.pdf"),
        "-f",
        "json",
    )
    assert run_ls(monkeypatch, tmp_path / "store", *args) == 1
    assert len(json.loads(capsys.readouterr().out)) == 1
