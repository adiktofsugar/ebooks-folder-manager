import logging
from typing import Union


logger = logging.getLogger(__name__)


class Metadata(object):
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
