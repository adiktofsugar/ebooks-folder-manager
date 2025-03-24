import logging
import os
import shutil
import subprocess
from typing import Literal, Sequence
import pymupdf

from efm import dedrm, kfxconvert
from adl.epub_get import get_ebook
from adl.exceptions import GetEbookException
from adl.login import login
from adl import account, data

from efm.config import Config
from efm.env import ensure_k2pdfopt
from efm.metadata import Metadata
from efm.exceptions import (
    BookError,
    GetMetadataError,
    RemoveDrmError,
)

logger = logging.getLogger(__name__)


class BaseAction(object):
    @classmethod
    def description(cls) -> str:
        raise NotImplementedError

    @classmethod
    def id(cls) -> str:
        raise NotImplementedError

    config: Config | None
    metadata: Metadata | None | Literal[False]
    filepath: str
    temp_dirpath: str
    dry: bool

    def __init__(
        self,
        config: Config | None,
        metadata: Metadata | None | Literal[False],
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

    def get_metadata(self) -> Metadata | Literal[False]:
        if self.metadata is None:
            # https://pymupdf.readthedocs.io/en/latest/how-to-open-a-file.html#supported-file-types
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
            ext = os.path.splitext(self.filepath)[1][1:].upper()
            if ext not in supported_formats:
                logger.info(
                    f"Setting metadata for {self.filepath} to False because it's not a supported format. Format is {ext}."
                )
                self.metadata = False
            else:
                try:
                    f = pymupdf.open(self.filepath)
                    if f.metadata is None:
                        self.metadata = False
                    else:
                        # https://pymupdf.readthedocs.io/en/latest/document.html#Document.metadata
                        # Contains the document’s meta data as a Python dictionary or None (if is_encrypted=True and needPass=True).
                        # Keys are format, encryption, title, author, subject, keywords, creator, producer, creationDate, modDate, trapped. All item values are strings or None.
                        format = f.metadata.get("format")
                        keywords_raw = f.metadata.get("keywords")
                        keywords = (
                            keywords_raw.split(",") if keywords_raw is not None else []
                        )
                        self.metadata = Metadata(
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
                    raise GetMetadataError(self.filepath, original_error=e)
        return self.metadata


class RenameAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "rename files based on metadata"

    @classmethod
    def id(cls) -> str:
        return "rename"

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
    @classmethod
    def description(cls) -> str:
        return "remove DRM from files"

    @classmethod
    def id(cls) -> str:
        return "drm"

    def perform(self):
        booktype = os.path.splitext(self.filepath)[1].lower()[1:]
        if booktype in [
            "prc",
            "mobi",
            "pobi",
            "azw",
            "azw1",
            "azw3",
            "azw4",
            "tpz",
            "kfx-zip",
        ]:
            # Kindle/Mobipocket
            return self._perform_k4mobi()
        elif booktype == "pdb":
            # eReader
            return self._perform_pdb()
            pass
        elif booktype == "pdf":
            # Adobe PDF (hopefully) or LCP PDF
            return self._perform_pdf()
            pass
        elif booktype == "epub":
            # Adobe Adept, PassHash (B&N) or LCP ePub
            return self._perform_epub()

        logger.info(f"No DeDRM support for format {booktype} files.")
        return self.filepath

    def _perform_k4mobi(self) -> str:
        if not self.config:
            raise RemoveDrmError(
                self.filepath,
                message="No config found, but kindle_* config keys are required to decrypt Kindle files.",
            )
        logger.debug(f"Removing DRM from k4mobi file {self.filepath}...")
        return dedrm.decryptk4mobi(
            self.filepath,
            outdir=self.temp_dirpath,
            kindle_android_files=self.config.kindle_android_files or [],
            kindle_db_files=self.config.kindle_database_files or [],
            kindle_pids=self.config.kindle_pidnums or [],
            kindle_serials=self.config.kindle_serialnums or [],
        )

    def _perform_pdb(self) -> str:
        logger.debug(f"Removing DRM from pdb file {self.filepath}...")
        social_drm_file = self.config.ereader_social_drm_file if self.config else None
        if not social_drm_file:
            raise RemoveDrmError(
                self.filepath,
                message="No social DRM file found. Add ereader_social_drm_file to config file.",
            )
        return dedrm.decryptpdb(
            self.filepath,
            outdir=self.temp_dirpath,
            social_drm_file=social_drm_file,
        )

    def _perform_pdf(self) -> str:
        logger.debug(f"Removing DRM from pdf file {self.filepath}...")
        return dedrm.decryptpdf(
            self.filepath,
            outdir=self.temp_dirpath,
            key_files=(
                [
                    *(self.config.adobe_key_files or []),
                    *(self.config.b_and_n_key_files or []),
                ]
                if self.config
                else []
            ),
            passwords=(
                (
                    [self.config.adobe_password]
                    if self.config.adobe_password
                    else [] + (self.config.pdf_passwords or [])
                )
                if self.config
                else []
            ),
        )

    def _perform_epub(self) -> str:
        logger.debug(f"Removing DRM from epub file {self.filepath}...")
        return dedrm.decryptepub(
            self.filepath,
            outdir=self.temp_dirpath,
            key_files=(
                [
                    *(self.config.adobe_key_files or []),
                    *(self.config.b_and_n_key_files or []),
                ]
                if self.config
                else []
            ),
        )


class ReformatPdfAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "reformat a PDF via k2pdfopt"

    @classmethod
    def id(cls) -> str:
        return "pdf"

    def perform(self):
        metadata = self.get_metadata()
        if metadata is False:
            logger.debug(f"Skipping {self.filepath} because no metadata.")
            return self.filepath

        if metadata.is_k2pdfopt_version:
            logger.debug(f"Skipping {self.filepath} because it's already reformatted.")
            return self.filepath

        if not metadata.is_pdf:
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
            check=True,
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

        metadata.is_k2pdfopt_version = True

        logger.info(f"Reformatted {self.filepath} with k2pdfopt")
        return temp_filepath_metadata


class PrintAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "print metadata to console"

    @classmethod
    def id(cls) -> str:
        return "print"

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
                            if metadata.is_pdf
                            else None,
                        ]
                        if s is not None
                    ],
                )
            )
        return self.filepath


class DownloadAcsmAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "download an ACSM file"

    @classmethod
    def id(cls) -> str:
        return "download_acsm"

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
                if data.config and a.urn == data.config.current_user:
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
                if new_filepath is None:
                    raise GetEbookException(self.filepath, "No file downloaded")
                logging.info(f"Downloaded {self.filepath}")
                return new_filepath
            except Exception as e:
                if isinstance(e, GetEbookException):
                    raise BookError(self.filepath, message=str(e))
                raise
        logger.debug(f"Skipping {self.filepath} because it's not an ACSM file.")
        return self.filepath


class Kfx2EpubAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "convert kfx to epub"

    @classmethod
    def id(cls) -> str:
        return "kfx2epub"

    def perform(self):
        valid_extensions = ["kfx", "kfx-zip", "kpf"]
        ext = os.path.splitext(self.filepath)[1].lower()[1:]
        if ext in valid_extensions:
            filepath = os.path.join(self.temp_dirpath, "after_kfx2epub.epub")
            with open(filepath, "wb") as f:
                f.write(kfxconvert.convert_to_epub(self.filepath))
            logger.info(f"Converted {self.filepath} to {filepath}")
            return filepath
        logger.debug(
            f"Skipping {self.filepath} because it's not a KFX-ZIP file (extensions {', '.join(valid_extensions)})."
        )
        return self.filepath


ALL_ACTIONS: Sequence[type[BaseAction]] = [
    DeDrmAction,
    RenameAction,
    PrintAction,
    ReformatPdfAction,
    DownloadAcsmAction,
    Kfx2EpubAction,
]
