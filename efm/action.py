import logging
import os
import pathlib
import shutil
import subprocess

import pymupdf
from efm.DeDRM_plugin.epubtest import encryption as detect_epub_encryption
from efm.DeDRM_plugin.ineptepub import decryptBook as decrypt_inept_epub

from efm.adl.adl.epub_get import get_ebook
from efm.adl.adl.exceptions import GetEbookException
from efm.adl.adl.login import login
from efm.adl.adl import account, data

from efm.config import Config
from efm.env import ensure_k2pdfopt
from efm.metadata import Metadata
from efm.exceptions import (
    BookError,
    DetectEncryptionError,
    GetMetadataError,
    MissingDrmKeyFileError,
    UnsupportedEncryptionError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)


class BaseAction(object):
    def __init__(
        self,
        config: Config | None,
        metadata: Metadata | None,
        filepath: str,
        temp_dirpath: str,
        dry: bool,
    ):
        self.dry = dry
        self.config = config
        self.metadata = metadata
        self.filepath = filepath
        self.temp_dirpath = temp_dirpath

    def perform(self) -> str:
        raise NotImplementedError

    def get_metadata(self) -> Metadata:
        if self.metadata is None:
            try:
                f = pymupdf.open(self.filepath)
                if f.metadata is None:
                    self.metadata = False
                else:
                    # https://pymupdf.readthedocs.io/en/latest/document.html#Document.metadata
                    # Contains the document’s meta data as a Python dictionary or None (if is_encrypted=True and needPass=True).
                    # Keys are format, encryption, title, author, subject, keywords, creator, producer, creationDate, modDate, trapped. All item values are strings or None.
                    format = f.metadata.get("format")
                    self.metadata = Metadata(
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


class RenameAction(BaseAction):
    def perform(self):
        metadata = self.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self.filepath,
                message="Cannot rename",
            )
        ext = os.path.splitext(self.filepath)[1]  # includes .
        filename = os.path.basename(self.filepath)
        new_filename = f"{metadata.author or 'unknown'} - {metadata.title}{ext}"
        if new_filename == filename:
            logger.debug(
                f"Skipping {self.filepath} because it's already named correctly."
            )
            return self.filepath
        temp_filepath = os.path.join(self.temp_dirpath, new_filename)
        shutil.copy(self.filepath, temp_filepath)
        logger.info(f"Renamed {self.filepath} to {new_filename}")
        return temp_filepath


class DeDrmAction(BaseAction):
    def perform(self):
        if self.filepath.lower().endswith(".epub"):
            return self._perform_epub()

        raise UnsupportedFormatError(
            self.filepath, format_type=os.path.splitext(self.filepath)[1]
        )

    def _perform_epub(self):
        logger.debug(f"Removing DRM from epub file {self.filepath}...")
        encryption_type = detect_epub_encryption(self.filepath)
        logger.debug(f"Encryption type: {encryption_type}")
        if encryption_type == "Error":
            raise DetectEncryptionError(self.filepath)

        if encryption_type == "Unencrypted":
            logger.debug(f"Skipping {self.filepath} because it's already unencrypted.")
            return self.filepath

        if encryption_type == "Adobe":
            adobe_key_filepath = (
                self.config.adobe_key_file if self.config is not None else None
            )
            if adobe_key_filepath is None:
                raise MissingDrmKeyFileError(self.filepath, encryption_type="Adobe")

            adobe_key_file = pathlib.Path(adobe_key_filepath).expanduser()
            if not adobe_key_file.exists():
                raise MissingDrmKeyFileError(
                    self.filepath,
                    encryption_type="Adobe",
                    message=f"Key file {adobe_key_file} not found",
                )

            logger.debug(f"Removing Adobe DRM from {self.filepath}...")
            output_filepath = os.path.join(self.temp_dirpath, "post_dedrm.epub")
            decrypt_inept_epub(
                adobe_key_file.read_bytes(), self.filepath, output_filepath
            )

            logger.info(
                f"Decrypted {self.filepath} with Adobe key file {adobe_key_file}"
            )
            return output_filepath

        if (
            encryption_type == "Readium LCP"
            or encryption_type == "Apple"
            or encryption_type == "Kobo"
            or encryption_type == "B&N"
        ):
            raise UnsupportedEncryptionError(
                self.filepath, encryption_type=encryption_type
            )


class ReformatPdfAction(BaseAction):
    def perform(self):
        metadata = self.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self.filepath,
                message="Cannot reformat",
            )

        if metadata.is_k2pdfopt_version:
            logger.debug(f"Skipping {self.filepath} because it's already reformatted.")
            return self.filepath

        if not metadata.format.lower().startswith("pdf"):
            logger.debug(
                f"Skipping {self.filepath} because it's not a PDF. Format is {metadata.format}."
            )
            return self.filepath

        ensure_k2pdfopt()
        temp_filepath_k2pdfopt = os.path.join(
            self.temp_dirpath, "post_reformat_pdf_k2pdfopt.pdf"
        )
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
                temp_filepath_k2pdfopt,
                self.filepath,
            ],
            # need to ignore stdin so it doesn't go into interactive mode
            stdin=subprocess.DEVNULL,
        )
        logger.debug(
            f"Reformated {self.filepath} with k2pdfopt to {temp_filepath_k2pdfopt}"
        )

        f = pymupdf.open(temp_filepath_k2pdfopt)
        f.embfile_add("__ebooks-folder-manager.json", b'{"k2pdfopt_version": true}')

        temp_filepath_metadata = os.path.join(
            self.temp_dirpath, "post_reformat_pdf_metadata.pdf"
        )
        f.save(temp_filepath_metadata)
        logger.debug(
            f"Added metadata to {temp_filepath_k2pdfopt} and saved to {temp_filepath_metadata}"
        )

        self.get_metadata().is_k2pdfopt_version = True

        logger.info(f"Reformatted {self.filepath} with k2pdfopt")
        return temp_filepath_metadata


class PrintAction(BaseAction):
    def perform(self):
        metadata = self.get_metadata()
        if metadata is False:
            print(
                f"File {self.filepath} has no metadata for one reason or another. It could be encrypted."
            )
        else:
            print(
                "\n".join(
                    [
                        s
                        for s in [
                            f"Metadata for {self.filepath}:",
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
        return self.filepath


class DownloadAction(BaseAction):
    def perform(self):
        if self.filepath.lower().endswith(".acsm"):
            if not self.config:
                raise BookError(
                    self.filepath,
                    message="Can not download ACSM file - no config found",
                )
            username = self.config.adobe_user
            password = self.config.adobe_password
            if not username or not password:
                raise BookError(
                    self.filepath,
                    message="Can not download ACSM file - no user or password found - add adobe_user and adobe_password to config file",
                )

            current_user = None
            user = None
            for a in data.accounts:
                if a.urn == data.config.current_user:
                    current_user = a
                if a.sign_id == username:
                    user = a

            if not user:
                # login sets the default user to this one
                login(username, password)
            elif current_user != user:
                account.set_default_account(user.urn)

            try:
                new_filepath = get_ebook(self.filepath)
                logging.info(f"Downloaded {self.filepath}")
                return new_filepath
            except Exception as e:
                if isinstance(e, GetEbookException):
                    raise BookError(self.filepath, message=str(e))
                raise
        logger.debug(f"Skipping {self.filepath} because it's not an ACSM file.")
        return self.filepath
