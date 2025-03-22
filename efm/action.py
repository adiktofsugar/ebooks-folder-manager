import logging
import os
import shutil
import subprocess

import pymupdf
from efm.DeDRM_plugin.epubtest import encryption as detect_epub_encryption
from efm.DeDRM_plugin.ineptepub import decryptBook as decrypt_inept_epub
from efm.env import ensure_k2pdfopt
from efm.book import Book
from efm.exceptions import (
    DetectEncryptionError,
    GetMetadataError,
    MissingDrmKeyFileError,
    UnsupportedEncryptionError,
    UnsupportedFormatError,
)


class BaseAction(object):
    def __init__(self, filepath: str, temp_dirpath: str, dry: bool):
        self.dry = dry
        self.book = Book(filepath)
        self.filepath = filepath
        self.temp_dirpath = temp_dirpath

    def perform(self) -> str:
        raise NotImplementedError


class RenameAction(BaseAction):
    def perform(self):
        metadata = self.book.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self.filepath,
                message="Cannot rename",
            )
        ext = os.path.splitext(self.filepath)[1]  # includes .
        new_name = f"{metadata.author or 'unknown'} - {metadata.title}{ext}"
        temp_filepath = os.path.join(self.temp_dirpath, new_name)
        shutil.copy(self.filepath, temp_filepath)
        return temp_filepath


class DeDrmAction(BaseAction):
    def perform(self):
        if self.filepath.lower().endswith(".epub"):
            return self._perform_epub()

        raise UnsupportedFormatError(
            self.filepath, format_type=os.path.splitext(self.filepath)[1]
        )

    def _perform_epub(self):
        logging.debug(f"Removing DRM from epub file {self.filepath}...")
        encryption_type = detect_epub_encryption(self.filepath)
        logging.debug(f"Encryption type: {encryption_type}")
        if encryption_type == "Error":
            raise DetectEncryptionError(self.filepath)

        if encryption_type == "Unencrypted":
            logging.debug(f"Skipping {self.filepath} because it's already unencrypted.")
            return self.filepath

        if encryption_type == "Adobe":
            adobe_key_file = (
                self.book.config.adobe_key_file
                if self.book.config is not None
                else None
            )
            if adobe_key_file is None:
                raise MissingDrmKeyFileError(self.filepath, key_type="Adobe")

            logging.debug(f"Removing Adobe DRM from {self.filepath}...")
            output_filepath = os.path.join(self.temp_dirpath, "post_drdrm.epub")
            decrypt_inept_epub(adobe_key_file, self.filepath, output_filepath)
            logging.info(
                f"Decrypted {self.filepath} with Adobe key file {adobe_key_file} to {output_filepath}"
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
        metadata = self.book.get_metadata()
        if metadata is False:
            raise GetMetadataError(
                self.filepath,
                message="Cannot reformat",
            )

        if metadata.is_k2pdfopt_version:
            logging.debug(f"Skipping {self.filepath} because it's already reformatted.")
            return self.filepath

        if not metadata.format.lower().startswith("pdf"):
            logging.debug(
                f"Skipping {self.filepath} because it's not a PDF. Format is {metadata.format}."
            )
            return self.filepath

        ensure_k2pdfopt()
        logging.info(f"Reformatting {self.filepath} with k2pdfopt...")
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
        f = pymupdf.open(temp_filepath_k2pdfopt)
        f.embfile_add("__ebooks-folder-manager.json", b'{"k2pdfopt_version": true}')

        temp_filepath_metadata = os.path.join(
            self.temp_dirpath, "post_reformat_pdf_metadata.pdf"
        )
        f.save(temp_filepath_metadata)
        return temp_filepath_metadata


class PrintAction(BaseAction):
    def perform(self):
        metadata = self.book.get_metadata()
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
