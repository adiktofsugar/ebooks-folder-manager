import logging
from pathlib import Path
from typing import LiteralString

import pymupdf

from efm.exceptions import GetMetadataError


logger = logging.getLogger(__name__)


class Metadata(object):
    def __init__(
        self,
        format: str | None,
        encryption: str | None,
        title: str | None,
        author: str | None,
        subject: str | None,
        keywords: list[LiteralString] | None,
        creator: str | None,
        producer: str | None,
        creation_date: str | None,
        mod_date: str | None,
        is_k2pdfopt_version: bool,
    ):
        self.format = format
        self.is_pdf = format is not None and format.lower() == "pdf"
        self.encryption = encryption
        self.title = title
        self.author = author
        self.subject = subject
        self.keywords = keywords
        self.creator = creator
        self.producer = producer
        self.creation_date = creation_date
        self.mod_date = mod_date
        self.is_k2pdfopt_version = is_k2pdfopt_version



def get_metadata(filepath:Path) -> Metadata | None:
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
        f = pymupdf.open(filepath)
        if f.metadata is None:
            logger.info(f"{filepath} has no metadata.")
            return None
        format = f.metadata.get("format")
        keywords_raw = f.metadata.get("keywords")
        keywords = (
            keywords_raw.split(",") if keywords_raw is not None else []
        )
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
