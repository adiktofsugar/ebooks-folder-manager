import logging
import os
from typing import Union
import pymupdf

from efm.config import Config, get_closest_config
from efm.exceptions import (
    GetMetadataError,
)

logger = logging.getLogger(__name__)


class BookMetadata(object):
    def __init__(
        self,
        format: str,
        encryption: str,
        title: str,
        author: str,
        subject: str,
        keywords: list[str],
        creator: str,
        producer: str,
        creation_date: str,
        mod_date: str,
        is_k2pdfopt_version: bool,
    ):
        self.format = format
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


class Book(object):
    file: str
    config: Config | None
    metadata: Union[BookMetadata, None, False]

    def __init__(self, file: str):
        self.config = get_closest_config(os.path.dirname(file))
        self.file = file
        self.metadata = None

    def get_metadata(self):
        if self.metadata is None:
            try:
                f = pymupdf.open(self.file)
                if f.metadata is None:
                    self.metadata = False
                else:
                    # https://pymupdf.readthedocs.io/en/latest/document.html#Document.metadata
                    # Contains the document’s meta data as a Python dictionary or None (if is_encrypted=True and needPass=True).
                    # Keys are format, encryption, title, author, subject, keywords, creator, producer, creationDate, modDate, trapped. All item values are strings or None.
                    format = f.metadata.get("format")
                    self.metadata = BookMetadata(
                        format=format,
                        encryption=f.metadata.get("encryption"),
                        title=f.metadata.get("title"),
                        author=f.metadata.get("author"),
                        subject=f.metadata.get("subject"),
                        keywords=f.metadata.get("keywords").split(",")
                        if f.metadata.get("keywords")
                        else [],
                        creator=f.metadata.get("creator"),
                        producer=f.metadata.get("producer"),
                        creation_date=f.metadata.get("creationDate"),
                        mod_date=f.metadata.get("modDate"),
                        is_k2pdfopt_version=(
                            format.lower().startswith("pdf")
                            and "__ebooks-folder-manager.json" in f.embfile_names()
                        ),
                    )
            except pymupdf.FileDataError as e:
                raise GetMetadataError(self, original_error=e)
        return self.metadata
