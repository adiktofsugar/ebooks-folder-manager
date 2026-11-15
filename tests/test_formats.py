from pathlib import Path
from typing import Any

import pytest

from efm import metadata
from efm.metadata import extract
from tests.book_builders import make_cbz, make_epub

CALIBRE_SERIES = """
    <meta name="calibre:series" content="Discworld"/>
    <meta name="calibre:series_index" content="17"/>"""


def test_epub2_calibre_series(tmp_path: Path):
    m = extract(make_epub(tmp_path / "b.epub", extra_meta=CALIBRE_SERIES)).metadata
    assert (m.kind, m.series, m.series_index) == ("epub2", "Discworld", "17")
    assert (m.title, m.author) == ("A Title", "An Author")


def test_epub3_collection_wins_over_calibre(tmp_path: Path):
    extra = (
        """
    <meta property="belongs-to-collection" id="c1">The Expanse</meta>
    <meta refines="#c1" property="collection-type">series</meta>
    <meta refines="#c1" property="group-position">2.5</meta>"""
        + CALIBRE_SERIES
    )
    book_file = make_epub(tmp_path / "b.epub", version="3.0", extra_meta=extra)
    extracted = extract(book_file)
    m = extracted.metadata
    assert (m.kind, m.series, m.series_index) == ("epub3", "The Expanse", "2.5")
    assert extracted.raw is not None
    assert extracted.raw["epub_fields"]["creators"] == ["An Author"]


def test_epub3_falls_back_to_calibre(tmp_path: Path):
    book_file = make_epub(tmp_path / "b.epub", version="3.0", extra_meta=CALIBRE_SERIES)
    m = extract(book_file).metadata
    assert (m.kind, m.series, m.series_index) == ("epub3", "Discworld", "17")


def test_epub_without_series(tmp_path: Path):
    m = extract(make_epub(tmp_path / "b.epub")).metadata
    assert (m.kind, m.series, m.series_index) == ("epub2", None, None)


def test_index_without_series_is_dropped(tmp_path: Path):
    extra = '<meta name="calibre:series_index" content="3"/>'
    m = extract(make_epub(tmp_path / "b.epub", extra_meta=extra)).metadata
    assert (m.series, m.series_index) == (None, None)


def test_unreadable_opf_keeps_pymupdf_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def broken(book_file: Path) -> dict[str, Any]:
        raise KeyError("OEBPS/content.opf")

    monkeypatch.setattr(metadata, "read_epub_fields", broken)
    extracted = extract(make_epub(tmp_path / "b.epub"))
    assert extracted.raw is not None and "epub_fields" not in extracted.raw
    assert extracted.metadata.title == "A Title"
    assert extracted.metadata.kind == "epub"


def test_sample_epub_kind(sample_books_dir: Path):
    m = extract(sample_books_dir / "WorldUnbound.epub").metadata
    assert m.kind == "epub2"


def test_sample_pdf_kind(sample_books_dir: Path):
    assert extract(sample_books_dir / "Emotions.pdf").metadata.kind == "pdf"


def test_cbz_comic_info(tmp_path: Path):
    info = """<?xml version="1.0"?>
<ComicInfo><Series>Saga</Series><Number>3</Number><Title>Chapter Three</Title><Writer>BKV</Writer></ComicInfo>"""
    extracted = extract(make_cbz(tmp_path / "c.cbz", info))
    m = extracted.metadata
    assert m.format == "zip"
    assert (m.kind, m.series, m.series_index) == ("cbz", "Saga", "3")
    assert extracted.raw is not None
    assert extracted.raw["cbz_fields"]["writer"] == "BKV"


def test_cbz_without_comic_info(tmp_path: Path):
    extracted = extract(make_cbz(tmp_path / "c.cbz", None))
    assert extracted.metadata.kind == "cbz"
    assert extracted.metadata.series is None
    assert extracted.raw is not None and "cbz_fields" not in extracted.raw
