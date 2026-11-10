import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import override

import pymupdf

from efm import dedrm, kfxconvert
from efm.config import Config
from efm.env import ensure_k2pdfopt
from efm.exceptions import (
    RemoveDrmError,
)
from efm.metadata import Metadata, get_metadata, is_k2pdfopt_file

logger = logging.getLogger(__name__)


class BaseAction:
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
    @override
    @classmethod
    def description(cls) -> str:
        return "remove DRM from files"

    @override
    @classmethod
    def id(cls) -> str:
        return "drm"

    @override
    def perform(self) -> Path:
        booktype = self.filepath.suffix.lower()[1:]
        new_filepath = self._perform_for_type(booktype)
        if new_filepath is None:
            logger.info(f"No DeDRM support for format {booktype} files.")
            return self.filepath
        # it's almost guaranteed I'll need to change the metadata now because it's impossible to do
        #  before removing the DRM
        self.metadata = get_metadata(new_filepath)
        return new_filepath

    def _perform_for_type(self, booktype: str):
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
        return None

    def _perform_k4mobi(self) -> Path:
        if not self.config:
            raise RemoveDrmError(
                self.filepath,
                message="No config found, but kindle_* config keys are required",
            )
        kindle_android_files = []
        kindle_db_files = []
        kindle_pids = []
        kindle_serials = []
        if self.config.kindle_android_files:
            logger.debug("Using kindle_android_files from config")
            kindle_android_files = self.config.kindle_android_files
        if self.config.kindle_database_files:
            logger.debug("Using kindle_database_files from config")
            kindle_db_files = self.config.kindle_database_files
        if self.config.kindle_pidnums:
            logger.debug("Using kindle_pidnums from config")
            kindle_pids = self.config.kindle_pidnums
        if self.config.kindle_serialnums:
            logger.debug("Using kindle_serialnums from config")
            kindle_serials = self.config.kindle_serialnums
        logger.debug(f"Removing DRM from k4mobi file {self.filepath}...")
        return Path(
            dedrm.decryptk4mobi(
                self.filepath,
                outdir=self.temp_dirpath,
                kindle_android_files=kindle_android_files,
                kindle_db_files=kindle_db_files,
                kindle_pids=kindle_pids,
                kindle_serials=kindle_serials,
            )
        )

    def _perform_pdb(self) -> Path:
        logger.debug(f"Removing DRM from pdb file {self.filepath}...")
        if not self.config:
            raise RemoveDrmError(
                self.filepath,
                message="No config found, but ereader_social_drm_file key is required",
            )
        social_drm_file = self.config.ereader_social_drm_file
        if not social_drm_file:
            raise RemoveDrmError(
                self.filepath,
                message="ereader_social_drm_file is a required config key",
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
        # I think it's possible to remove drm from pdf in rare cases, so we allow it in this case
        key_files: list[Path] = []
        passwords: list[str] = []
        if self.config:
            if self.config.adobe_key_files:
                logger.debug("Using adobe_key_files from config")
                key_files.append(*self.config.adobe_key_files)
            if self.config.b_and_n_key_files:
                logger.debug("Using b_and_n_files from config")
                key_files.append(*self.config.b_and_n_key_files)
            if self.config.adobe_password:
                logger.debug("Using adobe_password from config")
                passwords.append(self.config.adobe_password)
            if self.config.pdf_passwords:
                logger.debug("Using pdf_passwords from config")
                passwords.append(*self.config.pdf_passwords)
        return Path(
            dedrm.decryptpdf(
                self.filepath,
                outdir=self.temp_dirpath,
                key_files=key_files,
                passwords=passwords,
            )
        )

    def _perform_epub(self) -> Path:
        logger.debug(f"Removing DRM from epub file {self.filepath}")
        # I think it's possible to remove drm from epub in rare cases, so we allow it in this case
        key_files: list[Path] = []
        if self.config:
            if self.config.adobe_key_files:
                logger.debug("Using adobe_key_files from config")
                key_files.append(*self.config.adobe_key_files)
            if self.config.b_and_n_key_files:
                logger.debug("Using b_and_n_files from config")
                key_files.append(*self.config.b_and_n_key_files)
        return dedrm.decryptepub(
            self.filepath, outdir=self.temp_dirpath, key_files=key_files
        )


class ReformatPdfAction(BaseAction):
    @override
    @classmethod
    def description(cls) -> str:
        return "reformat a PDF via k2pdfopt"

    @override
    @classmethod
    def id(cls) -> str:
        return "pdf"

    @override
    def perform(self) -> Path:
        metadata = self.metadata
        if not metadata:
            logger.debug(f"Skipping {self.filepath} because no metadata.")
            return self.filepath

        if is_k2pdfopt_file(self.filepath):
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

        f: pymupdf.Document = pymupdf.open(temp_filepath_k2pdfopt)
        f.embfile_add("__ebooks-folder-manager.json", b'{"k2pdfopt_version": true}')

        temp_filepath_metadata = self.temp_dirpath / "post_reformat_pdf_metadata.pdf"
        f.save(str(temp_filepath_metadata))
        logger.debug(
            f"Added metadata to {temp_filepath_k2pdfopt} and saved to {temp_filepath_metadata}"
        )

        logger.debug(f"Reformatted {self.filepath} with k2pdfopt")
        return temp_filepath_metadata


class Kfx2EpubAction(BaseAction):
    @override
    @classmethod
    def description(cls) -> str:
        return "convert kfx to epub"

    @override
    @classmethod
    def id(cls) -> str:
        return "kfx2epub"

    @override
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
    DeDrmAction,
    Kfx2EpubAction,
    ReformatPdfAction,
]
