"""Tests for top-level subcommand parsing and dispatch."""

import sys

import pytest

from efm.__main__ import main


def test_no_command_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["efm"])
    assert main() == 1
    assert "process" in capsys.readouterr().out


def test_process_requires_output_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["efm", "process", str(tmp_path)])
    assert main() == 1


def test_process_rejects_file(monkeypatch, tmp_path):
    book = tmp_path / "book.epub"
    book.write_text("not a book")
    monkeypatch.setattr(
        sys, "argv", ["efm", "process", str(book), "-o", str(tmp_path / "out")]
    )
    assert main() == 1


def test_process_writes_db(monkeypatch, tmp_path):
    books = tmp_path / "books"
    books.mkdir()
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["efm", "process", str(books), "-o", str(out)])
    assert main() == 0
    assert (out / "db.yaml").exists()


def test_setup_rejects_unknown_tool(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["efm", "setup", "not-a-tool"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
