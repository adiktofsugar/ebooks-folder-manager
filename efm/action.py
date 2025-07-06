import logging
from pathlib import Path
import subprocess
from typing import Sequence
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
    metadata: Metadata | None
    filepath: Path
    temp_dirpath: Path

    def __init__(
        self,
        config: Config | None,
        metadata: Metadata | None,
        filepath: Path,
        temp_dirpath: Path,
    ):
        self.config = config
        self.metadata = metadata
        self.filepath = filepath
        self.temp_dirpath = temp_dirpath

    def perform(self) -> Path:
        raise NotImplementedError


class DeDrmAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "remove DRM from files"

    @classmethod
    def id(cls) -> str:
        return "drm"

    def perform(self) -> Path:
        booktype = self.filepath.suffix.lower()[1:]
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
            return self._perform_k4mobi()
        elif booktype == "pdb":
            return self._perform_pdb()
        elif booktype == "pdf":
            return self._perform_pdf()
        elif booktype == "epub":
            return self._perform_epub()

        logger.info(f"No DeDRM support for format {booktype} files.")
        return self.filepath

    def _perform_k4mobi(self) -> Path:
        if not self.config:
            raise RemoveDrmError(
                self.filepath,
                message="No config found, but kindle_* config keys are required to decrypt Kindle files.",
            )
        logger.debug(f"Removing DRM from k4mobi file {self.filepath}...")
        return Path(
            dedrm.decryptk4mobi(
                self.filepath,
                outdir=self.temp_dirpath,
                kindle_android_files=self.config.kindle_android_files or [],
                kindle_db_files=self.config.kindle_database_files or [],
                kindle_pids=self.config.kindle_pidnums or [],
                kindle_serials=self.config.kindle_serialnums or [],
            )
        )

    def _perform_pdb(self) -> Path:
        logger.debug(f"Removing DRM from pdb file {self.filepath}...")
        social_drm_file = self.config.ereader_social_drm_file if self.config else None
        if not social_drm_file:
            raise RemoveDrmError(
                self.filepath,
                message="No social DRM file found. Add ereader_social_drm_file to config file.",
            )
        return Path(
            dedrm.decryptpdb(
                self.filepath,
                outdir=self.temp_dirpath,
                social_drm_file=social_drm_file,
            )
        )

    def _perform_pdf(self) -> Path:
        logger.debug(f"Removing DRM from pdf file {self.filepath}...")
        return Path(
            dedrm.decryptpdf(
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
        )

    def _perform_epub(self) -> Path:
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

    def perform(self) -> Path:
        metadata = self.metadata
        if not metadata:
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
        temp_filepath_k2pdfopt = self.temp_dirpath / "post_reformat_pdf_k2pdfopt.pdf"
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
                str(temp_filepath_k2pdfopt),
                str(self.filepath),
            ],
            stdin=subprocess.DEVNULL,
            check=True,
        )
        logger.debug(
            f"Reformated {self.filepath} with k2pdfopt to {temp_filepath_k2pdfopt}"
        )

        f = pymupdf.open(temp_filepath_k2pdfopt)
        f.embfile_add("__ebooks-folder-manager.json", b'{"k2pdfopt_version": true}')

        temp_filepath_metadata = self.temp_dirpath / "post_reformat_pdf_metadata.pdf"
        f.save(str(temp_filepath_metadata))
        logger.debug(
            f"Added metadata to {temp_filepath_k2pdfopt} and saved to {temp_filepath_metadata}"
        )

        metadata.is_k2pdfopt_version = True

        logger.debug(f"Reformatted {self.filepath} with k2pdfopt")
        return temp_filepath_metadata


class DownloadAcsmAction(BaseAction):
    @classmethod
    def description(cls) -> str:
        return "download an ACSM file"

    @classmethod
    def id(cls) -> str:
        return "download_acsm"

    def perform(self) -> Path:
        if self.filepath.suffix.lower() == ".acsm":
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
                login(username, password)
            elif current_user != user:
                account.set_default_account(user.urn)

            try:
                new_filepath = get_ebook(str(self.filepath))
                if new_filepath is None:
                    raise GetEbookException(str(self.filepath), "No file downloaded")
                logging.info(f"Downloaded {self.filepath}")
                return Path(new_filepath)
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

    def perform(self) -> Path:
        valid_extensions = ["kfx", "kfx-zip", "kpf"]
        ext = self.filepath.suffix.lower()[1:]
        if ext in valid_extensions:
            filepath = self.temp_dirpath / "after_kfx2epub.epub"
            with open(filepath, "wb") as f:
                f.write(kfxconvert.convert_to_epub(str(self.filepath)))
            logger.debug(f"Converted {self.filepath} to {filepath}")
            return filepath
        logger.debug(
            f"Skipping {self.filepath} because it's not a KFX-ZIP file (extensions {', '.join(valid_extensions)})."
        )
        return self.filepath


ALL_ACTIONS: Sequence[type[BaseAction]] = [
    DownloadAcsmAction,
    Kfx2EpubAction,
    DeDrmAction,
    ReformatPdfAction,
]
