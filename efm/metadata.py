import logging
from typing import LiteralString


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
