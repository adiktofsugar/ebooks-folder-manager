"""Tests for top-level subcommand parsing and dispatch."""

import sys

import pytest

from efm.__main__ import main


def test_no_command_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["efm"])
    assert main() == 1
    assert "ls" in capsys.readouterr().out


def test_ls_rejects_missing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["efm", "ls", str(tmp_path / "nope")])
    assert main() == 1


def test_ls_empty_dir(monkeypatch, tmp_path):
    books = tmp_path / "books"
    books.mkdir()
    monkeypatch.setattr(
        sys, "argv", ["efm", "--store", str(tmp_path / "store"), "ls", str(books)]
    )
    assert main() == 0


def test_setup_rejects_unknown_tool(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["efm", "setup", "not-a-tool"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_find_rejects_missing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["efm", "find", str(tmp_path / "nope")])
    assert main() == 1


def test_find_rejects_bad_regex(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["efm", "find", str(tmp_path), "--title", "("])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_acsm_requires_files(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["efm", "acsm"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
