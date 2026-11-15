import hashlib
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Literal, NamedTuple, assert_never

import pymupdf
from pydantic import BaseModel, ConfigDict

from efm.cover import extract_cover, generate_cover
from efm.exceptions import UnsupportedSchemaError
from efm.formats import READ_ERRORS, read_cbz_fields, read_epub_fields

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"PDF", "XPS", "EPUB", "MOBI", "FB2", "CBZ", "SVG", "TXT"}
K2PDFOPT_MARKER = "__ebooks-folder-manager.json"


# Versioned models. To add a version, see docs/store.md.


class MetadataVX(BaseModel):
    """Any versioned record, read only far enough to pick its model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    schema_version: int


class MetadataV1(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    size: int
    format: str | None = None
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: list[str] = []
    encryption: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    mod_date: str | None = None
    # Only for fixed-layout formats; reflowable ones (EPUB etc.) would need a full layout pass.
    page_count: int | None = None
    error: str | None = None

    @property
    def is_pdf(self) -> bool:
        return self.format is not None and self.format.lower().startswith("pdf")


class MetadataV2(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    size: int
    # What a writer would dispatch on: epub2, epub3, pdf, cbz, mobi, ...
    kind: str | None = None
    format: str | None = None
    title: str | None = None
    author: str | None = None
    series: str | None = None
    # As written in the book, e.g. "1.5"
    series_index: str | None = None
    subject: str | None = None
    keywords: list[str] = []
    encryption: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    mod_date: str | None = None
    # Only for fixed-layout formats; reflowable ones (EPUB etc.) would need a full layout pass.
    page_count: int | None = None
    error: str | None = None

    @property
    def is_pdf(self) -> bool:
        return self.format is not None and self.format.lower().startswith("pdf")


Metadata = MetadataV2
AnyMetadata = MetadataV1 | MetadataV2
METADATA_MODELS: dict[int, type[AnyMetadata]] = {1: MetadataV1, 2: MetadataV2}


def v1_to_v2(m: MetadataV1) -> MetadataV2:
    return MetadataV2(**m.model_dump(exclude={"schema_version"}))


def migrate_metadata(m: AnyMetadata) -> Metadata:
    match m:
        case MetadataV1():
            return migrate_metadata(v1_to_v2(m))
        case MetadataV2():
            return m
        case _:
            assert_never(m)


# Bump when extraction learns something new, so older store entries get re-extracted.
EXTRACTOR_VERSION = 1


class InternalMetadataV1(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    is_k2pdfopt_version: bool = False
    cover_image_hash: str | None = None


class InternalMetadataV2(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    is_k2pdfopt_version: bool = False
    cover_image_hash: str | None = None
    extractor_version: int = EXTRACTOR_VERSION


InternalMetadata = InternalMetadataV2
AnyInternalMetadata = InternalMetadataV1 | InternalMetadataV2
INTERNAL_METADATA_MODELS: dict[int, type[AnyInternalMetadata]] = {
    1: InternalMetadataV1,
    2: InternalMetadataV2,
}


def internal_v1_to_v2(m: InternalMetadataV1) -> InternalMetadataV2:
    return InternalMetadataV2(
        **m.model_dump(exclude={"schema_version"}), extractor_version=0
    )


def migrate_internal_metadata(m: AnyInternalMetadata) -> InternalMetadata:
    match m:
        case InternalMetadataV1():
            return migrate_internal_metadata(internal_v1_to_v2(m))
        case InternalMetadataV2():
            return m
        case _:
            assert_never(m)


def load_versioned[T: BaseModel](data: object, models: Mapping[int, type[T]]) -> T:
    version = MetadataVX.model_validate(data).schema_version
    model = models.get(version)
    if model is None:
        raise UnsupportedSchemaError(version, sorted(models))
    return model.model_validate(data)


def load_metadata(data: object) -> Metadata:
    return migrate_metadata(load_versioned(data, METADATA_MODELS))


def load_internal_metadata(data: object) -> InternalMetadata:
    return migrate_internal_metadata(load_versioned(data, INTERNAL_METADATA_MODELS))


# Extraction


class Extracted(NamedTuple):
    metadata: Metadata
    internal: InternalMetadata
    raw: dict[str, Any] | None


def read_raw_metadata(book_file: Path) -> dict[str, Any] | None:
    """What pymupdf reports, unmodified, plus format-specific fields. None if pymupdf can't open the file.

    Raises pymupdf.FileDataError for files it recognizes but can't parse.
    """
    if book_file.suffix[1:].upper() not in SUPPORTED_FORMATS:
        return None
    with pymupdf.open(book_file) as doc:
        raw: dict[str, Any] = {
            "pymupdf_fields": {
                "metadata": doc.metadata,
                "page_count": None if doc.is_reflowable else doc.page_count,
                "embfile_names": doc.embfile_names() if doc.is_pdf else [],
            }
        }
    fmt = str((raw["pymupdf_fields"]["metadata"] or {}).get("format") or "").upper()
    for prefix, key, reader in (
        ("EPUB", "epub_fields", read_epub_fields),
        # pymupdf reports comic archives as "zip".
        ("ZIP", "cbz_fields", read_cbz_fields),
    ):
        if fmt.startswith(prefix):
            try:
                raw[key] = reader(book_file)
            except READ_ERRORS as e:
                logger.debug(f"Couldn't read {key} from {book_file}: {e}")
    return raw


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def normalize(
    raw: dict[str, Any] | None, book_file: Path, error: str | None = None
) -> Metadata:
    size = book_file.stat().st_size
    if raw is None:
        return Metadata(
            size=size,
            format=book_file.suffix[1:].upper() or None,
            error=error or f"Unsupported format: {book_file.suffix or '(none)'}",
        )
    pymupdf_fields: dict[str, Any] = raw.get("pymupdf_fields") or {}
    m: dict[str, Any] = pymupdf_fields.get("metadata") or {}
    keywords = _clean(m.get("keywords"))
    fmt = _clean(m.get("format"))
    kind = fmt.split()[0].lower() if fmt else None
    kind = "cbz" if kind == "zip" else kind
    series, series_index = None, None
    if epub := raw.get("epub_fields"):
        version = str(epub.get("version") or "")
        kind = f"epub{version.split('.')[0]}" if version[:1].isdigit() else kind
        series, series_index = (
            _clean(epub.get("series")),
            _clean(epub.get("series_index")),
        )
    elif cbz := raw.get("cbz_fields"):
        series, series_index = _clean(cbz.get("series")), _clean(cbz.get("number"))
    return Metadata(
        size=size,
        kind=kind,
        format=fmt,
        series=series,
        series_index=series_index if series else None,
        title=_clean(m.get("title")),
        author=_clean(m.get("author")),
        subject=_clean(m.get("subject")),
        keywords=[k.strip() for k in keywords.split(",") if k.strip()]
        if keywords
        else [],
        encryption=_clean(m.get("encryption")),
        creator=_clean(m.get("creator")),
        producer=_clean(m.get("producer")),
        creation_date=_clean(m.get("creationDate")),
        mod_date=_clean(m.get("modDate")),
        page_count=pymupdf_fields.get("page_count"),
        error=error,
    )


def internal_from(raw: dict[str, Any] | None) -> InternalMetadata:
    pymupdf_fields: dict[str, Any] = (raw or {}).get("pymupdf_fields") or {}
    embfiles: list[str] = pymupdf_fields.get("embfile_names") or []
    return InternalMetadata(is_k2pdfopt_version=K2PDFOPT_MARKER in embfiles)


def extract(book_file: Path) -> Extracted:
    try:
        raw = read_raw_metadata(book_file)
        error = None
    except (pymupdf.FileDataError, RuntimeError) as e:
        logger.debug(f"pymupdf couldn't open {book_file}: {e}")
        raw = None
        error = f"Couldn't read metadata: {e}"
    return Extracted(normalize(raw, book_file, error), internal_from(raw), raw)


def get_metadata(book_file: Path) -> Metadata:
    return extract(book_file).metadata


def is_k2pdfopt_file(book_file: Path) -> bool:
    try:
        return internal_from(read_raw_metadata(book_file)).is_k2pdfopt_version
    except (pymupdf.FileDataError, RuntimeError):
        return False


def extract_cover_image(
    book_file: Path, metadata: Metadata | None, cache_dir: Path
) -> str | None:
    """Extract or generate cover image and return hash.

    Args:
        book_file: Path to the ebook file
        metadata: Book metadata (for title/author in generated covers)
        cache_dir: Directory to save cover images

    Returns:
        Hash string of the cover image, or None if failed
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Try to extract cover
    cover = extract_cover(book_file)

    # If no cover found, generate one
    if not cover:
        # Use file hash as seed
        file_hash = hashlib.sha256(book_file.read_bytes()).hexdigest()

        # Extract title and author from metadata
        title = metadata.title if metadata else None
        author = metadata.author if metadata else None

        # If no metadata, use filename
        if not title:
            title = book_file.stem

        logger.debug(f"Generating cover for {book_file.name}")
        cover = generate_cover(file_hash, title, author)

    # Save cover if not already cached
    cover_file = cache_dir / f"{cover.hash}.png"
    if not cover_file.exists():
        cover.save(cover_file)
        logger.debug(f"Saved cover image to {cover_file}")

    return cover.hash
