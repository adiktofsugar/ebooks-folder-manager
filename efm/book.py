import logging
import os
import shutil
import subprocess
import tempfile
from typing import Union
import pymupdf

from efm.DeDRM_plugin.epubtest import encryption
from efm.DeDRM_plugin.ineptepub import decryptBook
from efm.config import Config, get_closest_config
from efm.env import ensure_k2pdfopt
from efm.exceptions import (
    DetectEncryptionError,
    GetMetadataError,
    MissingDrmKeyFileError,
    UnsupportedEncryptionError,
    UnsupportedFormatError,
)


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
    dry: bool
    config: Config | None
    metadata: Union[BookMetadata, None, False]
    new_file: str | None
    tmp_file: str | None

    def __init__(self, file: str, dry: bool = False):
        self.config = get_closest_config(os.path.dirname(file))
        self.file = file
        self.dry = dry
        self.metadata = None
        self.new_file = None
        self.tmp_file = None

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

    def get_tmp_file(self):
        if self.tmp_file is None:
            filename, ext = os.path.splitext(self.file)
            tmp_file = tempfile.NamedTemporaryFile(
                prefix=filename, suffix=ext, delete=False
            )
            self.tmp_file = tmp_file.name
            shutil.copy(self.file, self.tmp_file)
        return self.tmp_file

    def print_metadata(self):
        metadata = self.get_metadata()
        if metadata is False:
            print(
                f"File {self.file} has no metadata for one reason or another. It could be encrypted."
            )
        else:
            print(
                "\n".join(
                    [
                        s
                        for s in [
                            f"Metadata for {self.file}:",
                            f"  Format: {metadata.format}"
                            if metadata.format is not None
                            else None,
                            f"  Encryption: {metadata.encryption}"
                            if metadata.encryption is not None
                            else None,
                            f"  Title: {metadata.title}",
                            f"  Author: {metadata.author}",
                            f"  Subject: {metadata.subject}",
                            f"  Keywords: {metadata.keywords}",
                            f"  Creator: {metadata.creator}",
                            f"  Producer: {metadata.producer}",
                            f"  Creation Date: {metadata.creation_date}",
                            f"  Mod Date: {metadata.mod_date}",
                            f"  Is k2pdfopt version: {metadata.is_k2pdfopt_version}"
                            if metadata.format.lower().startswith("pdf")
                            else None,
                        ]
                        if s is not None
                    ],
                )
            )

    def remove_drm(self):
        """
        So this doesn't really work because it depends on methods from an inherited calibre class
        That means I'll need to basically remake that class without using any of the calibre stuff, and/or just work with epubs for now.
        """
        # dedrm = DeDRM()
        # decrypted_file: str | None = dedrm.run(self.get_tmp_file())
        # if decrypted_file is not None:
        #     self.tmp_file = decrypted_file
        if self.file.lower().endswith(".epub"):
            logging.debug(f"Removing DRM from epub file {self.file}...")
            encryption_type = encryption(self.file)
            logging.debug(f"Encryption type: {encryption_type}")
            if encryption_type == "Error":
                raise DetectEncryptionError(self)
            if encryption_type == "Unencrypted":
                logging.debug(f"Skipping {self.file} because it's already unencrypted.")
                return

            if encryption_type == "Adobe":
                adobe_key_file = (
                    self.config.adobe_key_file if self.config is not None else None
                )
                if adobe_key_file is None:
                    raise MissingDrmKeyFileError(self, key_type="Adobe")
                logging.debug(f"Removing Adobe DRM from {self.file}...")
                filename, ext = os.path.splitext(self.file)
                logging.debug(f"filename: {filename}, ext: {ext}")
                with tempfile.NamedTemporaryFile(
                    prefix=filename, suffix=ext, delete=False
                ) as tmp:
                    logging.debug(f"Decrypted file will be saved to {tmp.name}")
                    decryptBook(adobe_key_file, self.get_tmp_file(), tmp.file.name)
                    logging.info(
                        f"Decrypted {self.file} with Adobe key file {adobe_key_file}"
                    )
                    shutil.move(tmp.file.name, self.get_tmp_file())
                logging.debug(f"Removed Adobe DRM from {self.file}.")
                return

            if (
                encryption_type == "Readium LCP"
                or encryption_type == "Apple"
                or encryption_type == "Kobo"
                or encryption_type == "B&N"
            ):
                raise UnsupportedEncryptionError(self, encryption_type=encryption_type)

        raise UnsupportedFormatError(self, format_type=os.path.splitext(self.file)[1])

    def rename(self):
        metadata = self.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self, message=f"Cannot rename {self.file} because it has no metadata."
            )
        ext = os.path.splitext(self.file)[1]  # includes .
        new_name = f"{metadata.author} - {metadata.title}{ext}"
        new_path = os.path.join(os.path.dirname(self.file), new_name)
        if new_path == self.file:
            logging.debug(f"Skipping {self.file} because it's already renamed.")
            return
        self.new_file = new_path

    def reformat_pdf(self):
        metadata = self.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self, message=f"Cannot reformat {self.file} because it has no metadata."
            )
        if metadata.is_k2pdfopt_version:
            logging.debug(f"Skipping {self.file} because it's already reformatted.")
            return
        if not metadata.format.lower().startswith("pdf"):
            logging.debug(
                f"Skipping {self.file} because it's not a PDF. Format is {metadata.format}."
            )
            return
        ensure_k2pdfopt()
        filename, ext = os.path.splitext(self.file)
        logging.info(f"Reformatting {self.file} with k2pdfopt...")

        with tempfile.NamedTemporaryFile(
            # prefix and suffix are set because k2pdfopt makes titles based on the filename
            prefix=filename,
            suffix=ext,
        ) as tmp:
            # -om = output margin
            # -ds = document scale
            # -w = width of reader
            # -h = height of reader
            # -o = output file
            subprocess.run(
                [
                    "k2pdfopt",
                    "-om",
                    "0.1",
                    "-ds",
                    "0.5",
                    "-w",
                    "1264",
                    "-h",
                    "1680",
                    "-o",
                    tmp.file.name,
                    self.get_tmp_file(),
                ],
                # need to ignore stdin so it doesn't go into interactive mode
                stdin=subprocess.DEVNULL,
            )
            f = pymupdf.open(tmp.file.name)
            f.embfile_add("__ebooks-folder-manager.json", b'{"k2pdfopt_version": true}')
            f.save(self.get_tmp_file())

    def process(self, actions: list[str]):
        logging.debug(f"Processing {self.file} - actions: {actions}")
        try:
            # Note: this order has significance
            if "drm" in actions:
                self.remove_drm()
            if "rename" in actions:
                self.rename()
            if "print" in actions:
                self.print_metadata()
            if "pdf" in actions:
                self.reformat_pdf()
            if "none" in actions:
                self.get_metadata()
        except Exception:
            if self.tmp_file is not None:
                shutil.rmtree(self.tmp_file, ignore_errors=True)
            raise
        self.save()

    def save(self):
        if self.new_file is not None:
            if self.dry:
                logging.info(f"Would rename {self.file} to {self.new_file}")
            else:
                logging.info(f"Renaming {self.file} to {self.new_file}")
                shutil.move(self.file, self.new_file)
            self.file = self.new_file

        if self.tmp_file is not None:
            if self.dry:
                logging.info(f"Would save {self.file} with changes")
            else:
                logging.info(f"Saving {self.file} with changes")
                shutil.move(self.tmp_file, self.file)

        self.new_file = None
        self.tmp_file = None
        self.metadata = None
