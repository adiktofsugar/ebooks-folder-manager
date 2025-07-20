import logging
from pathlib import Path
from typing import LiteralString
from dataclasses import dataclass
import hashlib

import pymupdf
from ebooklib import epub

from efm.exceptions import GetMetadataError
from efm.cover import CoverImage, extract_cover, generate_cover


logger = logging.getLogger(__name__)


@dataclass
class Metadata:
    format: str | None
    encryption: str | None
    title: str | None
    author: str | None
    subject: str | None
    keywords: list[LiteralString] | None
    creator: str | None
    producer: str | None
    creation_date: str | None
    mod_date: str | None
    is_k2pdfopt_version: bool
    cover_image_hash: str | None = None

    def __post_init__(self):
        self.is_pdf = self.format is not None and self.format.lower() == "pdf"


def get_metadata(filepath: Path) -> Metadata | None:
    supported_formats = [
        "PDF",
        "XPS",
        "EPUB",
        "MOBI",
        "FB2",
        "CBZ",
        "SVG",
        "TXT",
    ]
    ext = filepath.suffix[1:].upper()
    if ext not in supported_formats:
        logger.info(
            f"{filepath} is not a supported format for pymupdf. Format is {ext}."
        )
        return None
    try:
        f: pymupdf.Document = pymupdf.open(filepath)
        if f.metadata is None:
            logger.info(f"{filepath} has no metadata.")
            return None
        format = f.metadata.get("format")
        keywords_raw = f.metadata.get("keywords")
        keywords = keywords_raw.split(",") if keywords_raw is not None else []
        return Metadata(
            format=format,
            encryption=f.metadata.get("encryption"),
            title=f.metadata.get("title"),
            author=f.metadata.get("author"),
            subject=f.metadata.get("subject"),
            keywords=keywords,
            creator=f.metadata.get("creator"),
            producer=f.metadata.get("producer"),
            creation_date=f.metadata.get("creationDate"),
            mod_date=f.metadata.get("modDate"),
            is_k2pdfopt_version=(
                format.lower().startswith("pdf")
                and "__ebooks-folder-manager.json" in f.embfile_names()
                if format is not None
                else False
            ),
        )
    except pymupdf.FileDataError as e:
        raise GetMetadataError(filepath, original_error=e)









def extract_cover_image(
    filepath: Path, metadata: Metadata | None, cache_dir: Path
) -> str | None:
    """Extract or generate cover image and return hash.

    Args:
        filepath: Path to the ebook file
        metadata: Book metadata (for title/author in generated covers)
        cache_dir: Directory to save cover images

    Returns:
        Hash string of the cover image, or None if failed
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to extract cover
    cover = extract_cover(filepath)
    
    # If no cover found, generate one
    if not cover:
        # Use file hash as seed
        file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()

        # Extract title and author from metadata
        title = metadata.title if metadata else None
        author = metadata.author if metadata else None

        # If no metadata, use filename
        if not title:
            title = filepath.stem

        logger.info(f"Generating cover for {filepath.name}")
        cover = generate_cover(file_hash, title, author)

    # Save cover if not already cached
    cover_path = cache_dir / f"{cover.hash}.png"
    if not cover_path.exists():
        cover.save(cover_path)
        logger.info(f"Saved cover image to {cover_path}")

    return cover.hash
