from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from efm.exceptions import UnsupportedSchemaError
from efm.metadata import (
    InternalMetadata,
    Metadata,
    extract,
    load_internal_metadata,
    load_metadata,
    normalize,
)

LOADERS: list[tuple[Callable[[object], BaseModel], BaseModel]] = [
    (load_metadata, Metadata(size=10, title="Cats", keywords=["a", "b"])),
    (load_internal_metadata, InternalMetadata(is_k2pdfopt_version=True)),
]


@pytest.mark.parametrize(("loader", "model"), LOADERS)
def test_round_trip(loader: Callable[[object], BaseModel], model: BaseModel):
    assert loader(model.model_dump(mode="json")) == model


@pytest.mark.parametrize(("loader", "model"), LOADERS)
def test_missing_schema_version(
    loader: Callable[[object], BaseModel], model: BaseModel
):
    data = model.model_dump(mode="json")
    del data["schema_version"]
    with pytest.raises(ValidationError):
        loader(data)


@pytest.mark.parametrize(("loader", "model"), LOADERS)
def test_unknown_schema_version(
    loader: Callable[[object], BaseModel], model: BaseModel
):
    data = model.model_dump(mode="json") | {"schema_version": 99}
    with pytest.raises(UnsupportedSchemaError):
        loader(data)


@pytest.mark.parametrize(("loader", "model"), LOADERS)
def test_extra_field_rejected(loader: Callable[[object], BaseModel], model: BaseModel):
    data = model.model_dump(mode="json") | {"surprise": 1}
    with pytest.raises(ValidationError):
        loader(data)


def test_is_pdf_derived_from_format():
    assert Metadata(size=1, format="PDF 1.7").is_pdf
    assert not Metadata(size=1, format="EPUB").is_pdf
    assert "is_pdf" not in Metadata(size=1).model_dump()


def test_normalize_cleans_empty_strings(tmp_path: Path):
    book_file = tmp_path / "x.epub"
    book_file.write_bytes(b"x")
    raw = {
        "pymupdf_fields": {
            "metadata": {
                "format": "EPUB",
                "title": " Cats ",
                "author": "",
                "keywords": "a, b,,",
                "encryption": "",
            },
            "page_count": None,
            "embfile_names": [],
        }
    }
    m = normalize(raw, book_file)
    assert m.title == "Cats"
    assert m.author is None
    assert m.encryption is None
    assert m.keywords == ["a", "b"]
    assert m.error is None


def test_extract_unsupported_format(tmp_path: Path):
    book_file = tmp_path / "x.acsm"
    book_file.write_text("<fulfillmentToken/>")
    extracted = extract(book_file)
    assert extracted.raw is None
    assert extracted.metadata.format == "ACSM"
    assert extracted.metadata.error


def test_extract_unreadable_file(tmp_path: Path):
    book_file = tmp_path / "x.pdf"
    book_file.write_text("not a pdf")
    extracted = extract(book_file)
    assert extracted.raw is None
    assert (
        extracted.metadata.error
        and "Couldn't read metadata" in extracted.metadata.error
    )


def test_extract_sample_epub(sample_books_dir: Path):
    extracted = extract(sample_books_dir / "InterestingTimes.epub")
    assert extracted.metadata.title == "Interesting Times"
    assert extracted.metadata.author == "Terry Pratchett"
    # Reflowable: page_count would need a full layout pass, so it's skipped.
    assert extracted.metadata.page_count is None
    assert extracted.raw is not None
